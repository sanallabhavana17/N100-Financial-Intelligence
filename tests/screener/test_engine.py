import pandas as pd
import pytest

from src.screener.engine import apply_filters


def test_greater_than_filter():
    df = pd.DataFrame({"roe": [10, 20, 30]})

    result = apply_filters(df, [
        {"metric": "roe", "operator": ">", "value": 15}
    ])

    assert result["roe"].tolist() == [20, 30]


def test_less_than_filter():
    df = pd.DataFrame({"de": [0.5, 1.0, 2.0]})

    result = apply_filters(df, [
        {"metric": "de", "operator": "<", "value": 1}
    ])

    assert result["de"].tolist() == [0.5]


def test_multiple_filters_use_and_logic():
    df = pd.DataFrame({
        "roe": [10, 20, 30],
        "de": [0.5, 0.5, 2.0],
    })

    result = apply_filters(df, [
        {"metric": "roe", "operator": ">", "value": 15},
        {"metric": "de", "operator": "<", "value": 1},
    ])

    assert result["roe"].tolist() == [20]
    assert result["de"].tolist() == [0.5]


def test_null_values_are_excluded():
    df = pd.DataFrame({"roe": [20, None, 30]})

    result = apply_filters(df, [
        {"metric": "roe", "operator": ">", "value": 15}
    ])

    assert len(result) == 2


def test_unknown_metric_raises_error():
    df = pd.DataFrame({"roe": [20, 30]})

    with pytest.raises(ValueError, match="Unknown screener metric"):
        apply_filters(df, [
            {"metric": "does_not_exist", "operator": ">", "value": 15}
        ])


def test_unknown_operator_raises_error():
    df = pd.DataFrame({"roe": [20, 30]})

    with pytest.raises(ValueError, match="Unsupported operator"):
        apply_filters(df, [
            {"metric": "roe", "operator": "LIKE", "value": 15}
        ])


def test_fcf_yield_is_calculated():
    from src.screener.engine import load_data

    df = load_data()

    assert "fcf_yield" in df.columns

    sample = df.dropna(
        subset=["free_cash_flow_cr", "market_cap_crore", "fcf_yield"]
    ).iloc[0]

    expected = (
        sample["free_cash_flow_cr"]
        / sample["market_cap_crore"]
        * 100
    )

    assert abs(sample["fcf_yield"] - expected) < 1e-9


def test_revenue_cr_is_loaded_from_sales():
    from src.screener.engine import load_data

    df = load_data()

    assert "revenue_cr" in df.columns

    sample = df.dropna(subset=["revenue_cr"]).iloc[0]

    assert sample["revenue_cr"] > 0


def test_all_six_presets_exist():
    from src.screener.engine import load_config

    config = load_config()
    screeners = config["screeners"]

    expected = {
        "quality_compounder",
        "value_pick",
        "growth_accelerator",
        "dividend_champion",
        "debt_free_blue_chip",
        "turnaround_watch",
    }

    assert expected.issubset(screeners.keys())


def test_quality_compounder_filters():
    from src.screener.engine import run_screener

    result = run_screener("quality_compounder")

    assert len(result) > 0
    assert (result["return_on_equity_pct"] > 15).all()
    assert (result["debt_to_equity"] < 1).all()
    assert (result["free_cash_flow_cr"] > 0).all()
    assert (result["revenue_cagr_5yr"] > 10).all()


def test_value_pick_filters():
    from src.screener.engine import run_screener

    result = run_screener("value_pick")

    assert len(result) > 0
    assert (result["pe_ratio"] < 20).all()
    assert (result["pb_ratio"] < 3).all()
    assert (result["debt_to_equity"] < 2).all()
    assert (result["dividend_yield_pct"] > 1).all()


def test_growth_accelerator_filters():
    from src.screener.engine import run_screener

    result = run_screener("growth_accelerator")

    assert len(result) > 0
    assert (result["pat_cagr_5yr"] > 20).all()
    assert (result["revenue_cagr_5yr"] > 15).all()
    assert (result["debt_to_equity"] < 2).all()


def test_dividend_champion_filters():
    from src.screener.engine import run_screener

    result = run_screener("dividend_champion")

    assert len(result) > 0
    assert (result["dividend_yield_pct"] > 2).all()
    assert (result["dividend_payout_ratio_pct"] < 80).all()
    assert (result["free_cash_flow_cr"] > 0).all()


def test_debt_free_blue_chip_filters():
    from src.screener.engine import run_screener

    result = run_screener("debt_free_blue_chip")

    assert len(result) > 0
    assert (result["debt_to_equity"] == 0).all()
    assert (result["return_on_equity_pct"] > 12).all()
    assert (result["revenue_cr"] > 5000).all()
