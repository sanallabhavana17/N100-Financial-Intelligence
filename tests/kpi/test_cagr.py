import pandas as pd

from src.analytics.cagr import (
    calculate_cagr,
    calculate_cagr_for_years,
    calculate_growth_metrics,
)


# ==========================================================
# ORIGINAL CAGR TESTS — 6
# ==========================================================


def test_cagr_normal_growth():
    cagr, flag = calculate_cagr(100, 150, 5)

    assert cagr is not None
    assert flag is None
    assert round(cagr, 2) == 8.45


def test_cagr_decline_to_loss():
    cagr, flag = calculate_cagr(100, -20, 5)

    assert cagr is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_turnaround():
    cagr, flag = calculate_cagr(-20, 100, 5)

    assert cagr is None
    assert flag == "TURNAROUND"


def test_cagr_both_negative():
    cagr, flag = calculate_cagr(-20, -30, 5)

    assert cagr is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_zero_base():
    cagr, flag = calculate_cagr(0, 100, 5)

    assert cagr is None
    assert flag == "ZERO_BASE"


def test_cagr_insufficient_years():
    cagr, flag = calculate_cagr(100, 150, 0)

    assert cagr is None
    assert flag == "INSUFFICIENT"


# ==========================================================
# DAY 10 — CAGR WINDOW TESTS — 4
# ==========================================================


def test_cagr_for_exact_historical_year():
    df = pd.DataFrame(
        {
            "company_id": ["TEST", "TEST"],
            "year": [2019, 2024],
            "sales": [100, 150],
            "net_profit": [10, 20],
            "eps": [5, 10],
        }
    )

    cagr, flag = calculate_cagr_for_years(
        df,
        "TEST",
        2024,
        "sales",
        5,
    )

    assert cagr is not None
    assert flag is None
    assert round(cagr, 2) == 8.45


def test_cagr_missing_historical_year():
    df = pd.DataFrame(
        {
            "company_id": ["TEST"],
            "year": [2024],
            "sales": [150],
        }
    )

    cagr, flag = calculate_cagr_for_years(
        df,
        "TEST",
        2024,
        "sales",
        5,
    )

    assert cagr is None
    assert flag == "INSUFFICIENT"


def test_growth_metrics_contains_all_windows():
    df = pd.DataFrame(
        {
            "company_id": ["TEST"] * 11,
            "year": list(range(2014, 2025)),
            "sales": [100 + i * 10 for i in range(11)],
            "net_profit": [10 + i for i in range(11)],
            "eps": [5 + i * 0.5 for i in range(11)],
        }
    )

    result = calculate_growth_metrics(
        df,
        "TEST",
        2024,
    )

    assert result["revenue_cagr_3yr"] is not None
    assert result["revenue_cagr_5yr"] is not None
    assert result["revenue_cagr_10yr"] is not None

    assert result["pat_cagr_3yr"] is not None
    assert result["pat_cagr_5yr"] is not None
    assert result["pat_cagr_10yr"] is not None

    assert result["eps_cagr_3yr"] is not None
    assert result["eps_cagr_5yr"] is not None
    assert result["eps_cagr_10yr"] is not None


def test_growth_metrics_turnaround_flag():
    df = pd.DataFrame(
        {
            "company_id": ["TEST", "TEST"],
            "year": [2019, 2024],
            "sales": [100, 150],
            "net_profit": [-20, 50],
            "eps": [-5, 10],
        }
    )

    result = calculate_growth_metrics(
        df,
        "TEST",
        2024,
    )

    assert result["pat_cagr_5yr"] is None
    assert result["pat_cagr_5yr_flag"] == "TURNAROUND"

    assert result["eps_cagr_5yr"] is None
    assert result["eps_cagr_5yr_flag"] == "TURNAROUND"