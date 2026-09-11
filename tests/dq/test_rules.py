import pandas as pd

from src.etl.validator import (
    validate_pk_uniqueness,
    validate_company_year_pk,
    validate_fk_integrity,
    validate_balance_sheet_balance,
    validate_opm_cross_check,
    validate_positive_sales,
    validate_year_format,
    validate_ticker_format,
    validate_net_cash,
    validate_fixed_assets,
    validate_tax_rate,
    validate_dividend_payout,
    validate_document_urls,
    validate_eps_sign,
)


def get_rule(failures):
    assert failures
    return failures[0]


def test_dq01_primary_key_uniqueness():
    df = pd.DataFrame({"id": ["TCS", "TCS"]})
    failures = []

    validate_pk_uniqueness(df, "companies", failures)

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-01"
    assert rule["severity"] == "CRITICAL"


def test_dq02_company_year_uniqueness():
    df = pd.DataFrame({
        "company_id": ["TCS", "TCS"],
        "year": ["2024-03", "2024-03"],
    })
    failures = []

    validate_company_year_pk(df, "profitandloss", failures)

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-02"
    assert rule["severity"] == "CRITICAL"


def test_dq03_foreign_key_integrity():
    companies = pd.DataFrame({
        "id": ["TCS", "INFY"],
    })

    child = pd.DataFrame({
        "company_id": ["TCS", "INVALID"],
    })

    failures = []

    validate_fk_integrity(
        child,
        companies,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-03"
    assert rule["severity"] == "CRITICAL"


def test_dq04_balance_sheet_balance():
    df = pd.DataFrame({
        "total_assets": [1000],
        "total_liabilities": [900],
    })

    failures = []

    validate_balance_sheet_balance(
        df,
        "balancesheet",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-04"
    assert rule["severity"] == "WARNING"


def test_dq05_opm_cross_check():
    df = pd.DataFrame({
        "sales": [1000],
        "operating_profit": [200],
        "opm_percentage": [50],
    })

    failures = []

    validate_opm_cross_check(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-05"
    assert rule["severity"] == "WARNING"


def test_dq06_positive_sales():
    df = pd.DataFrame({
        "sales": [1000, 0],
    })

    failures = []

    validate_positive_sales(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-06"
    assert rule["severity"] == "WARNING"


def test_dq07_year_format():
    df = pd.DataFrame({
        "year": ["2024-03", "INVALID_YEAR"],
    })

    failures = []

    validate_year_format(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-07"
    assert rule["severity"] == "CRITICAL"


def test_dq08_ticker_format():
    df = pd.DataFrame({
        "company_id": ["T", "THIS_TICKER_IS_TOO_LONG"],
    })

    failures = []

    validate_ticker_format(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-08"
    assert rule["severity"] == "CRITICAL"


def test_dq09_net_cash_check():
    df = pd.DataFrame({
        "net_cash_flow": [100],
        "operating_activity": [100],
        "investing_activity": [0],
        "financing_activity": [50],
    })

    failures = []

    validate_net_cash(
        df,
        "cashflow",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-09"
    assert rule["severity"] == "WARNING"


def test_dq10_non_negative_fixed_assets():
    df = pd.DataFrame({
        "fixed_assets": [-10],
    })

    failures = []

    validate_fixed_assets(
        df,
        "balancesheet",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-10"
    assert rule["severity"] == "WARNING"


def test_dq11_tax_rate_range():
    df = pd.DataFrame({
        "tax_percentage": [75],
    })

    failures = []

    validate_tax_rate(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-11"
    assert rule["severity"] == "WARNING"


def test_dq12_dividend_payout_cap():
    df = pd.DataFrame({
        "dividend_payout": [250],
    })

    failures = []

    validate_dividend_payout(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-12"
    assert rule["severity"] == "WARNING"


def test_dq13_document_url_validity():
    df = pd.DataFrame({
        "Annual_Report": [
            "https://example.com/report.pdf"
        ],
    })

    class FakeResponse:
        status_code = 404

    def fake_head(url, **kwargs):
        return FakeResponse()

    failures = []

    validate_document_urls(
        df,
        "documents",
        failures,
        request_head=fake_head,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-13"
    assert rule["severity"] == "WARNING"


def test_dq14_eps_sign_consistency():
    df = pd.DataFrame({
        "net_profit": [100],
        "eps": [-2],
    })

    failures = []

    validate_eps_sign(
        df,
        "profitandloss",
        failures,
    )

    rule = get_rule(failures)

    assert rule["rule_id"] == "DQ-14"
    assert rule["severity"] == "WARNING"
