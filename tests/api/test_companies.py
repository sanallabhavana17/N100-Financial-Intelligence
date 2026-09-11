from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_companies_returns_92():
    response = client.get("/api/v1/companies")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 92
    assert len(data["companies"]) == 92


def test_tcs_company_profile():
    response = client.get("/api/v1/companies/TCS")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["company_name"]


def test_invalid_company_returns_404():
    response = client.get("/api/v1/companies/INVALID")

    assert response.status_code == 404


def test_tcs_profit_and_loss():
    response = client.get("/api/v1/companies/TCS/pl")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0
    assert len(data["profit_and_loss"]) == data["count"]


def test_tcs_balance_sheet():
    response = client.get("/api/v1/companies/TCS/bs")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0


def test_tcs_cashflow():
    response = client.get("/api/v1/companies/TCS/cashflow")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0


def test_tcs_ratios():
    response = client.get("/api/v1/companies/TCS/ratios")

    assert response.status_code == 200

    data = response.json()

    assert data["company_id"] == "TCS"
    assert data["count"] > 0
