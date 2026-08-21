from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


def test_free_cash_flow():
    assert free_cash_flow(100, -40) == 60


def test_free_cash_flow_negative():
    assert free_cash_flow(50, -100) == -50


def test_cfo_quality_high():
    score, label = cfo_quality_score(120, 100)
    assert score == 1.2
    assert label == "High Quality"


def test_cfo_quality_zero_pat():
    assert cfo_quality_score(100, 0) == (None, None)


def test_capex_intensity_moderate():
    value, label = capex_intensity(-50, 1000)
    assert value == 5.0
    assert label == "Moderate"


def test_capex_intensity_zero_sales():
    assert capex_intensity(-50, 0) == (None, None)


def test_fcf_conversion():
    assert fcf_conversion_rate(60, 100) == 60.0


def test_fcf_conversion_zero_operating_profit():
    assert fcf_conversion_rate(60, 0) is None


def test_capital_allocation_shareholder_returns():
    assert (
        capital_allocation_pattern(100, -50, -30, 1.2)
        == "Shareholder Returns"
    )


def test_capital_allocation_reinvestor():
    assert (
        capital_allocation_pattern(100, -50, -30, 0.8)
        == "Reinvestor"
    )