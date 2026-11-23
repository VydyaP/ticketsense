from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn

from backend.app.core.config import settings

logger = logging.getLogger("ticketsense.ml")


class ModelNotLoadedError(RuntimeError):
    """Raised when a prediction is requested but the model artifact is unavailable."""


class ModelService:
    """Loads the trained model bundle once and serves predictions from memory.

    The bundle (written by ml/train.py) holds two scikit-learn Pipelines, each
    TF-IDF + Logistic Regression: one predicts category, the other priority.
    """

    def __init__(self, model_path: str | None = None, metrics_path: str | None = None):
        self.model_path = Path(model_path or settings.MODEL_PATH)
        self.metrics_path = Path(metrics_path or settings.METRICS_PATH)
        self.cat_pipe: Any = None
        self.prio_pipe: Any = None
        self.metrics_data: dict[str, Any] | None = None
        self.load_model()
        self.load_metrics()

    def load_model(self) -> None:
        """Load the joblib bundle. On failure the service stays unloaded and /health reports it."""
        if not self.model_path.exists():
            logger.error("Model artifact not found at %s", self.model_path)
            return
        try:
            bundle = joblib.load(self.model_path)
            self.cat_pipe = bundle["category_pipeline"]
            self.prio_pipe = bundle["priority_pipeline"]
        except Exception:
            logger.exception("Failed to load model artifact from %s", self.model_path)
            self.cat_pipe = self.prio_pipe = None
            return

        trained_with = bundle.get("sklearn_version")
        if trained_with and trained_with != sklearn.__version__:
            # Pickled sklearn objects are only guaranteed to work on the same version.
            logger.warning(
                "Model trained with scikit-learn %s but running %s; pin the same version",
                trained_with,
                sklearn.__version__,
            )
        logger.info("Loaded model artifact from %s", self.model_path)

    def load_metrics(self) -> None:
        """Load the evaluation metrics written by ml/train.py (served by /api/model/metrics)."""
        try:
            self.metrics_data = json.loads(self.metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Metrics file unavailable at %s", self.metrics_path)
            self.metrics_data = None

    @property
    def is_loaded(self) -> bool:
        return self.cat_pipe is not None and self.prio_pipe is not None

    @property
    def categories(self) -> list[str]:
        """Category labels the model can predict (also the valid values for corrections)."""
        return [str(c) for c in self.cat_pipe.classes_] if self.is_loaded else []

    @property
    def priorities(self) -> list[str]:
        return [str(p) for p in self.prio_pipe.classes_] if self.is_loaded else []

    @staticmethod
    def _top(classes: list[str], probs: np.ndarray) -> tuple[str, float, dict[str, float]]:
        """Return (best label, its probability, full probability map)."""
        best = int(np.argmax(probs))
        distribution = {cls: round(float(p), 4) for cls, p in zip(classes, probs, strict=True)}
        return classes[best], round(float(probs[best]), 4), distribution

    def predict(self, title: str, description: str) -> dict[str, Any]:
        """Predict category and priority for one ticket, with confidence scores.

        Title and description are joined into one text, exactly as in training.
        Confidence is the Logistic Regression probability of the chosen class.
        """
        if not self.is_loaded:
            raise ModelNotLoadedError("The classification model is not loaded")

        text = f"{title.strip()} {description.strip()}"
        category, cat_conf, cat_probs = self._top(
            self.categories, self.cat_pipe.predict_proba([text])[0]
        )
        priority, prio_conf, prio_probs = self._top(
            self.priorities, self.prio_pipe.predict_proba([text])[0]
        )
        return {
            "category": category,
            "category_confidence": cat_conf,
            "category_probabilities": cat_probs,
            "priority": priority,
            "priority_confidence": prio_conf,
            "priority_probabilities": prio_probs,
        }

    def get_metrics(self) -> dict[str, Any] | None:
        return self.metrics_data


# Loaded once at import time and shared by all requests.
model_service = ModelService()
