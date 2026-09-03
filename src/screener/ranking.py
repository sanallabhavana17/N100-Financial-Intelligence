"""
N100 Financial Intelligence Platform
Sprint 3 — Screener Ranking Engine

Provides:
1. Configured single-metric ranking
2. Composite ranking:
   - 50% Profitability
   - 30% Growth
   - 20% Valuation
3. Sector-relative normalization
4. Peer-adjusted ranking
5. CSV and Excel export
"""

from pathlib import Path
import sqlite3

import pandas as pd
import yaml


CONFIG_PATH = Path("screener_config.yaml")
DATA_PATH = Path("output/final_financial_ratios.csv")
MARKET_DATA_PATH = Path("data/raw/market_cap.xlsx")
PL_DATA_PATH = Path("data/processed/profitandloss_cleaned.csv")
DB_PATH = Path("data/nifty100.db")

OUTPUT_DIR = Path("output")
SCREENER_CSV_PATH = OUTPUT_DIR / "screener_output.csv"
SCREENER_XLSX_PATH = OUTPUT_DIR / "screener_output.xlsx"


SCREENERS = [
    "quality_compounder",
    "value_pick",
    "growth_accelerator",
    "dividend_champion",
    "debt_free_blue_chip",
    "turnaround_watch",
]


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

    # FCF Yield.
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


def load_sector_data(db_path=DB_PATH):
    """Load company sector mapping from the validated SQLite database."""

    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}"
        )

    with sqlite3.connect(db_path) as connection:
        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector,
                sub_sector,
                index_weight_pct,
                market_cap_category
            FROM sectors
            """,
            connection,
        )

    sectors = sectors.drop_duplicates(
        subset=["company_id"],
        keep="last",
    )

    return sectors


def load_ranking_data(
    data_path=DATA_PATH,
    market_data_path=MARKET_DATA_PATH,
    pl_data_path=PL_DATA_PATH,
    db_path=DB_PATH,
):
    """
    Load screener data and attach validated sector information.
    """

    result = load_data(
        data_path=data_path,
        market_data_path=market_data_path,
        pl_data_path=pl_data_path,
    )

    sectors = load_sector_data(db_path)

    result = result.merge(
        sectors,
        on="company_id",
        how="left",
        validate="many_to_one",
    )

    return result


def rank_results(
    df,
    ranking_metric,
    ranking_order="desc",
):
    """
    Rank screener results by a configured metric.

    Rank 1 = best result.
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

    result = result[
        result[ranking_metric].notna()
    ].copy()

    ascending = ranking_order == "asc"

    result = result.sort_values(
        by=ranking_metric,
        ascending=ascending,
        kind="mergesort",
    ).reset_index(drop=True)

    result["ranking"] = range(
        1,
        len(result) + 1,
    )

    return result


