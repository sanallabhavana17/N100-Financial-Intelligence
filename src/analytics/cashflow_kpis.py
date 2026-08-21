def free_cash_flow(operating_activity, investing_activity):
    """
    Free Cash Flow = Operating Activity + Investing Activity

    Negative FCF is allowed.
    """
    return operating_activity + investing_activity


def cfo_quality_score(cfo, pat):
    """
    CFO Quality = CFO / PAT

    Returns:
        > 1.0       -> High Quality
        0.5 to 1.0  -> Moderate
        < 0.5       -> Accrual Risk

    Returns None if PAT = 0.

    The function returns:
        (ratio, label)
    """
    if pat == 0:
        return None, None

    ratio = cfo / pat

    if ratio > 1.0:
        label = "High Quality"
    elif ratio >= 0.5:
        label = "Moderate"
    else:
        label = "Accrual Risk"

    return ratio, label


def capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(Investing Activity) / Sales × 100

    < 3%       -> Asset Light
    3% to 8%   -> Moderate
    > 8%       -> Capital Intensive

    Returns None if sales = 0.

    The function returns:
        (percentage, label)
    """
    if sales == 0:
        return None, None

    percentage = abs(investing_activity) / sales * 100

    if percentage < 3:
        label = "Asset Light"
    elif percentage <= 8:
        label = "Moderate"
    else:
        label = "Capital Intensive"

    return percentage, label


def fcf_conversion_rate(fcf, operating_profit):
    """
    FCF Conversion Rate = FCF / Operating Profit × 100

    Returns None if operating profit = 0.
    """
    if operating_profit == 0:
        return None

    return (fcf / operating_profit) * 100


def capital_allocation_pattern(cfo, cfi, cff, cfo_pat_ratio=None):
    """
    Classify capital allocation based on the signs of:

        CFO = Cash Flow from Operations
        CFI = Cash Flow from Investing
        CFF = Cash Flow from Financing

    Patterns:

        (+,-,-) -> Reinvestor
        (+,-,-) with high CFO/PAT -> Shareholder Returns
        (+,+,-) -> Liquidating Assets
        (-,+,+) -> Distress Signal
        (-,-,+) -> Growth Funded by Debt
        (+,+,+) -> Cash Accumulator
        (-,-,-) -> Pre-Revenue
        (+,-,+) -> Mixed
    """

    def sign(value):
        if value > 0:
            return "+"
        elif value < 0:
            return "-"
        else:
            return "0"

    pattern = (sign(cfo), sign(cfi), sign(cff))

    # Special case:
    # (+,-,-) with high CFO/PAT ratio = Shareholder Returns
    if pattern == ("+", "-", "-"):
        if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
            return "Shareholder Returns"
        return "Reinvestor"

    labels = {
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }

    return labels.get(pattern, "Mixed")