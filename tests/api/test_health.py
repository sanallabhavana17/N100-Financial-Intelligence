from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_health_status():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


def test_health_database_counts():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    counts = response.json()["db_row_counts"]

    expected_tables = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
        "documents",
        "peer_groups",
        "peer_percentiles",
        "sectors",
    }

    assert set(counts) == expected_tables

    assert counts["companies"] == 92
    assert counts["financial_ratios"] > 0
    assert counts["market_cap"] > 0
    assert counts["sectors"] == 92
