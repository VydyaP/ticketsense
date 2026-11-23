"""Tests for monitoring endpoints, dashboard stats and model metrics."""

from __future__ import annotations

from httpx import AsyncClient

from backend.app.ml.model import model_service


async def test_health_reports_db_and_model(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["model_loaded"] is True


async def test_request_id_header(client: AsyncClient):
    generated = await client.get("/")
    assert generated.headers["X-Request-ID"]

    echoed = await client.get("/", headers={"X-Request-ID": "trace-123"})
    assert echoed.headers["X-Request-ID"] == "trace-123"


async def test_prometheus_metrics(client: AsyncClient):
    await client.post(
        "/api/tickets", json={"title": "Monitor broken", "description": "No display at all"}
    )
    await client.get("/api/tickets/12345")

    body = (await client.get("/metrics")).text
    assert "ticketsense_http_requests_total" in body
    assert "ticketsense_http_request_duration_seconds_bucket" in body
    assert "ticketsense_ticket_predictions_total{" in body
    # Paths are labelled by route template, not raw IDs (keeps label count bounded).
    assert 'endpoint="/api/tickets/{ticket_id}"' in body
    assert 'endpoint="/api/tickets/12345"' not in body


async def test_stats(client: AsyncClient):
    await client.post(
        "/api/tickets", json={"title": "Monitor dead", "description": "Screen will not turn on"}
    )
    second = await client.post(
        "/api/tickets", json={"title": "Badge lost", "description": "I lost my access card"}
    )
    await client.patch(
        f"/api/tickets/{second.json()['id']}",
        json={"corrected_category": model_service.categories[0], "status": "resolved"},
    )

    stats = (await client.get("/api/stats")).json()
    assert stats["total_tickets"] == 2
    assert stats["total_corrections"] == 1
    assert stats["status_counts"] == {"open": 1, "resolved": 1}
    assert sum(stats["category_counts"].values()) == 2
    assert sum(stats["priority_counts"].values()) == 2


async def test_model_metrics_endpoint(client: AsyncClient):
    metrics = (await client.get("/api/model/metrics")).json()
    assert metrics["category_model"]["classes"] == model_service.categories
    # The trained model must beat the "always predict the biggest class" baseline.
    cat = metrics["category_model"]
    assert cat["macro_f1"] > cat["baseline_majority_class"]["macro_f1"]