def rank_screener(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """
    Run a configured screener and rank its results.

    This preserves the original Sprint 3 single-metric
    ranking behaviour.
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
    """Rank a screener using only the latest available year."""

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

    results["ranking"] = range(
        1,
        len(results) + 1,
    )

    return results


# ------------------------------------------------------------------
# D17 — COMPOSITE RANKING ENGINE
# ------------------------------------------------------------------


def _percentile_score(series, higher_is_better=True):
    """
    Convert a metric into a 0–100 percentile score.

    Higher values receive higher scores when higher_is_better=True.
    Missing values remain missing.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    if not higher_is_better:
        numeric = -numeric

    if numeric.notna().sum() <= 1:
        return pd.Series(
            50.0,
            index=series.index,
            dtype="float64",
        ).where(
            numeric.notna(),
            pd.NA,
        )

    return numeric.rank(
        method="average",
        pct=True,
    ) * 100


def _mean_available_scores(df, columns):
    """Average available score columns row-wise."""

    available = [
        column
        for column in columns
        if column in df.columns
    ]

    if not available:
        return pd.Series(
            pd.NA,
            index=df.index,
            dtype="float64",
        )

    return df[available].mean(
        axis=1,
        skipna=True,
    ).where(
        df[available].notna().any(axis=1),
        pd.NA,
    )


def calculate_composite_score(df):
    """
    Calculate the Sprint 3 composite score.

    Weighting:
        Profitability = 50%
        Growth        = 30%
        Valuation     = 20%

    The resulting composite score is on a 0–100 scale.
    """

    result = df.copy()

    # --------------------------------------------------------------
    # Profitability: 50%
    # --------------------------------------------------------------

    result["profitability_roe_score"] = _percentile_score(
        result["return_on_equity_pct"],
        higher_is_better=True,
    )

    result["profitability_roce_score"] = _percentile_score(
        result["return_on_capital_employed_pct"],
        higher_is_better=True,
    )

    result["profitability_margin_score"] = _percentile_score(
        result["net_profit_margin_pct"],
        higher_is_better=True,
    )

    result["profitability_score"] = _mean_available_scores(
        result,
        [
            "profitability_roe_score",
            "profitability_roce_score",
            "profitability_margin_score",
        ],
    )

    # --------------------------------------------------------------
    # Growth: 30%
    # --------------------------------------------------------------

    result["growth_revenue_score"] = _percentile_score(
        result["revenue_cagr_5yr"],
        higher_is_better=True,
    )

    result["growth_pat_score"] = _percentile_score(
        result["pat_cagr_5yr"],
        higher_is_better=True,
    )

    result["growth_score"] = _mean_available_scores(
        result,
        [
            "growth_revenue_score",
            "growth_pat_score",
        ],
    )

    # --------------------------------------------------------------
    # Valuation: 20%
    #
    # Lower P/E, P/B and EV/EBITDA are considered better.
    # --------------------------------------------------------------

    result["valuation_pe_score"] = _percentile_score(
        result["pe_ratio"],
        higher_is_better=False,
    )

    result["valuation_pb_score"] = _percentile_score(
        result["pb_ratio"],
        higher_is_better=False,
    )

    result["valuation_ev_ebitda_score"] = _percentile_score(
        result["ev_ebitda"],
        higher_is_better=False,
    )

    result["valuation_score"] = _mean_available_scores(
        result,
        [
            "valuation_pe_score",
            "valuation_pb_score",
            "valuation_ev_ebitda_score",
        ],
    )

    # --------------------------------------------------------------
    # Final weighted score.
    # --------------------------------------------------------------

    components = [
        "profitability_score",
        "growth_score",
        "valuation_score",
    ]

    weighted_values = result[components].copy()

    weights = {
        "profitability_score": 0.50,
        "growth_score": 0.30,
        "valuation_score": 0.20,
    }

    weighted_sum = sum(
        weighted_values[column] * weight
        for column, weight in weights.items()
    )

    available_weight = sum(
        weights[column]
        * weighted_values[column].notna()
        for column in components
    )

    result["composite_score"] = (
        weighted_sum
        / available_weight
    ).where(
        available_weight.gt(0),
        pd.NA,
    )

    result["composite_score"] = result[
        "composite_score"
    ].clip(
        lower=0,
        upper=100,
    )

    return result


def add_sector_relative_scores(df):
    """
    Normalize composite scores within broad_sector.

    Produces:
        sector_percentile_score
        sector_z_score
        sector_peer_rank
        sector_outlier_flag

    Outlier rule:
        - absolute sector z-score > 2
        - OR bottom decile within the sector
    """

    result = df.copy()

    if "broad_sector" not in result.columns:
        raise ValueError(
            "Sector-relative ranking requires 'broad_sector'."
        )

    if "composite_score" not in result.columns:
        result = calculate_composite_score(result)

    result["sector_percentile_score"] = (
        result.groupby("broad_sector")[
            "composite_score"
        ]
        .rank(
            method="average",
            pct=True,
        )
        * 100
    )

    sector_mean = result.groupby(
        "broad_sector"
    )["composite_score"].transform("mean")

    sector_std = result.groupby(
        "broad_sector"
    )["composite_score"].transform("std")

    result["sector_z_score"] = (
        result["composite_score"] - sector_mean
    ) / sector_std.replace(0, pd.NA)

    result["sector_peer_rank"] = (
        result.groupby("broad_sector")[
            "composite_score"
        ]
        .rank(
            method="min",
            ascending=False,
        )
    )

    sector_size = result.groupby(
        "broad_sector"
    )["company_id"].transform("count")

    bottom_decile = (
        result["sector_percentile_score"].notna()
        & result["sector_percentile_score"].le(10)
    )

    z_outlier = (
        result["sector_z_score"].abs().gt(2)
    )

    result["sector_outlier_flag"] = (
        bottom_decile | z_outlier
    )

    result["sector_outlier_flag"] = (
        result["sector_outlier_flag"]
        .fillna(False)
        .astype(bool)
    )

    # Suppress unused-variable warnings while keeping
    # sector_size available for readability/debugging.
    result["sector_size"] = sector_size

    return result


def rank_composite(df):
    """
    Rank companies globally using the composite score.

    Rank 1 = highest composite score.
    """

    result = df.copy()

    if "composite_score" not in result.columns:
        result = calculate_composite_score(result)

    result = result[
        result["composite_score"].notna()
    ].copy()

    result = result.sort_values(
        [
            "composite_score",
            "company_id",
        ],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)

    result["composite_rank"] = range(
        1,
        len(result) + 1,
    )

    return result


def rank_screener_composite(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """
    Run a screener, calculate composite score,
    add sector-relative metrics and rank results.
    """

    from src.screener.engine import run_screener

    results = run_screener(
        name,
        config_path=config_path,
        data_path=data_path,
    )

    if results.empty:
        return results

    # Attach sector information.
    sectors = load_sector_data()

    results = results.merge(
        sectors,
        on="company_id",
        how="left",
        validate="many_to_one",
    )

    # Composite score.
    results = calculate_composite_score(
        results
    )

    # Sector-relative score.
    results = add_sector_relative_scores(
        results
    )

    # Global composite rank.
    results = rank_composite(
        results
    )

    # Recalculate peer rank after composite processing.
    results = results.sort_values(
        [
            "year",
            "composite_rank",
        ]
    ).reset_index(drop=True)

    return results


def rank_screener_latest_composite(
    name,
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
):
    """Return latest-year composite ranking for one screener."""

    results = rank_screener_composite(
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
        [
            "composite_rank",
            "company_id",
        ],
        kind="mergesort",
    ).reset_index(drop=True)

    results["ranking"] = range(
        1,
        len(results) + 1,
    )

    return results


# ------------------------------------------------------------------
# D17 — EXPORT
# ------------------------------------------------------------------


def _export_columns(df):
    """Select useful columns for screener output."""

    preferred = [
        "ranking",
        "composite_rank",
        "company_id",
        "year",
        "broad_sector",
        "sub_sector",
        "market_cap_category",
        "composite_score",
        "profitability_score",
        "growth_score",
        "valuation_score",
        "sector_percentile_score",
        "sector_z_score",
        "sector_peer_rank",
        "sector_outlier_flag",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "net_profit_margin_pct",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "debt_to_equity",
        "free_cash_flow_cr",
        "fcf_yield",
        "revenue_cr",
    ]

    return [
        column
        for column in preferred
        if column in df.columns
    ]


def export_screener_results(
    results,
    screener_name,
    csv_path=SCREENER_CSV_PATH,
):
    """
    Export one screener result to a CSV file.

    All screeners are also combined into the master
    screener_output.csv.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    export = results.copy()

    export.insert(
        0,
        "screener",
        screener_name,
    )

    columns = [
        "screener"
    ] + _export_columns(export)

    export = export[
        [
            column
            for column in columns
            if column in export.columns
        ]
    ]

    file_path = Path(csv_path)

    if file_path.exists():
        export.to_csv(
            file_path,
            mode="a",
            header=False,
            index=False,
        )
    else:
        export.to_csv(
            file_path,
            index=False,
        )

    return export


def export_all_screeners(
    config_path=CONFIG_PATH,
    data_path=DATA_PATH,
    xlsx_path=SCREENER_XLSX_PATH,
    csv_path=SCREENER_CSV_PATH,
):
    """
    Generate latest-year ranked output for all six
    preset screeners.

    Outputs:
        output/screener_output.csv
        output/screener_output.xlsx
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove previous master CSV so repeated runs do
    # not duplicate rows.
    csv_file = Path(csv_path)

    if csv_file.exists():
        csv_file.unlink()

    all_results = []

    with pd.ExcelWriter(
        xlsx_path,
        engine="openpyxl",
    ) as writer:

        for name in SCREENERS:

            results = rank_screener_latest_composite(
                name,
                config_path=config_path,
                data_path=data_path,
            )

            if results.empty:
                continue

            # Top-N output.
            config = load_config(
                config_path
            )

            expected_range = config[
                "screeners"
            ][name].get(
                "expected_count_range",
                [10, 25],
            )

            top_n = max(
                20,
                int(expected_range[1]),
            )

            results = results.head(
                top_n
            ).copy()

            export = results.copy()

            export.insert(
                0,
                "screener",
                name,
            )

            columns = [
                "screener"
            ] + _export_columns(export)

            export = export[
                [
                    column
                    for column in columns
                    if column in export.columns
                ]
            ]

            # Master CSV.
            all_results.append(
                export
            )

            # Individual worksheet.
            sheet_name = name[:31]

            export.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )

            # Formatting.
            worksheet = writer.sheets[
                sheet_name
            ]

            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = (
                worksheet.dimensions
            )

            for column_cells in worksheet.columns:

                max_length = 0
                column_letter = (
                    column_cells[0].column_letter
                )

                for cell in column_cells:
                    value = cell.value

                    if value is not None:
                        max_length = max(
                            max_length,
                            len(str(value)),
                        )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max_length + 2,
                    30,
                )

    if all_results:
        combined = pd.concat(
            all_results,
            ignore_index=True,
        )

        combined.to_csv(
            csv_file,
            index=False,
        )

    return all_results


