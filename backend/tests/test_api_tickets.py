"""API tests for ticket endpoints, run against a real PostgreSQL database."""

from __future__ import annotations

from httpx import AsyncClient

from backend.app.ml.model import model_service

CATEGORIES = model_service.categories


async def create(client: AsyncClient, title: str, description: str) -> dict:
    response = await client.post("/api/tickets", json={"title": title, "description": description})
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_ticket_stores_prediction(client: AsyncClient):
    data = await create(client, "Need second monitor", "Please provide a 27 inch monitor.")

    assert data["id"] == 1
    assert data["status"] == "open"
    assert data["predicted_category"] in CATEGORIES
    assert data["predicted_priority"] in ("High", "Medium", "Low")
    assert 0.0 <= data["category_confidence"] <= 1.0
    assert data["effective_category"] == data["predicted_category"]
    assert data["corrected_category"] is None

    # Round-trip through the database.
    fetched = await client.get(f"/api/tickets/{data['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["category_probabilities"] == data["category_probabilities"]


async def test_create_ticket_validation(client: AsyncClient):
    too_short_title = await client.post(
        "/api/tickets", json={"title": "hi", "description": "valid description"}
    )
    assert too_short_title.status_code == 422

    missing_field = await client.post("/api/tickets", json={"title": "Valid title"})
    assert missing_field.status_code == 422


async def test_get_missing_ticket_returns_404(client: AsyncClient):
    response = await client.get("/api/tickets/999")
    assert response.status_code == 404
    assert "999" in response.json()["detail"]


async def test_list_filter_search_and_paginate(client: AsyncClient):
    await create(client, "VPN disconnects", "Connection to the server keeps dropping")
    await create(client, "Password expired", "Cannot log in to my account")
    monitor = await create(client, "Monitor flickering", "Screen flickers all day")

    everything = (await client.get("/api/tickets")).json()
    assert everything["total"] == 3
    assert everything["items"][0]["id"] == monitor["id"]  # newest first

    search = (await client.get("/api/tickets", params={"search": "monitor"})).json()
    assert search["total"] == 1  # ILIKE: case-insensitive

    page = (await client.get("/api/tickets", params={"page": 2, "page_size": 2})).json()
    assert page["total_pages"] == 2
    assert len(page["items"]) == 1

    by_category = (
        await client.get("/api/tickets", params={"category": monitor["predicted_category"]})
    ).json()
    assert monitor["id"] in [t["id"] for t in by_category["items"]]

    bad_filter = await client.get("/api/tickets", params={"status": "nonsense"})
    assert bad_filter.status_code == 422


async def test_update_status_and_correct_category(client: AsyncClient):
    ticket = await create(client, "Wi-Fi keeps dropping", "Signal drops near room B")
    url = f"/api/tickets/{ticket['id']}"

    response = await client.patch(url, json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    other = next(c for c in CATEGORIES if c != ticket["predicted_category"])
    response = await client.patch(url, json={"corrected_category": other})
    assert response.status_code == 200
    assert response.json()["corrected_category"] == other
    assert response.json()["effective_category"] == other
    assert response.json()["predicted_category"] == ticket["predicted_category"]  # kept

    # The filter uses the corrected category once a human has fixed it.
    filtered = (await client.get("/api/tickets", params={"category": other})).json()
    assert [t["id"] for t in filtered["items"]] == [ticket["id"]]


async def test_update_validation(client: AsyncClient):
    ticket = await create(client, "Printer jam", "Printer on floor 2 jams")
    url = f"/api/tickets/{ticket['id']}"

    assert (await client.patch(url, json={"status": "banana"})).status_code == 422
    unknown = await client.patch(url, json={"corrected_category": "Not A Category"})
    assert unknown.status_code == 422
    assert "Valid categories" in unknown.json()["detail"]
    assert (await client.patch(url, json={})).status_code == 422
    assert (await client.patch("/api/tickets/999", json={"status": "resolved"})).status_code == 404


async def test_predict_does_not_save(client: AsyncClient):
    response = await client.post(
        "/api/predict",
        json={"title": "Need admin rights", "description": "Please grant local admin access"},
    )
    assert response.status_code == 200
    assert response.json()["category"] in CATEGORIES
    assert (await client.get("/api/tickets")).json()["total"] == 0
