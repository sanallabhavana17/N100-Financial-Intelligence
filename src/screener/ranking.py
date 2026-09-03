"""
N100 Financial Intelligence Platform
Sprint 3 — Screener Ranking Engine

Ranks screener results using the ranking_metric configured
in screener_config.yaml.
"""

from pathlib import Path

import pandas as pd
import yaml


CONFIG_PATH = Path("screener_config.yaml")
DATA_PATH = Path("output/final_financial_ratios.csv")
MARKET_DATA_PATH = Path("data/raw/market_cap.xlsx")
PL_DATA_PATH = Path("data/processed/profitandloss_cleaned.csv")


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
    Load financial data and merge valuation/revenue data.

    This follows the same data sources used by the screener engine.
    """

    financial = pd.read_csv(data_path)

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

    market = market.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    result = financial.merge(
        market,
        on=["company_id", "year"],
        how="left",
    )

    # Revenue from cleaned P&L.
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

    # FCF Yield = FCF / Market Cap × 100.
    result["fcf_yield"] = (
        result["free_cash_flow_cr"]
        / result["market_cap_crore"]
        * 100
    )

    result.loc[
        result["market_cap_crore"].isna()
        | result["market_cap_crore"].eq(0),
        "fcf_yield",
    ] = pd.NA

    return result


def rank_results(
    df,
    ranking_metric,
    ranking_order="desc",
):
    """
    Rank screener results by the configured metric.

    Parameters
    ----------
    df : pandas.DataFrame
        Screener result dataframe.

    ranking_metric : str
        Column used for ranking.

    ranking_order : str
        'asc' or 'desc'.

    Returns
    -------
    pandas.DataFrame
        Ranked dataframe with a rank column.
    """

    if ranking_metric not in df.columns:
        raise ValueError(
            f"Unknown ranking metric '{ranking_metric}'. "
            f"Available columns: {', '.join(df.columns)}"
        )

    if ranking_order not in {"asc", "desc"}:
        raise ValueError(
            f"Unsupported ranking order '{ranking_order}'. "
            "Use 'asc' or 'desc'."
        )

    result = df.copy()

    # Ranking requires a valid metric value.
    result = result[
        result[ranking_metric].notna()
    ].copy()

    ascending = ranking_order == "asc"

    result = result.sort_values(
        by=ranking_metric,
        ascending=ascending,
        kind="mergesort",
    ).reset_index(drop=True)

    # Rank 1 = best result.
    result["ranking"] = range(1, len(result) + 1)

    return result


def rank_screener(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """
    Run a configured screener and rank its results.

    The filters themselves are handled by src.screener.engine.
    """

    from src.screener.engine import run_screener

    config = load_config(config_path)

    screeners = config.get("screeners", {})

    if name not in screeners:
        raise ValueError(
            f"Unknown screener '{name}'. "
            f"Available screeners: {', '.join(screeners)}"
        )

    screener_config = screeners[name]

    ranking_metric = screener_config.get(
        "ranking_metric"
    )

    ranking_order = screener_config.get(
        "ranking_order",
        "desc",
    )

    if not ranking_metric:
        raise ValueError(
            f"Screener '{name}' does not define "
            "'ranking_metric' in screener_config.yaml."
        )

    results = run_screener(
        name,
        config_path=config_path,
        data_path=data_path,
    )

    return rank_results(
        results,
        ranking_metric=ranking_metric,
        ranking_order=ranking_order,
    )


def rank_latest_year(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """
    Rank a screener using only the latest available year.
    """

    results = rank_screener(
        name,
        config_path=config_path,
        data_path=data_path,
    )

    if results.empty:
        return results

    latest_year = results["year"].max()

    results = results[
        results["year"].eq(latest_year)
    ].copy()

    results = results.sort_values(
        "ranking"
    ).reset_index(drop=True)

    # Re-number after selecting the latest year.
    results["ranking"] = range(
        1,
        len(results) + 1,
    )

    return results


if __name__ == "__main__":

    names = [
        "quality_compounder",
        "value_pick",
        "growth_accelerator",
        "dividend_champion",
        "debt_free_blue_chip",
        "turnaround_watch",
    ]

    print("N100 SCREENER RANKING ENGINE")
    print("=" * 70)

    for name in names:

        try:
            results = rank_latest_year(name)

            print()
            print(f"{name}")
            print("-" * 70)

            if results.empty:
                print("No results.")
                continue

            print(
                f"Year: {results['year'].iloc[0]}"
            )

            print(
                f"Companies: {results['company_id'].nunique()}"
            )

            print()

            columns = [
                "ranking",
                "company_id",
                "year",
                "composite_quality_score",
                "return_on_equity_pct",
                "debt_to_equity",
                "free_cash_flow_cr",
                "revenue_cagr_5yr",
                "pat_cagr_5yr",
                "pe_ratio",
                "pb_ratio",
                "dividend_yield_pct",
                "fcf_yield",
            ]

            available = [
                column
                for column in columns
                if column in results.columns
            ]

            print(
                results[available]
                .head(20)
                .to_string(index=False)
            )

        except Exception as exc:
            print(
                f"{name}: ERROR - {exc}"
            )