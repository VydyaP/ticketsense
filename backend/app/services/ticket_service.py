from __future__ import annotations

import math
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.metrics import TICKET_CORRECTIONS_TOTAL, TICKET_PREDICTIONS_TOTAL
from backend.app.ml.model import ModelService
from backend.app.models.ticket import Ticket
from backend.app.schemas.ticket import TicketCreate, TicketUpdate


class TicketService:
    """Service handling ticket database operations and model integration."""

    @staticmethod
    async def create_ticket(
        db: AsyncSession, ticket_in: TicketCreate, ml_service: ModelService
    ) -> Ticket:
        """Predict triage labels, persist new ticket, and record metrics."""
        prediction = ml_service.predict(ticket_in.title, ticket_in.description)

        ticket = Ticket(
            title=ticket_in.title.strip(),
            description=ticket_in.description.strip(),
            status="open",
            predicted_category=prediction["category"],
            category_confidence=prediction["category_confidence"],
            predicted_priority=prediction["priority"],
            priority_confidence=prediction["priority_confidence"],
            category_probabilities=prediction["category_probabilities"],
            priority_probabilities=prediction["priority_probabilities"],
            corrected_category=None,
        )

        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)

        # Track prediction metric
        TICKET_PREDICTIONS_TOTAL.labels(
            category=ticket.predicted_category,
            priority=ticket.predicted_priority,
        ).inc()

        return ticket

    @staticmethod
    async def get_ticket(db: AsyncSession, ticket_id: int) -> Ticket | None:
        """Fetch a single ticket by its primary key."""
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_tickets(
        db: AsyncSession,
        status: str | None = None,
        category: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Ticket], int, int]:
        """Retrieve paginated and filtered list of tickets."""
        stmt = select(Ticket)

        if status:
            stmt = stmt.where(Ticket.status == status)

        if category:
            # Check either predicted or corrected
            stmt = stmt.where(
                or_(
                    Ticket.corrected_category == category,
                    (Ticket.corrected_category.is_(None) & (Ticket.predicted_category == category)),
                )
            )

        if priority:
            stmt = stmt.where(Ticket.predicted_priority == priority)

        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(Ticket.title.ilike(pattern), Ticket.description.ilike(pattern)))

        # Count total matching
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        total_pages = max(1, math.ceil(total / page_size))
        offset = (page - 1) * page_size

        # Order by newest first
        stmt = stmt.order_by(Ticket.created_at.desc()).offset(offset).limit(page_size)
        items = list((await db.execute(stmt)).scalars().all())

        return items, total, total_pages

    @staticmethod
    async def update_ticket(db: AsyncSession, ticket: Ticket, update_in: TicketUpdate) -> Ticket:
        """Update ticket status and/or category feedback."""
        if update_in.status is not None:
            ticket.status = update_in.status

        if update_in.corrected_category is not None:
            ticket.corrected_category = update_in.corrected_category

            # Track human correction metric
            TICKET_CORRECTIONS_TOTAL.labels(
                original_category=ticket.predicted_category,
                corrected_category=ticket.corrected_category,
            ).inc()

        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict[str, Any]:
        """Compute aggregate ticket counts and model feedback metrics."""
        # Status counts
        status_stmt = select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
        status_results = (await db.execute(status_stmt)).all()
        status_counts = dict(status_results)

        # Category counts (using effective category logic)
        effective_cat_expr = func.coalesce(Ticket.corrected_category, Ticket.predicted_category)
        cat_stmt = select(effective_cat_expr, func.count(Ticket.id)).group_by(effective_cat_expr)
        cat_results = (await db.execute(cat_stmt)).all()
        category_counts = {cat: count for cat, count in cat_results if cat}

        # Priority counts
        prio_stmt = select(Ticket.predicted_priority, func.count(Ticket.id)).group_by(
            Ticket.predicted_priority
        )
        prio_results = (await db.execute(prio_stmt)).all()
        priority_counts = dict(prio_results)

        # Total counts & corrections
        total_stmt = select(func.count(Ticket.id))
        total_tickets = (await db.execute(total_stmt)).scalar_one()

        corrections_stmt = select(func.count(Ticket.id)).where(
            Ticket.corrected_category.isnot(None)
        )
        total_corrections = (await db.execute(corrections_stmt)).scalar_one()

        # Share of tickets whose predicted category nobody has corrected. This is NOT
        # accuracy: an uncorrected ticket may simply not have been reviewed yet.
        uncorrected_rate = (
            round((total_tickets - total_corrections) / total_tickets * 100, 1)
            if total_tickets
            else None
        )

        return {
            "total_tickets": total_tickets,
            "total_corrections": total_corrections,
            "uncorrected_rate": uncorrected_rate,
            "status_counts": status_counts,
            "category_counts": category_counts,
            "priority_counts": priority_counts,
        }
