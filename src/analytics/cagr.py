def calculate_cagr(start_value, end_value, years):
    """
    Calculate CAGR.

    Formula:
        ((end / start) ** (1 / years) - 1) * 100

    Returns:
        (cagr_value, flag)
    """

    if years is None or years <= 0:
        return None, "INSUFFICIENT"

    if start_value == 0:
        return None, "ZERO_BASE"

    if start_value > 0 and end_value > 0:
        cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
        return cagr, None

    if start_value > 0 and end_value < 0:
        return None, "DECLINE_TO_LOSS"

    if start_value < 0 and end_value > 0:
        return None, "TURNAROUND"

    if start_value < 0 and end_value < 0:
        return None, "BOTH_NEGATIVE"

    if end_value == 0:
        return None, "DECLINE_TO_LOSS"

    return None, "INSUFFICIENT"


def calculate_cagr_for_years(
    df,
    company_id,
    end_year,
    value_column,
    years,
):
    """
    Calculate CAGR for a company using an exact historical year.

    Example:
        end_year = 2024
        years = 5

    Requires data for:
        2019 -> 2024

    Returns:
        (cagr_value, flag)
    """

    start_year = end_year - years

    company_data = df[
        (df["company_id"] == company_id)
        & (df["year"].isin([start_year, end_year]))
    ].copy()

    if len(company_data) < 2:
        return None, "INSUFFICIENT"

    start_rows = company_data[company_data["year"] == start_year]
    end_rows = company_data[company_data["year"] == end_year]

    if start_rows.empty or end_rows.empty:
        return None, "INSUFFICIENT"

    start_value = start_rows.iloc[0][value_column]
    end_value = end_rows.iloc[0][value_column]

    if start_value is None or end_value is None:
        return None, "INSUFFICIENT"

    return calculate_cagr(
        start_value,
        end_value,
        years,
    )


def calculate_growth_metrics(df, company_id, end_year):
    """
    Calculate Revenue, PAT and EPS CAGR for 3Y, 5Y and 10Y.

    Returns a dictionary containing both CAGR values
    and their corresponding edge-case flags.
    """

    result = {}

    metrics = {
        "revenue": "sales",
        "pat": "net_profit",
        "eps": "eps",
    }

    windows = [3, 5, 10]

    for metric_name, column_name in metrics.items():

        for years in windows:

            value, flag = calculate_cagr_for_years(
                df=df,
                company_id=company_id,
                end_year=end_year,
                value_column=column_name,
                years=years,
            )

            result[f"{metric_name}_cagr_{years}yr"] = value
            result[f"{metric_name}_cagr_{years}yr_flag"] = flag

    return result