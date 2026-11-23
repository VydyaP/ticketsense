from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Ticket(Base):
    """SQLAlchemy model representing an IT Support Ticket and its ML triage metadata."""

    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Status: 'open', 'in_progress', 'resolved', 'closed'
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", index=True)

    # ML Predictions & Confidence
    predicted_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_priority: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    priority_confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Human feedback correction (null if category was accepted as-is)
    corrected_category: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    # Detailed probability distributions
    category_probabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    priority_probabilities: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_tickets_status_priority", "status", "predicted_priority"),
        Index("ix_tickets_created_at", "created_at"),
    )

    @property
    def effective_category(self) -> str:
        """Returns corrected category if updated by an agent, else the ML predicted category."""
        return self.corrected_category or self.predicted_category
