import operator
from pathlib import Path

import pandas as pd
import yaml


CONFIG_PATH = Path("screener_config.yaml")
DATA_PATH = Path("output/final_financial_ratios.csv")
MARKET_DATA_PATH = Path("data/raw/market_cap.xlsx")
PL_DATA_PATH = Path("data/processed/profitandloss_cleaned.csv")


OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def load_config(config_path=CONFIG_PATH):
    """Load screener configuration from YAML."""
    with open(config_path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_data(
    data_path=DATA_PATH,
    market_data_path=MARKET_DATA_PATH,
    pl_data_path=PL_DATA_PATH,
):
    """
    Load financial ratios and merge market and revenue data.

    Financial KPIs come from final_financial_ratios.csv.
    Valuation metrics come from market_cap.xlsx.
    Revenue comes from the cleaned P&L dataset.
    """

    # ---------------------------------------------------------
    # 1. Financial ratio data
    # ---------------------------------------------------------
    financial = pd.read_csv(data_path)

    # ---------------------------------------------------------
    # 2. Market / valuation data
    # ---------------------------------------------------------
    market = pd.read_excel(market_data_path)

    market_columns = [
        "company_id",
        "year",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "market_cap_crore",
        "enterprise_value_crore",
    ]

    available_market_columns = [
        column
        for column in market_columns
        if column in market.columns
    ]

    market = market[available_market_columns].copy()

    # Prevent duplicate company-year rows.
    market = market.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    result = financial.merge(
        market,
        on=["company_id", "year"],
        how="left",
    )

    # ---------------------------------------------------------
    # 3. Revenue from cleaned P&L
    # ---------------------------------------------------------
    pl = pd.read_csv(pl_data_path)

    if "sales" not in pl.columns:
        raise ValueError(
            "Cleaned P&L data must contain a 'sales' column."
        )

    revenue = pl[
        ["company_id", "year", "sales"]
    ].copy()

    revenue = revenue.rename(
        columns={"sales": "revenue_cr"}
    )

    revenue = revenue.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    result = result.merge(
        revenue,
        on=["company_id", "year"],
        how="left",
    )

    # ---------------------------------------------------------
    # 4. FCF Yield
    # ---------------------------------------------------------
    result["fcf_yield"] = (
        result["free_cash_flow_cr"]
        / result["market_cap_crore"]
        * 100
    )

    # Invalid / zero market cap cannot produce meaningful yield.
    result.loc[
        result["market_cap_crore"].isna()
        | result["market_cap_crore"].eq(0),
        "fcf_yield",
    ] = pd.NA

    return result


def apply_filters(df, filters):
    """
    Apply all configured filters using AND logic.

    Each filter must contain:
        metric
        operator
        value
    """

    result = df.copy()

    for item in filters:
        metric = item["metric"]
        op = item["operator"]
        value = item["value"]

        # -----------------------------------------------------
        # Validate metric
        # -----------------------------------------------------
        if metric not in result.columns:
            raise ValueError(
                f"Unknown screener metric '{metric}'. "
                f"Available columns: {', '.join(result.columns)}"
            )

        # -----------------------------------------------------
        # Validate operator
        # -----------------------------------------------------
        if op not in OPERATORS:
            raise ValueError(
                f"Unsupported operator '{op}'. "
                f"Supported operators: {', '.join(OPERATORS)}"
            )

        # -----------------------------------------------------
        # Apply filter
        # -----------------------------------------------------
        result = result[
            result[metric].notna()
            & OPERATORS[op](result[metric], value)
        ]

    return result


def run_screener(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """
    Run a named screener defined in screener_config.yaml.

    Special logic:
    turnaround_watch additionally requires
    current D/E to be lower than the previous
    available year for the same company.
    """

    # ---------------------------------------------------------
    # Load configuration
    # ---------------------------------------------------------
    config = load_config(config_path)

    # ---------------------------------------------------------
    # Load all screener data
    # ---------------------------------------------------------
    df = load_data(
        data_path=data_path,
        market_data_path=MARKET_DATA_PATH,
        pl_data_path=PL_DATA_PATH,
    )

    # ---------------------------------------------------------
    # Get configured screeners
    # ---------------------------------------------------------
    screeners = config.get("screeners", {})

    if name not in screeners:
        raise ValueError(
            f"Unknown screener '{name}'. "
            f"Available screeners: {', '.join(screeners)}"
        )

    # ---------------------------------------------------------
    # TURNAROUND WATCH:
    # Calculate previous-year D/E BEFORE applying filters.
    #
    # This is important because otherwise the previous value
    # could accidentally refer to the previous qualifying row
    # rather than the previous year.
    # ---------------------------------------------------------
    if name == "turnaround_watch":

        df = df.sort_values(
            ["company_id", "year"]
        ).copy()

        df["previous_debt_to_equity"] = (
            df.groupby("company_id")[
                "debt_to_equity"
            ].shift(1)
        )

    # ---------------------------------------------------------
    # Apply normal YAML filters
    # ---------------------------------------------------------
    filters = screeners[name].get("filters", [])

    result = apply_filters(
        df,
        filters,
    )

    # ---------------------------------------------------------
    # TURNAROUND WATCH:
    # Require current D/E < previous-year D/E
    # ---------------------------------------------------------
    if name == "turnaround_watch":

        result = result[
            result["previous_debt_to_equity"].notna()
            & result["debt_to_equity"].notna()
            & (
                result["debt_to_equity"]
                < result["previous_debt_to_equity"]
            )
        ].copy()

    return result


if __name__ == "__main__":

    results = run_screener(
        "quality_compounder"
    )

    print(
        f"Quality Compounder results: "
        f"{len(results)} company/year rows"
    )

    columns = [
        "company_id",
        "year",
        "return_on_equity_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
        "pe_ratio",
        "pb_ratio",
        "dividend_yield_pct",
        "revenue_cr",
        "fcf_yield",
    ]

    available = [
        column
        for column in columns
        if column in results.columns
    ]

    print(
        results[available].to_string(
            index=False
        )
    )