"""
TicketSense ML Training Pipeline.

Reproducibly trains and evaluates text classification models for IT ticket
category and priority triage, saving the combined model artifact, metrics.json,
and confusion matrix visualization.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATASET_URL = (
    "https://raw.githubusercontent.com/vanessaaleung/support-ticket-nlp/master/all_tickets.csv"
)

# Standard IT Helpdesk Category Mapping for Endava ITSM Dataset
CATEGORY_MAPPING = {
    4: "Access/Account",
    5: "Hardware",
    6: "Network",
    7: "Facilities",
    3: "Software",
    8: "Software",
    9: "Software",
}


def map_category(raw_val: Any) -> str:
    """Map numeric category code to standard human-readable category."""
    try:
        val = int(raw_val)
        return CATEGORY_MAPPING.get(val, "Other")
    except (ValueError, TypeError):
        return "Other"


def map_priority(urgency_val: Any) -> str:
    """Map ITIL urgency level to High, Medium, or Low priority."""
    try:
        val = int(urgency_val)
        if val in (0, 1):
            return "High"
        if val == 2:
            return "Medium"
        return "Low"
    except (ValueError, TypeError):
        return "Medium"


class TicketClassifierBundle:
    """Bundle containing both category and priority trained pipelines."""

    def __init__(self, category_pipeline: Pipeline, priority_pipeline: Pipeline):
        self.category_pipeline = category_pipeline
        self.priority_pipeline = priority_pipeline
        self.categories = list(category_pipeline.classes_)
        self.priorities = list(priority_pipeline.classes_)

    def predict(self, texts: list[str]) -> list[Dict[str, Any]]:
        """Predict category and priority with confidence scores for input texts."""
        cat_probs = self.category_pipeline.predict_proba(texts)
        prio_probs = self.priority_pipeline.predict_proba(texts)

        results = []
        for i in range(len(texts)):
            cat_idx = int(np.argmax(cat_probs[i]))
            cat_label = self.categories[cat_idx]
            cat_conf = float(cat_probs[i][cat_idx])

            prio_idx = int(np.argmax(prio_probs[i]))
            prio_label = self.priorities[prio_idx]
            prio_conf = float(prio_probs[i][prio_idx])

            results.append(
                {
                    "category": cat_label,
                    "category_confidence": round(cat_conf, 4),
                    "category_probabilities": {
                        self.categories[j]: round(float(cat_probs[i][j]), 4)
                        for j in range(len(self.categories))
                    },
                    "priority": prio_label,
                    "priority_confidence": round(prio_conf, 4),
                    "priority_probabilities": {
                        self.priorities[j]: round(float(prio_probs[i][j]), 4)
                        for j in range(len(self.priorities))
                    },
                }
            )
        return results


def download_dataset_if_needed(data_path: Path, url: str) -> Path:
    """Ensure dataset exists locally, downloading from source if not present."""
    if data_path.exists():
        logger.info(f"Using existing dataset at: {data_path}")
        return data_path

    data_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading dataset from: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 TicketSense-ML"})
    with urllib.request.urlopen(req) as resp, open(data_path, "wb") as f:
        f.write(resp.read())
    logger.info(f"Dataset downloaded successfully ({data_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return data_path


def load_and_preprocess_data(data_path: Path) -> pd.DataFrame:
    """Load dataset, clean text fields, and extract target labels."""
    logger.info(f"Reading CSV from {data_path}...")
    df = pd.read_csv(data_path)

    df["title"] = df["title"].fillna("")
    df["body"] = df["body"].fillna("")
    df["text"] = (df["title"] + " " + df["body"]).str.strip()

    # Filter out empty or trivially short tickets
    df = df[df["text"].str.len() >= 8].copy()

    df["category_label"] = df["category"].apply(map_category)
    df["priority_label"] = df["urgency"].apply(map_priority)

    logger.info(f"Preprocessed {len(df)} total tickets.")
    logger.info(f"Category distribution:\n{df['category_label'].value_counts().to_dict()}")
    logger.info(f"Priority distribution:\n{df['priority_label'].value_counts().to_dict()}")
    return df


def train_and_evaluate(
    df: pd.DataFrame, output_dir: Path
) -> Tuple[TicketClassifierBundle, Dict[str, Any]]:
    """Train TF-IDF + LogisticRegression models and compute evaluation metrics."""
    X = df["text"].values
    y_cat = df["category_label"].values
    y_prio = df["priority_label"].values

    # Stratified 80/20 train/test split on category
    X_train, X_test, y_cat_train, y_cat_test, y_prio_train, y_prio_test = train_test_split(
        X, y_cat, y_prio, test_size=0.20, random_state=42, stratify=y_cat
    )

    logger.info(f"Training set: {len(X_train)} samples | Test set: {len(X_test)} samples")

    # 1. Train Category Pipeline
    logger.info("Training Category classifier (TF-IDF + LogisticRegression)...")
    cat_pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=12000,
                    sublinear_tf=True,
                    stop_words="english",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    C=1.5,
                    solver="lbfgs",
                    random_state=42,
                ),
            ),
        ]
    )
    cat_pipe.fit(X_train, y_cat_train)
    y_cat_pred = cat_pipe.predict(X_test)

    cat_report = classification_report(y_cat_test, y_cat_pred, output_dict=True)
    cat_macro_f1 = f1_score(y_cat_test, y_cat_pred, average="macro")
    cat_acc = float(np.mean(y_cat_test == y_cat_pred))
    logger.info(f"Category Test Accuracy: {cat_acc:.4f} | Macro F1: {cat_macro_f1:.4f}")

    # 2. Train Priority Pipeline
    logger.info("Training Priority classifier (TF-IDF + LogisticRegression)...")
    prio_pipe = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=8000,
                    sublinear_tf=True,
                    stop_words="english",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    C=1.0,
                    solver="lbfgs",
                    random_state=42,
                ),
            ),
        ]
    )
    prio_pipe.fit(X_train, y_prio_train)
    y_prio_pred = prio_pipe.predict(X_test)

    prio_report = classification_report(y_prio_test, y_prio_pred, output_dict=True)
    prio_macro_f1 = f1_score(y_prio_test, y_prio_pred, average="macro")
    prio_acc = float(np.mean(y_prio_test == y_prio_pred))
    logger.info(f"Priority Test Accuracy: {prio_acc:.4f} | Macro F1: {prio_macro_f1:.4f}")

    # 3. Build Confusion Matrix Plot for Categories
    classes = sorted(list(np.unique(y_cat_test)))
    cm = confusion_matrix(y_cat_test, y_cat_pred, labels=classes)

    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=classes,
        yticklabels=classes,
    )
    plt.title("TicketSense: Category Classification Confusion Matrix (Test Set)")
    plt.xlabel("Predicted Category")
    plt.ylabel("Actual Category")
    plt.tight_layout()

    cm_path = output_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=300)
    plt.close()
    logger.info(f"Saved confusion matrix plot to: {cm_path}")

    # 4. Compile Metrics JSON
    metrics = {
        "dataset": {
            "name": "Public IT Helpdesk Support Dataset",
            "license": "MIT License",
            "source": DEFAULT_DATASET_URL,
            "total_samples": int(len(df)),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
        },
        "category_model": {
            "algorithm": "TF-IDF (1-2 ngrams, sublinear_tf) + Multinomial Logistic Regression (balanced)",
            "accuracy": round(cat_acc, 4),
            "macro_f1": round(cat_macro_f1, 4),
            "weighted_f1": round(float(cat_report["weighted avg"]["f1-score"]), 4),
            "classes": classes,
            "per_class": {
                cls: {
                    "precision": round(float(cat_report[cls]["precision"]), 4),
                    "recall": round(float(cat_report[cls]["recall"]), 4),
                    "f1_score": round(float(cat_report[cls]["f1-score"]), 4),
                    "support": int(cat_report[cls]["support"]),
                }
                for cls in classes
            },
        },
        "priority_model": {
            "algorithm": "TF-IDF + Multinomial Logistic Regression (balanced)",
            "accuracy": round(prio_acc, 4),
            "macro_f1": round(prio_macro_f1, 4),
            "weighted_f1": round(float(prio_report["weighted avg"]["f1-score"]), 4),
            "classes": sorted(list(np.unique(y_prio_test))),
            "per_class": {
                cls: {
                    "precision": round(float(prio_report[cls]["precision"]), 4),
                    "recall": round(float(prio_report[cls]["recall"]), 4),
                    "f1_score": round(float(prio_report[cls]["f1-score"]), 4),
                    "support": int(prio_report[cls]["support"]),
                }
                for cls in sorted(list(np.unique(y_prio_test)))
            },
        },
    }

    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics JSON to: {metrics_path}")

    bundle = TicketClassifierBundle(cat_pipe, prio_pipe)
    return bundle, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train TicketSense NLP Models")
    parser.add_argument(
        "--data-path",
        type=Path,
        default=Path("data/all_tickets.csv"),
        help="Path to local or cached CSV dataset",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_DATASET_URL,
        help="URL to download raw dataset if not present locally",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ml"),
        help="Directory where metrics and confusion matrix are saved",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("backend/app/ml/artifacts"),
        help="Directory where serialized model artifact is saved",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    data_file = download_dataset_if_needed(args.data_path, args.url)
    df = load_and_preprocess_data(data_file)
    bundle, metrics = train_and_evaluate(df, args.output_dir)

    # Save model artifact bundle
    model_path = args.artifact_dir / "ticket_classifier.joblib"
    joblib.dump(bundle, model_path, compress=3)
    logger.info(
        f"Saved model artifact to: {model_path} ({model_path.stat().st_size / 1024 / 1024:.2f} MB)"
    )

    # Copy metrics and confusion matrix into backend artifacts directory for API serving
    with open(args.artifact_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Training pipeline complete!")


if __name__ == "__main__":
    main()
