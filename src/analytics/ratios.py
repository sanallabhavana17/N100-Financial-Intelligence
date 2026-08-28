def net_profit_margin(net_profit, sales):
    """
    Net Profit Margin = Net Profit / Sales × 100

    Returns None if sales = 0.
    """
    if sales == 0:
        return None

    return (net_profit / sales) * 100


def operating_profit_margin(operating_profit, sales):
    """
    Operating Profit Margin = Operating Profit / Sales × 100

    Returns None if sales = 0.
    """
    if sales == 0:
        return None

    return (operating_profit / sales) * 100


def check_opm_difference(computed_opm, source_opm):
    """
    Check difference between computed OPM and source OPM.

    Returns True when the difference is greater than
    1 percentage point.
    """
    if computed_opm is None or source_opm is None:
        return False

    return abs(computed_opm - source_opm) > 1


def return_on_equity(net_profit, equity_capital, reserves):
    """
    ROE = Net Profit / (Equity Capital + Reserves) × 100

    Returns None if equity + reserves <= 0.
    """
    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return (net_profit / equity) * 100


def return_on_capital_employed(
    ebit,
    equity_capital,
    reserves,
    borrowings
):
    """
    ROCE = EBIT / (Equity + Reserves + Borrowings) × 100

    Returns None if capital employed <= 0.
    """
    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed <= 0:
        return None

    return (ebit / capital_employed) * 100


def return_on_assets(net_profit, total_assets):
    """
    ROA = Net Profit / Total Assets × 100

    Returns None if total assets = 0.
    """
    if total_assets == 0:
        return None

    return (net_profit / total_assets) * 100


# ==========================================================
# DAY 09 — LEVERAGE & EFFICIENCY RATIOS
# ==========================================================


def debt_to_equity(
    borrowings,
    equity_capital,
    reserves
):
    """
    Debt-to-Equity = Borrowings / (Equity Capital + Reserves)

    Special rule:
    If borrowings = 0, return 0.

    If equity + reserves <= 0, return None.
    """
    if borrowings == 0:
        return 0

    equity = equity_capital + reserves

    if equity <= 0:
        return None

    return borrowings / equity


def high_leverage_flag(
    debt_equity,
    is_financials_sector
):
    """
    High leverage flag.

    D/E > 5 is considered high leverage.

    Financials companies are excluded because
    high leverage is structurally normal for banks,
    NBFCs and insurance companies.
    """
    if debt_equity is None:
        return False

    if is_financials_sector:
        return False

    return debt_equity > 5


def interest_coverage_ratio(
    operating_profit,
    other_income,
    interest
):
    """
    Interest Coverage Ratio (ICR)

    ICR = (Operating Profit + Other Income) / Interest

    Returns None when interest = 0.
    """
    if interest == 0:
        return None

    return (
        (operating_profit + other_income)
        / interest
    )


def icr_label(interest_coverage):
    """
    Display label for Interest Coverage Ratio.

    None or NaN means the company has no interest expense,
    therefore it is treated as Debt Free.
    """
    if interest_coverage is None:
        return "Debt Free"

    try:
        if interest_coverage != interest_coverage:
            return "Debt Free"
    except TypeError:
        return None

    return None


def icr_warning_flag(interest_coverage):
    """
    Warning flag when ICR < 1.5.

    True = company may have difficulty covering
    its interest payments.
    """
    if interest_coverage is None:
        return False

    return interest_coverage < 1.5


def net_debt(
    borrowings,
    investments
):
    """
    Net Debt = Borrowings - Investments

    Investments are used as a liquid asset proxy.
    """
    return borrowings - investments


def asset_turnover(
    sales,
    total_assets
):
    """
    Asset Turnover = Sales / Total Assets

    Returns None when total assets = 0.
    """
    if total_assets == 0:
        return None

    return sales / total_assets