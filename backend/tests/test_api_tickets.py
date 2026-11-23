from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_predict_ticket(client: AsyncClient):
    """Test ticket creation persists ticket and performs ML classification."""
    payload = {
        "title": "Need second monitor for remote desk setup",
        "description": "Please approve purchase of a 27 inch Dell monitor and HDMI display cable.",
    }
    response = await client.post("/api/tickets", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["status"] == "open"
    assert data["predicted_category"] in (
        "Hardware",
        "Access/Account",
        "Network",
        "Facilities",
        "Other",
        "Software",
    )
    assert 0.0 <= data["category_confidence"] <= 1.0
    assert data["predicted_priority"] in ("High", "Medium", "Low")
    assert 0.0 <= data["priority_confidence"] <= 1.0
    assert data["effective_category"] == data["predicted_category"]
    assert data["corrected_category"] is None


@pytest.mark.asyncio
async def test_ticket_validation_errors(client: AsyncClient):
    """Test input validation for invalid or too-short tickets."""
    # Title too short
    response = await client.post(
        "/api/tickets", json={"title": "hi", "description": "Too short title"}
    )
    assert response.status_code == 422

    # Description too short
    response = await client.post(
        "/api/tickets", json={"title": "Valid title here", "description": "bad"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_and_filter_tickets(client: AsyncClient):
    """Test listing tickets with pagination and filtering."""
    # Create 3 tickets
    t1 = await client.post(
        "/api/tickets", json={"title": "VPN disconnects", "description": "Network gateway issue"}
    )
    t2 = await client.post(
        "/api/tickets",
        json={"title": "Password expired", "description": "Cannot login to email account"},
    )
    t3 = await client.post(
        "/api/tickets",
        json={"title": "Monitor flickering", "description": "Hardware cable replacement required"},
    )

    assert t1.status_code == 201
    assert t2.status_code == 201
    assert t3.status_code == 201

    # List all
    response = await client.get("/api/tickets")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Search filter
    search_resp = await client.get("/api/tickets?search=Monitor")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert "Monitor" in search_data["items"][0]["title"]


@pytest.mark.asyncio
async def test_update_ticket_status_and_category_feedback(client: AsyncClient):
    """Test updating ticket workflow status and recording human category correction."""
    # Create ticket
    create_resp = await client.post(
        "/api/tickets",
        json={
            "title": "Wi-Fi keeps dropping on floor 3",
            "description": "Signal drops intermittently near conference room B.",
        },
    )
    ticket_id = create_resp.json()["id"]

    # 1. Update status to in_progress
    patch_resp = await client.patch(f"/api/tickets/{ticket_id}", json={"status": "in_progress"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "in_progress"

    # 2. Correct category (human feedback)
    feedback_resp = await client.patch(
        f"/api/tickets/{ticket_id}", json={"corrected_category": "Network"}
    )
    assert feedback_resp.status_code == 200
    data = feedback_resp.json()
    assert data["corrected_category"] == "Network"
    assert data["effective_category"] == "Network"

    # 3. Invalid status pattern returns 422
    bad_resp = await client.patch(f"/api/tickets/{ticket_id}", json={"status": "invalid_status"})
    assert bad_resp.status_code == 422

    # 4. Non-existent ticket returns 404
    missing_resp = await client.patch("/api/tickets/99999", json={"status": "resolved"})
    assert missing_resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_endpoint_without_saving(client: AsyncClient):
    """Test POST /api/predict returns predictions without creating records in database."""
    payload = {
        "title": "Need administrator rights to install Docker Desktop",
        "description": "Please grant local administrative access to install container tools on developer laptop.",
    }
    response = await client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["category"] in (
        "Access/Account",
        "Hardware",
        "Network",
        "Facilities",
        "Other",
        "Software",
    )
    assert 0.0 <= data["category_confidence"] <= 1.0
    assert data["priority"] in ("High", "Medium", "Low")
    assert 0.0 <= data["priority_confidence"] <= 1.0

    # Ensure no tickets were persisted
    list_resp = await client.get("/api/tickets")
    assert list_resp.json()["total"] == 0
