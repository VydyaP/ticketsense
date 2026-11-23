from __future__ import annotations

import pytest

from backend.app.ml.model import ModelService


def test_model_service_loads_artifacts():
    """Verify that model service loads real joblib artifact and metrics."""
    service = ModelService()
    assert service.is_loaded is True
    assert service.metrics_data is not None
    assert "category_model" in service.metrics_data
    assert "priority_model" in service.metrics_data


def test_model_predict_output_structure():
    """Test model inference returns required fields and valid probability distributions."""
    service = ModelService()
    result = service.predict(
        title="Cannot connect to VPN from home",
        description="Getting authentication timeout when connecting to global client gateway.",
    )

    assert "category" in result
    assert "category_confidence" in result
    assert "priority" in result
    assert "priority_confidence" in result
    assert "category_probabilities" in result
    assert "priority_probabilities" in result

    # Check probabilities sum to approximately 1.0
    cat_probs = result["category_probabilities"]
    assert sum(cat_probs.values()) == pytest.approx(1.0, abs=0.01)

    prio_probs = result["priority_probabilities"]
    assert sum(prio_probs.values()) == pytest.approx(1.0, abs=0.01)

    # Confidence matches max probability
    assert result["category_confidence"] == pytest.approx(max(cat_probs.values()), abs=0.001)
    assert result["priority_confidence"] == pytest.approx(max(prio_probs.values()), abs=0.001)


def test_model_service_fallback_heuristic(tmp_path):
    """Test graceful fallback behavior when model artifact is missing."""
    empty_service = ModelService(
        model_path=str(tmp_path / "non_existent.joblib"),
        metrics_path=str(tmp_path / "non_existent.json"),
    )
    assert empty_service.is_loaded is False

    result = empty_service.predict("Any title", "Any description")
    assert result["category"] == "Other"
    assert result["priority"] == "Medium"
    assert result["category_confidence"] == 0.5
