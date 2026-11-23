"""
TicketSense ML training pipeline.

Run from the repo root:  python ml/train.py

What it does, in order:
1. Downloads the Endava support-ticket dataset (if not cached in data/) and
   verifies its SHA-256 checksum so every run trains on exactly the same file.
2. Turns the dataset's anonymized numeric labels into human-readable labels
   (see CATEGORY_NAMES / map_priority below for how and why).
3. Splits 80/20 (stratified, fixed seed), trains two TF-IDF + Logistic
   Regression pipelines (category and priority), and evaluates them on the
   held-out 20% against a majority-class baseline.
4. Writes ml/metrics.json, ml/confusion_matrix.png, ml/category_evidence.json
   and the model artifact used by the API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import urllib.request
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")  # headless backend: no display needed (CI, servers)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402
from sklearn.dummy import DummyClassifier  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RANDOM_STATE = 42

# --- Dataset provenance -------------------------------------------------------
# The dataset was published by Microsoft + Endava in the MIT-licensed repo
# https://github.com/karolzak/support-tickets-classification . Its official
# download link (an Azure blob SAS URL) expired in 2022, so we download an
# identical public mirror and pin its checksum.
ORIGINAL_SOURCE = "https://github.com/karolzak/support-tickets-classification"
DATASET_URL = (
    "https://raw.githubusercontent.com/vanessaaleung/support-ticket-nlp/master/all_tickets.csv"
)
DATASET_SHA256 = "26ef6f2e5c800371b4d7505070a71e15535c3a7b57c3ac0deb8a4ff8823c64c8"

# --- Label mapping ------------------------------------------------------------
# The published dataset is anonymized: `category` is an integer 0-12 produced by
# sklearn's LabelEncoder, and the original category names were NOT released.
# The names below are OUR interpretation, chosen by reading sample tickets and
# the top TF-IDF terms of each code (regenerated on every run into
# ml/category_evidence.json so anyone can check them). Codes whose content is
# mixed or that have too few examples to learn from are grouped as "Other".
CATEGORY_NAMES: dict[int, str] = {
    4: "Accounts & Applications",  # access requests, passwords, app issues, joiners/leavers
    5: "Hardware & Equipment",  # monitors, laptops, peripherals
    6: "Infrastructure & Servers",  # servers, connectivity, outages, deployments
    7: "Physical Access & Badges",  # access cards, secure areas, visitor cards
    11: "Physical Access & Badges",  # lost badges, door events
    8: "Monitoring Alerts",  # automated "critical alert" emails (backups, sync)
    9: "Procurement & Quotes",  # purchase requisitions, equipment quotes
}
OTHER_CATEGORY = "Other"  # codes 0, 1, 2, 3, 10, 12 (mixed content or < 140 tickets each)


def map_category(code: int) -> str:
    """Map an anonymized category code to our human-readable category."""
    return CATEGORY_NAMES.get(int(code), OTHER_CATEGORY)


def map_priority(urgency: int) -> str:
    """Map the anonymized urgency code (0-3) to High / Medium / Low.

    ASSUMPTION: lower code = more urgent, as in the usual ITIL scale
    (1-Critical ... 4-Low). Supporting evidence: code 3 holds 71% of tickets
    (most help-desk tickets are low urgency), and the words
    "urgent/asap/critical/immediately" are about twice as frequent in codes 0-2
    as in code 3. This is documented as an assumption in the README.
    """
    urgency = int(urgency)
    if urgency <= 1:
        return "High"
    if urgency == 2:
        return "Medium"
    return "Low"


# --- Pipeline steps -----------------------------------------------------------
def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_dataset(data_path: Path) -> Path:
    """Download the dataset if missing, then verify its checksum."""
    if not data_path.exists():
        data_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading dataset from %s", DATASET_URL)
        req = urllib.request.Request(DATASET_URL, headers={"User-Agent": "ticketsense-train"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data_path.write_bytes(resp.read())

    actual = sha256_of(data_path)
    if actual != DATASET_SHA256:
        raise RuntimeError(
            f"Checksum mismatch for {data_path}: expected {DATASET_SHA256}, got {actual}. "
            "The mirror may have changed; results would not be reproducible."
        )
    logger.info("Dataset checksum verified (%s)", data_path)
    return data_path


def load_data(data_path: Path) -> pd.DataFrame:
    """Load the CSV, build the text field and the two target labels."""
    df = pd.read_csv(data_path)
    df["text"] = (df["title"].fillna("") + " " + df["body"].fillna("")).str.strip()
    # Drop near-empty tickets: there is nothing to learn from them.
    df = df[df["text"].str.len() >= 8].copy()
    df["category_label"] = df["category"].apply(map_category)
    df["priority_label"] = df["urgency"].apply(map_priority)
    logger.info("Loaded %d tickets", len(df))
    logger.info("Categories: %s", df["category_label"].value_counts().to_dict())
    logger.info("Priorities: %s", df["priority_label"].value_counts().to_dict())
    return df


def category_evidence(df: pd.DataFrame, top_n: int = 12) -> dict[str, Any]:
    """Top TF-IDF terms per raw category code: the evidence behind CATEGORY_NAMES."""
    vec = TfidfVectorizer(stop_words="english", min_df=5)
    matrix = vec.fit_transform(df["text"])
    terms = np.array(vec.get_feature_names_out())
    evidence = {}
    for code in sorted(df["category"].unique()):
        mask = (df["category"] == code).to_numpy()
        mean_scores = np.asarray(matrix[mask].mean(axis=0)).ravel()
        evidence[str(code)] = {
            "mapped_to": map_category(code),
            "tickets": int(mask.sum()),
            "top_terms": terms[mean_scores.argsort()[::-1][:top_n]].tolist(),
        }
    return evidence


def build_pipeline(max_features: int, c: float) -> Pipeline:
    """TF-IDF (unigrams + bigrams) followed by class-balanced Logistic Regression.

    class_weight="balanced" matters because the data is very imbalanced
    (one category is ~70% of tickets); without it the model mostly ignores
    small classes.
    """
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=max_features,
                    sublinear_tf=True,
                    stop_words="english",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000, class_weight="balanced", C=c, random_state=RANDOM_STATE
                ),
            ),
        ]
    )


def evaluate(name: str, pipe: Pipeline, x_train, y_train, x_test, y_test) -> tuple[dict, Any]:
    """Fit on train, score on test, and compare with a majority-class baseline."""
    pipe.fit(x_train, y_train)
    y_pred = pipe.predict(x_test)

    baseline = DummyClassifier(strategy="most_frequent").fit(x_train, y_train)
    y_base = baseline.predict(x_test)

    classes = sorted(np.unique(y_test))
    report = classification_report(y_test, y_pred, labels=classes, output_dict=True)
    result = {
        "algorithm": "TF-IDF (1-2 grams, sublinear tf) + Logistic Regression (balanced)",
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "macro_f1": round(f1_score(y_test, y_pred, average="macro"), 4),
        "weighted_f1": round(f1_score(y_test, y_pred, average="weighted"), 4),
        "baseline_majority_class": {
            "accuracy": round(accuracy_score(y_test, y_base), 4),
            "macro_f1": round(f1_score(y_test, y_base, average="macro"), 4),
        },
        "classes": classes,
        "per_class": {
            cls: {
                "precision": round(report[cls]["precision"], 4),
                "recall": round(report[cls]["recall"], 4),
                "f1_score": round(report[cls]["f1-score"], 4),
                "support": int(report[cls]["support"]),
            }
            for cls in classes
        },
    }
    logger.info(
        "%s: accuracy=%.4f macro_f1=%.4f (baseline accuracy=%.4f macro_f1=%.4f)",
        name,
        result["accuracy"],
        result["macro_f1"],
        result["baseline_majority_class"]["accuracy"],
        result["baseline_majority_class"]["macro_f1"],
    )
    return result, y_pred


def save_confusion_matrix(y_true, y_pred, path: Path) -> None:
    """Row-normalized confusion matrix: each row shows where that class's tickets went."""
    fig, ax = plt.subplots(figsize=(9, 7))
    ConfusionMatrixDisplay.from_predictions(
        y_true,
        y_pred,
        normalize="true",
        values_format=".2f",
        cmap="Blues",
        ax=ax,
        xticks_rotation=35,
    )
    ax.set_title("Category model - confusion matrix (test set, row-normalized)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the TicketSense models")
    parser.add_argument("--data-path", type=Path, default=Path("data/all_tickets.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("ml"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("backend/app/ml/artifacts"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(download_dataset(args.data_path))

    # One split shared by both models, stratified on category so small classes
    # appear in the test set in the same proportion as in training.
    x_train, x_test, yc_train, yc_test, yp_train, yp_test = train_test_split(
        df["text"].to_numpy(),
        df["category_label"].to_numpy(),
        df["priority_label"].to_numpy(),
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=df["category_label"],
    )

    cat_pipe = build_pipeline(max_features=20000, c=2.0)
    prio_pipe = build_pipeline(max_features=20000, c=1.0)
    cat_metrics, yc_pred = evaluate("category", cat_pipe, x_train, yc_train, x_test, yc_test)
    prio_metrics, _ = evaluate("priority", prio_pipe, x_train, yp_train, x_test, yp_test)

    save_confusion_matrix(yc_test, yc_pred, args.output_dir / "confusion_matrix.png")

    metrics = {
        "dataset": {
            "name": "Endava IT support tickets (anonymized)",
            "original_source": ORIGINAL_SOURCE,
            "original_license": "MIT (license of the publishing repository)",
            "download_url": DATASET_URL,
            "sha256": DATASET_SHA256,
            "total_samples": int(len(df)),
            "train_samples": int(len(x_train)),
            "test_samples": int(len(x_test)),
            "label_note": "Category names are our interpretation of anonymized codes; "
            "see ml/category_evidence.json.",
        },
        "scikit_learn_version": sklearn.__version__,
        "random_state": RANDOM_STATE,
        "category_model": cat_metrics,
        "priority_model": prio_metrics,
    }

    for path in (args.output_dir / "metrics.json", args.artifact_dir / "metrics.json"):
        path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "category_evidence.json").write_text(
        json.dumps(category_evidence(df), indent=2) + "\n", encoding="utf-8"
    )

    # The API loads this dict; the sklearn version is checked at load time
    # because pickled models are only reliable on the same version.
    bundle = {
        "category_pipeline": cat_pipe,
        "priority_pipeline": prio_pipe,
        "sklearn_version": sklearn.__version__,
    }
    model_path = args.artifact_dir / "ticket_classifier.joblib"
    joblib.dump(bundle, model_path, compress=3)
    logger.info("Saved model to %s (%.2f MB)", model_path, model_path.stat().st_size / 1e6)


if __name__ == "__main__":
    main()
