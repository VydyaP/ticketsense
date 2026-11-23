from __future__ import annotations

from fastapi import APIRouter

from backend.app.ml.model import model_service
from backend.app.schemas.ticket import PredictionRequest, PredictionResponse

router = APIRouter(prefix="/api/predict", tags=["Prediction"])


@router.post(
    "",
    response_model=PredictionResponse,
    summary="Predict ticket category and priority without persisting",
)
async def predict_ticket(request_in: PredictionRequest) -> PredictionResponse:
    """Run real-time inference on ticket title and description without storing in the database."""
    result = model_service.predict(request_in.title, request_in.description)
    return PredictionResponse(
        category=result["category"],
        category_confidence=result["category_confidence"],
        category_probabilities=result["category_probabilities"],
        priority=result["priority"],
        priority_confidence=result["priority_confidence"],
        priority_probabilities=result["priority_probabilities"],
    )
