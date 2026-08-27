"""
CAGR Engine

Handles CAGR calculations for:
- Revenue
- Net Profit (PAT)
- EPS

Supported edge cases:
1. Positive -> Positive
2. Positive -> Negative
3. Negative -> Positive
4. Negative -> Negative
5. Zero base
6. Insufficient data
"""


def calculate_cagr(start_value, end_value, years):
    """
    Calculate CAGR.

    Formula:
        ((end / start) ** (1 / years) - 1) * 100

    Returns:
        (cagr_value, flag)

    Possible flags:
        None
        DECLINE_TO_LOSS
        TURNAROUND
        BOTH_NEGATIVE
        ZERO_BASE
        INSUFFICIENT
    """

    # ---------------------------------------------------------
    # 1. Validate number of years
    # ---------------------------------------------------------

    if years is None or years <= 0:
        return None, "INSUFFICIENT"

    # ---------------------------------------------------------
    # 2. Missing values
    # ---------------------------------------------------------

    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    # ---------------------------------------------------------
    # 3. Convert to float
    # ---------------------------------------------------------

    try:
        start_value = float(start_value)
        end_value = float(end_value)
    except (TypeError, ValueError):
        return None, "INSUFFICIENT"

    # ---------------------------------------------------------
    # 4. Zero base
    # ---------------------------------------------------------

    if start_value == 0:
        return None, "ZERO_BASE"

    # ---------------------------------------------------------
    # 5. Positive -> Positive
    # ---------------------------------------------------------

    if start_value > 0 and end_value > 0:

        cagr = (
            (end_value / start_value) ** (1 / years) - 1
        ) * 100

        return cagr, None

    # ---------------------------------------------------------
    # 6. Positive -> Negative
    # ---------------------------------------------------------

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    # ---------------------------------------------------------
    # 7. Negative -> Positive
    # ---------------------------------------------------------

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    # ---------------------------------------------------------
    # 8. Negative -> Negative
    # ---------------------------------------------------------

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    # ---------------------------------------------------------
    # 9. Remaining zero-end case
    # ---------------------------------------------------------

    return None, "INSUFFICIENT"


def revenue_cagr(start_revenue, end_revenue, years):
    """
    Revenue CAGR wrapper.
    """

    return calculate_cagr(
        start_revenue,
        end_revenue,
        years
    )


def pat_cagr(start_pat, end_pat, years):
    """
    PAT / Net Profit CAGR wrapper.
    """

    return calculate_cagr(
        start_pat,
        end_pat,
        years
    )


def eps_cagr(start_eps, end_eps, years):
    """
    EPS CAGR wrapper.
    """

    return calculate_cagr(
        start_eps,
        end_eps,
        years
    )

def calculate_cagr_for_years(
    df,
    company_id,
    end_year,
    value_column,
    years,
):
    """
    Calculate CAGR for a specific company and historical window.

    Parameters
    ----------
    df : pandas.DataFrame
        Data containing company_id, year and the requested value column.
    company_id : str
        Company identifier.
    end_year : int
        Ending year.
    value_column : str
        Column to calculate CAGR for.
    years : int
        Number of years in the CAGR window.

    Returns
    -------
    tuple
        (cagr_value, flag)
    """

    start_year = end_year - years

    company_data = df[
        (df["company_id"] == company_id)
        & (df["year"].isin([start_year, end_year]))
    ]

    # Both required years must exist
    if len(company_data) < 2:
        return None, "INSUFFICIENT"

    start_row = company_data[company_data["year"] == start_year]
    end_row = company_data[company_data["year"] == end_year]

    if start_row.empty or end_row.empty:
        return None, "INSUFFICIENT"

    start_value = start_row.iloc[0][value_column]
    end_value = end_row.iloc[0][value_column]

    return calculate_cagr(
        start_value,
        end_value,
        years,
    )


def calculate_growth_metrics(
    df,
    company_id,
    end_year,
):
    """
    Calculate 3-year, 5-year and 10-year CAGR metrics
    for revenue, PAT and EPS.
    """

    result = {}

    windows = {
        3: "",
        5: "",
        10: "",
    }

    metrics = {
        "sales": "revenue_cagr",
        "net_profit": "pat_cagr",
        "eps": "eps_cagr",
    }

    for years in windows:

        for source_column, output_name in metrics.items():

            value, flag = calculate_cagr_for_years(
                df,
                company_id,
                end_year,
                source_column,
                years,
            )

            result[f"{output_name}_{years}yr"] = value
            result[f"{output_name}_{years}yr_flag"] = flag

    return result