def print_screener_summary(results, name):
    """Print a compact latest-year screener summary."""

    print()
    print(name)
    print("-" * 70)

    if results.empty:
        print("No results.")
        return

    print(
        f"Year: {results['year'].iloc[0]}"
    )

    print(
        f"Companies: {results['company_id'].nunique()}"
    )

    columns = [
        "ranking",
        "company_id",
        "broad_sector",
        "composite_score",
        "profitability_score",
        "growth_score",
        "valuation_score",
        "sector_peer_rank",
        "sector_outlier_flag",
        "return_on_equity_pct",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "pe_ratio",
        "pb_ratio",
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


if __name__ == "__main__":

    print("N100 SCREENER RANKING ENGINE")
    print("=" * 70)

    try:

        # Generate CSV + Excel output.
        exported = export_all_screeners()

        print()
        print(
            f"Screeners exported: {len(exported)}"
        )

        print(
            f"CSV: {SCREENER_CSV_PATH}"
        )

        print(
            f"Excel: {SCREENER_XLSX_PATH}"
        )

        # Display latest-year results.
        for name in SCREENERS:

            try:

                results = (
                    rank_screener_latest_composite(
                        name
                    )
                )

                print_screener_summary(
                    results,
                    name,
                )

            except Exception as exc:

                print(
                    f"{name}: ERROR - {exc}"
                )

    except Exception as exc:

        print(
            f"EXPORT ERROR: {exc}"
        )