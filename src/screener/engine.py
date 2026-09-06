import sqlite3
import operator
from pathlib import Path

import pandas as pd
import yaml


CONFIG_PATH = Path("config/screener_config.yaml")
DB_PATH = Path("data/nifty100.db")
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


# ------------------------------------------------------------------
# Sprint 3 - Day 15 supported screener metrics
# ------------------------------------------------------------------

FILTERABLE_METRICS = {
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
    "interest_coverage",
    "market_cap_crore",
    "net_profit",
    "eps_cagr_5yr",
    "asset_turnover",
    "revenue_cr",
}

def load_sector_data():
    """
    Load company-to-sector mapping from the SQLite database.
    Used for sector-relative ranking and Financials D/E handling.
    """
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["company_id", "broad_sector"])

    try:
        with sqlite3.connect(DB_PATH) as conn:
            return pd.read_sql_query(
                """
                SELECT company_id, broad_sector
                FROM sectors
                """,
                conn,
            )
    except Exception:
        return pd.DataFrame(columns=["company_id", "broad_sector"])

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
    # ---------------------------------------------------------
    # 3. Revenue and Net Profit from cleaned P&L
    # ---------------------------------------------------------
    pl = pd.read_csv(pl_data_path)

    required_pl_columns = [
        "company_id",
        "year",
        "sales",
        "net_profit",
    ]

    missing_pl_columns = [
        column
        for column in required_pl_columns
        if column not in pl.columns
    ]

    if missing_pl_columns:
        raise ValueError(
            "Cleaned P&L data is missing required columns: "
            + ", ".join(missing_pl_columns)
        )

    pl_data = pl[
        [
            "company_id",
            "year",
            "sales",
            "net_profit",
        ]
    ].copy()

    pl_data = pl_data.rename(
        columns={"sales": "revenue_cr"}
    )

    pl_data = pl_data.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    result = result.merge(
        pl_data,
        on=["company_id", "year"],
        how="left",
    )
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

    Sprint 3 Day 15 rules:
    - Only supported screener metrics may be filtered.
    - All filters use AND logic.
    - Financial-sector D/E filters are skipped because
      D/E is not directly comparable for financial institutions.
    - Debt-free companies receive infinite ICR.
    """

    result = df.copy()

    for item in filters:

        metric = item["metric"]
        op = item["operator"]
        value = item["value"]

        # ---------------------------------------------------------
        # Validate metric
        # ---------------------------------------------------------
        # Sprint 3 defines exactly 15 general filterable metrics.
        # Dividend payout is additionally required by the
        # Dividend Champion preset.
        preset_only_metrics = {
            "dividend_payout_ratio_pct",
            "revenue_cagr_3yr",
        }

        if (
            metric not in FILTERABLE_METRICS
            and metric not in preset_only_metrics
        ):
            raise ValueError(
                f"Unsupported screener metric '{metric}'. "
                f"Supported metrics: "
                f"{', '.join(sorted(FILTERABLE_METRICS))}"
            )

        if metric not in result.columns:
            raise ValueError(
                f"Screener metric '{metric}' is not available "
                f"in the loaded data."
            )

        # ---------------------------------------------------------
        # Validate operator
        # ---------------------------------------------------------
        if op not in OPERATORS:
            raise ValueError(
                f"Unsupported operator '{op}'. "
                f"Supported operators: "
                f"{', '.join(OPERATORS)}"
            )

        # ---------------------------------------------------------
        # Financial-sector D/E handling
        # ---------------------------------------------------------
        if (
            metric == "debt_to_equity"
            and "broad_sector" in result.columns
        ):
            financial_mask = (
                result["broad_sector"]
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("financials")
            )

            non_financial = result[~financial_mask].copy()
            financial = result[financial_mask].copy()

            if not financial.empty:
                non_financial = non_financial[
                    non_financial[metric].notna()
                    & OPERATORS[op](
                        non_financial[metric],
                        value,
                    )
                ]

                result = pd.concat(
                    [financial, non_financial],
                    ignore_index=True,
                )

                continue

        # ---------------------------------------------------------
        # Normal AND filter
        # ---------------------------------------------------------
        result = result[
            result[metric].notna()
            & OPERATORS[op](result[metric], value)
        ].copy()

    return result

def run_screener(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """
    Run one configured screener.

    Sprint 3 Day 15 rules:
    - Load screener configuration from YAML.
    - Evaluate the latest available year for each company.
    - Support the 15 approved filterable metrics.
    - Skip D/E filtering for Financials.
    - Treat Debt-Free companies as infinite ICR.
    - Turnaround Watch additionally checks declining D/E YoY.
    - Return results sorted by the configured ranking metric.
    """

    config = load_config(config_path)

    screeners = config.get("screeners", {})

    if name not in screeners:
        raise ValueError(
            f"Unknown screener '{name}'. "
            f"Available screeners: {list(screeners.keys())}"
        )

    df = load_data(data_path)

    # ---------------------------------------------------------
    # Add broad-sector information.
    # ---------------------------------------------------------
    sector_df = load_sector_data()

    if (
        not sector_df.empty
        and "company_id" in df.columns
    ):
        df = df.merge(
            sector_df.drop_duplicates("company_id"),
            on="company_id",
            how="left",
        )

    # ---------------------------------------------------------
    # Debt-free companies:
    # D/E = 0 means ICR should be treated as infinity.
    # Also recognize an explicit "Debt Free" ICR label.
    # ---------------------------------------------------------
    if "interest_coverage" in df.columns:

        debt_free_mask = pd.Series(
            False,
            index=df.index,
        )

        if "debt_to_equity" in df.columns:
            debt_free_mask = (
                pd.to_numeric(
                    df["debt_to_equity"],
                    errors="coerce",
                ) == 0
            )

        if "icr_label" in df.columns:
            label_mask = (
                df["icr_label"]
                .astype(str)
                .str.strip()
                .str.lower()
                .eq("debt free")
            )

            debt_free_mask = (
                debt_free_mask
                | label_mask
            )

        df.loc[
            debt_free_mask,
            "interest_coverage",
        ] = float("inf")

    # ---------------------------------------------------------
    # TURNAROUND WATCH:
    # Historical data is required to compare current D/E
    # against the previous year.
    # ---------------------------------------------------------
    if name == "turnaround_watch":

        # -----------------------------------------------------
        # Keep history temporarily so we can calculate the
        # previous-year D/E for the latest available year.
        # -----------------------------------------------------
        df = df.sort_values(
            ["company_id", "year"]
        ).copy()

        df["previous_debt_to_equity"] = (
            df.groupby("company_id")[
                "debt_to_equity"
            ].shift(1)
        )

        # -----------------------------------------------------
        # Keep ONLY the latest available year per company.
        # The previous_debt_to_equity value now represents the
        # immediately preceding year.
        # -----------------------------------------------------
        df = (
            df.groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
            .reset_index(drop=True)
        )

    else:

        # -----------------------------------------------------
        # Other screeners use the latest available year
        # for each company.
        # -----------------------------------------------------
        df = (
            df.sort_values(
                ["company_id", "year"]
            )
            .groupby(
                "company_id",
                as_index=False,
            )
            .tail(1)
            .reset_index(drop=True)
        )

    # ---------------------------------------------------------
    # Apply configured YAML filters.
    # ---------------------------------------------------------
    filters = screeners[name].get(
        "filters",
        [],
    )

    result = apply_filters(
        df,
        filters,
    )

    # ---------------------------------------------------------
    # TURNAROUND WATCH:
    # Require current D/E < previous-year D/E.
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



    # ---------------------------------------------------------
    # Sort by configured ranking metric.
    # ---------------------------------------------------------
    ranking_config = screeners[name].get(
        "ranking",
        {},
    )

    ranking_metric = ranking_config.get(
        "metric"
    )

    ranking_order = str(
        ranking_config.get(
            "order",
            "desc",
        )
    ).lower()

    if (
        ranking_metric
        and ranking_metric in result.columns
    ):

        result = result.sort_values(
            ranking_metric,
            ascending=(ranking_order == "asc"),
            na_position="last",
        ).reset_index(drop=True)

    # ---------------------------------------------------------
    # Fallback: composite quality score.
    # ---------------------------------------------------------
    if (
        ranking_metric is None
        and "composite_quality_score" in result.columns
    ):

        result = result.sort_values(
            "composite_quality_score",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)

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
















