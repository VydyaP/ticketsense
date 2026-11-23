"""Unit tests for the ML wrapper (no database or HTTP involved)."""

from __future__ import annotations

import pytest

from backend.app.ml.model import ModelNotLoadedError, ModelService


@pytest.fixture(scope="module")
def service() -> ModelService:
    return ModelService()


def test_loads_artifact_and_metrics(service: ModelService):
    assert service.is_loaded
    assert service.metrics_data is not None
    assert service.categories == service.metrics_data["category_model"]["classes"]
    assert set(service.priorities) == {"High", "Medium", "Low"}


def test_prediction_shape_and_probabilities(service: ModelService):
    result = service.predict("Monitor not working", "My second monitor shows no signal")

    assert result["category"] in service.categories
    assert result["priority"] in service.priorities
    assert sum(result["category_probabilities"].values()) == pytest.approx(1.0, abs=0.01)
    assert sum(result["priority_probabilities"].values()) == pytest.approx(1.0, abs=0.01)
    # Confidence is the probability of the chosen label, i.e. the highest one.
    assert result["category_confidence"] == max(result["category_probabilities"].values())
    assert result["priority_confidence"] == max(result["priority_probabilities"].values())


@pytest.mark.parametrize(
    ("title", "description", "expected"),
    [
        # Clear-cut examples in the style of the training data. These guard
        # against a broken retrain (e.g. shuffled labels), not model quality.
        (
            "lost access card",
            "hello I lost my access card please block it",
            "Physical Access & Badges",
        ),
        ("monitor request", "please provide a new monitor for my desk", "Hardware & Equipment"),
    ],
)
def test_sanity_predictions(service: ModelService, title: str, description: str, expected: str):
    assert service.predict(title, description)["category"] == expected


def test_missing_artifact_raises_instead_of_guessing(tmp_path):
    empty = ModelService(
        model_path=str(tmp_path / "missing.joblib"), metrics_path=str(tmp_path / "missing.json")
    )
    assert not empty.is_loaded
    assert empty.categories == []
    with pytest.raises(ModelNotLoadedError):
        empty.predict("Any title", "Any description")
