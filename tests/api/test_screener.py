from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_screener_min_roe():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": 15},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert float(company["roe"]) >= 15


def test_screener_invalid_min_roe():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": -1},
    )

    assert response.status_code == 400


def test_screener_invalid_max_de():
    response = client.get(
        "/api/v1/screener",
        params={"max_de": -1},
    )

    assert response.status_code == 400


def test_screener_invalid_max_pe():
    response = client.get(
        "/api/v1/screener",
        params={"max_pe": 0},
    )

    assert response.status_code == 400


def test_screener_combined_filters():
    response = client.get(
        "/api/v1/screener",
        params={
            "min_roe": 10,
            "max_de": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "count" in data
    assert "results" in data
