from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
)


def test_debt_to_equity_normal():
    result = debt_to_equity(200, 100, 100)
    assert result == 1.0


def test_debt_to_equity_debt_free_returns_zero():
    result = debt_to_equity(0, 100, 50)
    assert result == 0


def test_debt_to_equity_negative_equity():
    result = debt_to_equity(100, -100, 50)
    assert result is None


def test_interest_coverage_normal():
    result = interest_coverage_ratio(100, 20, 20)
    assert result == 6.0


def test_interest_coverage_zero_interest():
    result = interest_coverage_ratio(100, 20, 0)
    assert result is None


def test_icr_label_debt_free():
    result = icr_label(None)
    assert result == "Debt Free"


def test_high_debt_to_equity_flag():
    result = high_leverage_flag(6, False)
    assert result is True


def test_financials_high_leverage_suppressed():
    result = high_leverage_flag(6, True)
    assert result is False