from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from backend.app.core.config import settings

logger = logging.getLogger("ticketsense.ml")


class ModelService:
    """Service that manages loading and executing the trained TicketSense ML bundle."""

    def __init__(self, model_path: str | None = None, metrics_path: str | None = None):
        self.model_path = Path(model_path or settings.MODEL_PATH)
        self.metrics_path = Path(metrics_path or settings.METRICS_PATH)
        self.cat_pipe: Any = None
        self.prio_pipe: Any = None
        self.categories: list[str] = []
        self.priorities: list[str] = []
        self.metrics_data: dict[str, Any] | None = None
        self.load_model()
        self.load_metrics()

    def load_model(self) -> None:
        """Load joblib model bundle into memory."""
        if self.model_path.exists():
            try:
                bundle = joblib.load(self.model_path)
                if isinstance(bundle, dict):
                    self.cat_pipe = bundle["category_pipeline"]
                    self.prio_pipe = bundle["priority_pipeline"]
                    self.categories = list(self.cat_pipe.classes_)
                    self.priorities = list(self.prio_pipe.classes_)
                elif hasattr(bundle, "category_pipeline"):
                    self.cat_pipe = bundle.category_pipeline
                    self.prio_pipe = bundle.priority_pipeline
                    self.categories = list(self.cat_pipe.classes_)
                    self.priorities = list(self.prio_pipe.classes_)
                logger.info(f"Loaded ML model bundle successfully from {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to load model bundle from {self.model_path}: {e}")
                self.cat_pipe = None
                self.prio_pipe = None
        else:
            logger.warning(f"Model artifact not found at {self.model_path}")
            self.cat_pipe = None
            self.prio_pipe = None

    def load_metrics(self) -> None:
        """Load evaluation metrics JSON into memory."""
        if self.metrics_path.exists():
            try:
                with open(self.metrics_path, encoding="utf-8") as f:
                    self.metrics_data = json.load(f)
                logger.info(f"Loaded evaluation metrics from {self.metrics_path}")
            except Exception as e:
                logger.error(f"Failed to load metrics from {self.metrics_path}: {e}")
                self.metrics_data = None
        else:
            self.metrics_data = None

    @property
    def is_loaded(self) -> bool:
        """Check if model bundle is loaded and ready to serve predictions."""
        return self.cat_pipe is not None and self.prio_pipe is not None

    def predict(self, title: str, description: str) -> dict[str, Any]:
        """Classify a support ticket into category and priority with confidence scores."""
        text = f"{title.strip()} {description.strip()}".strip()

        # Fallback if model bundle failed to load
        if not self.is_loaded:
            logger.warning("Model bundle not loaded; returning heuristic fallback prediction")
            return {
                "category": "Other",
                "category_confidence": 0.5000,
                "category_probabilities": {"Other": 1.0},
                "priority": "Medium",
                "priority_confidence": 0.5000,
                "priority_probabilities": {"Medium": 1.0},
            }

        cat_probs = self.cat_pipe.predict_proba([text])[0]
        prio_probs = self.prio_pipe.predict_proba([text])[0]

        cat_idx = int(np.argmax(cat_probs))
        cat_label = self.categories[cat_idx]
        cat_conf = float(cat_probs[cat_idx])

        prio_idx = int(np.argmax(prio_probs))
        prio_label = self.priorities[prio_idx]
        prio_conf = float(prio_probs[prio_idx])

        return {
            "category": cat_label,
            "category_confidence": round(cat_conf, 4),
            "category_probabilities": {
                self.categories[j]: round(float(cat_probs[j]), 4)
                for j in range(len(self.categories))
            },
            "priority": prio_label,
            "priority_confidence": round(prio_conf, 4),
            "priority_probabilities": {
                self.priorities[j]: round(float(prio_probs[j]), 4)
                for j in range(len(self.priorities))
            },
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return the precomputed model evaluation metrics."""
        if self.metrics_data:
            return self.metrics_data
        return {
            "status": "unavailable",
            "message": "Evaluation metrics not found. Run ml/train.py to generate.",
        }


# Global singleton instance
model_service = ModelService()
