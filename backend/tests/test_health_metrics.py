from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Test GET /health returns 200 healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["model_loaded"] is True
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient):
    """Test GET /metrics returns standard Prometheus metrics exposition format."""
    # Trigger an API request first so metrics are populated
    await client.get("/")

    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "ticketsense_http_requests_total" in body
    assert "ticketsense_ticket_predictions_total" in body


@pytest.mark.asyncio
async def test_stats_and_model_metrics(client: AsyncClient):
    """Test GET /api/stats and GET /api/model/metrics endpoints."""
    # Create two tickets: one unmodified, one with corrected category
    await client.post(
        "/api/tickets",
        json={"title": "Monitor dead", "description": "Cannot turn on screen after power surge."},
    )
    t2 = await client.post(
        "/api/tickets",
        json={"title": "Badge access", "description": "Need building access card activated."},
    )
    t2_id = t2.json()["id"]

    # Provide category feedback on t2
    await client.patch(f"/api/tickets/{t2_id}", json={"corrected_category": "Facilities"})

    # Check stats endpoint
    stats_resp = await client.get("/api/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_tickets"] == 2
    assert stats["total_corrections"] == 1
    assert stats["feedback_accuracy_rate"] == 50.0
    assert "open" in stats["status_counts"]

    # Check model metrics endpoint
    metrics_resp = await client.get("/api/model/metrics")
    assert metrics_resp.status_code == 200
    metrics = metrics_resp.json()
    assert "dataset" in metrics
    assert "category_model" in metrics
    assert "priority_model" in metrics
    assert metrics["category_model"]["accuracy"] > 0.70
