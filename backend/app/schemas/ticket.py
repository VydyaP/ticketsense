from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TicketCreate(BaseModel):
    """Schema for submitting a new IT support ticket."""

    title: str = Field(..., min_length=3, max_length=200, description="Short summary of issue")
    description: str = Field(
        ..., min_length=5, max_length=5000, description="Detailed problem description"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "VPN connection drops every 5 minutes",
                "description": "Whenever I connect to the office global gateway, pulse secure disconnects after a few minutes and drops my SSH session to staging.",
            }
        }
    )


class TicketUpdate(BaseModel):
    """Schema for updating ticket status or correcting ticket category."""

    status: str | None = Field(
        None,
        description="Ticket status: 'open', 'in_progress', 'resolved', 'closed'",
        pattern="^(open|in_progress|resolved|closed)$",
    )
    corrected_category: str | None = Field(
        None,
        description="Corrected category provided as human triage feedback",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "in_progress",
                "corrected_category": "Network",
            }
        }
    )


class TicketResponse(BaseModel):
    """Schema for ticket details returned by the API."""

    id: int
    title: str
    description: str
    status: str
    predicted_category: str
    category_confidence: float
    predicted_priority: str
    priority_confidence: float
    corrected_category: str | None = None
    effective_category: str
    category_probabilities: dict[str, float] | None = None
    priority_probabilities: dict[str, float] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    """Paginated response for tickets listing."""

    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PredictionRequest(BaseModel):
    """Schema for on-the-fly triage prediction without persisting to database."""

    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=5, max_length=5000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Need 2FA hardware token replaced",
                "description": "My Yubikey was accidentally cracked during my commute and is not recognized by USB.",
            }
        }
    )


class PredictionResponse(BaseModel):
    """Schema for triage predictions."""

    category: str
    category_confidence: float
    category_probabilities: dict[str, float]
    priority: str
    priority_confidence: float
    priority_probabilities: dict[str, float]


class TicketStats(BaseModel):
    """Aggregated statistics for dashboard."""

    total_tickets: int
    total_corrections: int
    feedback_accuracy_rate: float
    status_counts: dict[str, int]
    category_counts: dict[str, int]
    priority_counts: dict[str, int]


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    database: str
    model_loaded: bool
    version: str
    timestamp: datetime
