from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    return_on_assets,
)


def test_net_profit_margin_normal():
    result = net_profit_margin(100, 1000)
    assert result == 10


def test_net_profit_margin_zero_sales():
    result = net_profit_margin(100, 0)
    assert result is None


def test_operating_profit_margin_normal():
    result = operating_profit_margin(200, 1000)
    assert result == 20


def test_opm_cross_check_match():
    computed = operating_profit_margin(200, 1000)
    assert check_opm_difference(computed, 20) is False


def test_opm_cross_check_mismatch():
    computed = operating_profit_margin(200, 1000)
    assert check_opm_difference(computed, 22) is True


def test_roe_normal():
    result = return_on_equity(
        net_profit=100,
        equity_capital=200,
        reserves=300
    )
    assert result == 20


def test_roe_negative_equity():
    result = return_on_equity(
        net_profit=100,
        equity_capital=-500,
        reserves=100
    )
    assert result is None


def test_roa_zero_assets():
    result = return_on_assets(
        net_profit=100,
        total_assets=0
    )
    assert result is None