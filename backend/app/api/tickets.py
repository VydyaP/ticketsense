from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.ml.model import model_service
from backend.app.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from backend.app.services.ticket_service import TicketService

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket with automatic ML triage",
)
async def create_ticket(
    ticket_in: TicketCreate,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Create an IT support ticket, trigger ML prediction for category and priority, and persist."""
    ticket = await TicketService.create_ticket(db, ticket_in, model_service)
    return TicketResponse.model_validate(ticket)


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List tickets with filtering and pagination",
)
async def list_tickets(
    status: str | None = Query(
        None, description="Filter by status (open, in_progress, resolved, closed)"
    ),
    category: str | None = Query(None, description="Filter by category"),
    priority: str | None = Query(None, description="Filter by priority (Low, Medium, High)"),
    search: str | None = Query(None, description="Search keyword in title or description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> TicketListResponse:
    """Retrieve tickets matching filter criteria with pagination."""
    items, total, total_pages = await TicketService.get_tickets(
        db,
        status=status,
        category=category,
        priority=priority,
        search=search,
        page=page,
        page_size=page_size,
    )
    return TicketListResponse(
        items=[TicketResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get single ticket by ID",
)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Fetch details of a specific support ticket."""
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} was not found",
        )
    return TicketResponse.model_validate(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update ticket status or correct category",
)
async def update_ticket(
    ticket_id: int,
    update_in: TicketUpdate,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Update ticket workflow status or record human feedback correcting predicted category."""
    ticket = await TicketService.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} was not found",
        )
    updated = await TicketService.update_ticket(db, ticket, update_in)
    return TicketResponse.model_validate(updated)
