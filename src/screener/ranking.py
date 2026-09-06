"""
N100 Financial Intelligence Platform
Sprint 3 â€” Screener Ranking Engine

Provides:
1. Configured single-metric ranking
2. Composite ranking:
   - 35% Profitability
   - 30% Cash Quality
   - 20% Growth
   - 15% Leverage
3. Sector-relative normalization
4. Peer-adjusted ranking
5. CSV and Excel export
"""

from pathlib import Path
import sqlite3

import pandas as pd
import yaml
from openpyxl.styles import PatternFill


CONFIG_PATH = Path("config/screener_config.yaml")
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
# D17 â€” COMPOSITE RANKING ENGINE
# ------------------------------------------------------------------


def _percentile_score(series, higher_is_better=True):
    """
    Convert a metric into a 0â€“100 percentile score.

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


def _winsorize_p10_p90(series):
    """Winsorize numeric values at the 10th and 90th percentiles."""
    numeric = pd.to_numeric(series, errors="coerce")

    valid = numeric.dropna()
    if valid.empty:
        return numeric

    lower = valid.quantile(0.10)
    upper = valid.quantile(0.90)

    return numeric.clip(lower=lower, upper=upper)


def _calculate_historical_fcf_cagr(df):
    """
    Calculate 5-year FCF CAGR for each company.

    CAGR is calculated only when both the starting and ending
    FCF values are positive.
    """

    required = {
        "company_id",
        "year",
        "free_cash_flow_cr",
    }

    if not required.issubset(df.columns):
        return pd.Series(
            float("nan"),
            index=df.index,
            dtype="float64",
        )

    history = df[
        ["company_id", "year", "free_cash_flow_cr"]
    ].copy()

    history["year"] = pd.to_numeric(
        history["year"],
        errors="coerce",
    )

    history["free_cash_flow_cr"] = pd.to_numeric(
        history["free_cash_flow_cr"],
        errors="coerce",
    )

    history = history.dropna(
        subset=[
            "company_id",
            "year",
            "free_cash_flow_cr",
        ]
    )

    history = history.drop_duplicates(
        subset=["company_id", "year"],
        keep="last",
    )

    latest = (
        history.sort_values(
            ["company_id", "year"]
        )
        .groupby("company_id", as_index=False)
        .tail(1)
        .rename(
            columns={
                "year": "latest_year",
                "free_cash_flow_cr": "latest_fcf",
            }
        )
    )

    base = history.rename(
        columns={
            "year": "base_year",
            "free_cash_flow_cr": "base_fcf",
        }
    )

    latest = latest[
        [
            "company_id",
            "latest_year",
            "latest_fcf",
        ]
    ].copy()

    latest["base_year"] = (
        latest["latest_year"] - 5
    )

    latest = latest.merge(
        base[
            [
                "company_id",
                "base_year",
                "base_fcf",
            ]
        ],
        on=[
            "company_id",
            "base_year",
        ],
        how="left",
    )

    valid = (
        latest["latest_fcf"].gt(0)
        & latest["base_fcf"].gt(0)
    )

    latest["fcf_cagr_5yr"] = float("nan")

    latest.loc[
        valid,
        "fcf_cagr_5yr",
    ] = (
        (
            latest.loc[valid, "latest_fcf"]
            / latest.loc[valid, "base_fcf"]
        )
        ** (1 / 5)
        - 1
    ) * 100

    lookup = latest.set_index(
        "company_id"
    )["fcf_cagr_5yr"]

    return df["company_id"].map(lookup)


def calculate_composite_score(df):
    """
    Calculate Sprint 3 Day 17 composite quality score.

    Profitability = 35%
        ROE  15%
        ROCE 10%
        NPM  10%

    Cash Quality = 30%
        FCF CAGR       15%
        CFO/PAT        10%
        FCF positive     5%

    Growth = 20%
        Revenue CAGR 5yr 10%
        PAT CAGR 5yr     10%

    Leverage = 15%
        D/E  10%
        ICR   5%

    Numeric metrics are winsorized at P10/P90
    before percentile scoring.

    Final score is between 0 and 100.
    """

    result = df.copy()

    # --------------------------------------------------------------
    # Profitability: 35%
    # --------------------------------------------------------------

    roe = _winsorize_p10_p90(
        result["return_on_equity_pct"]
    )

    roce = _winsorize_p10_p90(
        result["return_on_capital_employed_pct"]
    )

    npm = _winsorize_p10_p90(
        result["net_profit_margin_pct"]
    )

    result["profitability_roe_score"] = (
        _percentile_score(
            roe,
            higher_is_better=True,
        )
    )

    result["profitability_roce_score"] = (
        _percentile_score(
            roce,
            higher_is_better=True,
        )
    )

    result["profitability_margin_score"] = (
        _percentile_score(
            npm,
            higher_is_better=True,
        )
    )

    result["profitability_score"] = (
        result["profitability_roe_score"] * 15
        + result["profitability_roce_score"] * 10
        + result["profitability_margin_score"] * 10
    ) / 35

    # --------------------------------------------------------------
    # Cash Quality: 30%
    # --------------------------------------------------------------

    # FCF CAGR is supplied from the full historical dataset by rank_screener_composite().
    if "fcf_cagr_5yr" not in result.columns:
        result["fcf_cagr_5yr"] = float("nan")
    fcf_cagr = _winsorize_p10_p90(
        result["fcf_cagr_5yr"]
    )

    result["cashflow_fcf_cagr_score"] = (
        _percentile_score(
            fcf_cagr,
            higher_is_better=True,
        )
    )

    pat = pd.to_numeric(
        result["net_profit"],
        errors="coerce",
    )

    cfo = pd.to_numeric(
        result["cash_from_operations_cr"],
        errors="coerce",
    )

    cfo_pat = pd.Series(
        float("nan"),
        index=result.index,
        dtype="float64",
    )

    valid_pat = (
        pat.notna()
        & pat.ne(0)
        & cfo.notna()
    )

    cfo_pat.loc[valid_pat] = (
        cfo.loc[valid_pat]
        / pat.loc[valid_pat]
    )

    result["cfo_pat_ratio"] = cfo_pat

    cfo_pat_winsorized = _winsorize_p10_p90(
        result["cfo_pat_ratio"]
    )

    result["cashflow_cfo_pat_score"] = (
        _percentile_score(
            cfo_pat_winsorized,
            higher_is_better=True,
        )
    )

    fcf_numeric = pd.to_numeric(
        result["free_cash_flow_cr"],
        errors="coerce",
    )

    result["fcf_positive_flag"] = (
        fcf_numeric.gt(0)
        .astype("float64")
        .where(fcf_numeric.notna())
    )

    result["cashflow_fcf_positive_score"] = (
        result["fcf_positive_flag"] * 100
    )

    cash_components = pd.DataFrame(
        {
            "fcf_cagr": result[
                "cashflow_fcf_cagr_score"
            ],
            "cfo_pat": result[
                "cashflow_cfo_pat_score"
            ],
            "fcf_positive": result[
                "cashflow_fcf_positive_score"
            ],
        },
        index=result.index,
    )

    cash_weights = pd.Series(
        {
            "fcf_cagr": 15,
            "cfo_pat": 10,
            "fcf_positive": 5,
        }
    )

    cash_weighted = (
        cash_components * cash_weights
    )

    cash_available = (
        cash_components.notna()
        * cash_weights
    ).sum(axis=1)

    result["cash_quality_score"] = (
        cash_weighted.sum(axis=1)
        / cash_available
    ).where(
        cash_available.gt(0),
        float("nan"),
    )

    # Existing name retained for compatibility.
    result["cashflow_score"] = (
        result["cash_quality_score"]
    )

    # --------------------------------------------------------------
    # Growth: 20%
    # --------------------------------------------------------------

    revenue_growth = _winsorize_p10_p90(
        result["revenue_cagr_5yr"]
    )

    pat_growth = _winsorize_p10_p90(
        result["pat_cagr_5yr"]
    )

    result["growth_revenue_score"] = (
        _percentile_score(
            revenue_growth,
            higher_is_better=True,
        )
    )

    result["growth_pat_score"] = (
        _percentile_score(
            pat_growth,
            higher_is_better=True,
        )
    )

    growth_components = pd.DataFrame(
        {
            "revenue": result[
                "growth_revenue_score"
            ],
            "pat": result[
                "growth_pat_score"
            ],
        },
        index=result.index,
    )

    growth_weights = pd.Series(
        {
            "revenue": 10,
            "pat": 10,
        }
    )

    growth_weighted = (
        growth_components * growth_weights
    )

    growth_available = (
        growth_components.notna()
        * growth_weights
    ).sum(axis=1)

    result["growth_score"] = (
        growth_weighted.sum(axis=1)
        / growth_available
    ).where(
        growth_available.gt(0),
        float("nan"),
    )

    # --------------------------------------------------------------
    # Leverage: 15%
    # --------------------------------------------------------------

    debt_to_equity = _winsorize_p10_p90(
        result["debt_to_equity"]
    )

    interest_coverage = _winsorize_p10_p90(
        result["interest_coverage"]
    )

    result["leverage_de_score"] = (
        _percentile_score(
            debt_to_equity,
            higher_is_better=False,
        )
    )

    result["leverage_icr_score"] = (
        _percentile_score(
            interest_coverage,
            higher_is_better=True,
        )
    )

    leverage_components = pd.DataFrame(
        {
            "de": result[
                "leverage_de_score"
            ],
            "icr": result[
                "leverage_icr_score"
            ],
        },
        index=result.index,
    )

    leverage_weights = pd.Series(
        {
            "de": 10,
            "icr": 5,
        }
    )

    leverage_weighted = (
        leverage_components * leverage_weights
    )

    leverage_available = (
        leverage_components.notna()
        * leverage_weights
    ).sum(axis=1)

    result["leverage_score"] = (
        leverage_weighted.sum(axis=1)
        / leverage_available
    ).where(
        leverage_available.gt(0),
        float("nan"),
    )

    # --------------------------------------------------------------
    # Final weighted score: 100%
    # --------------------------------------------------------------

    components = pd.DataFrame(
        {
            "profitability": result[
                "profitability_score"
            ],
            "cash_quality": result[
                "cash_quality_score"
            ],
            "growth": result[
                "growth_score"
            ],
            "leverage": result[
                "leverage_score"
            ],
        },
        index=result.index,
    )

    weights = pd.Series(
        {
            "profitability": 35,
            "cash_quality": 30,
            "growth": 20,
            "leverage": 15,
        }
    )

    weighted = components * weights

    available_weight = (
        components.notna() * weights
    ).sum(axis=1)

    result["composite_score"] = (
        weighted.sum(axis=1)
        / available_weight
    ).where(
        available_weight.gt(0),
        float("nan"),
    )

    result["composite_score"] = (
        result["composite_score"]
        .clip(
            lower=0,
            upper=100,
        )
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

        # Attach sector information only when it is not already present.
    if "broad_sector" not in results.columns:
        sectors = load_sector_data()

        results = results.merge(
            sectors,
            on="company_id",
            how="left",
            validate="many_to_one",
        )
    # Calculate historical 5-year FCF CAGR from the full dataset before composite scoring.
    historical = load_data(data_path=data_path)
    historical_fcf_cagr = _calculate_historical_fcf_cagr(historical)
    historical_with_cagr = historical[["company_id"]].copy()
    historical_with_cagr["fcf_cagr_5yr"] = historical_fcf_cagr.to_numpy()
    company_fcf_cagr = historical_with_cagr.dropna(subset=["fcf_cagr_5yr"]).groupby("company_id")["fcf_cagr_5yr"].first()
    results["fcf_cagr_5yr"] = results["company_id"].map(company_fcf_cagr)
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
# D17 â€” EXPORT
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
                "expected_company_count",
                "10-25",
            )

            # Config stores expected counts as "minimum-maximum".
            if isinstance(expected_range, str):
                parts = expected_range.split("-")
                if len(parts) != 2:
                    raise ValueError(
                        f"Invalid expected_company_count for '{name}': "
                        f"{expected_range}"
                    )

                min_count = int(parts[0].strip())
                max_count = int(parts[1].strip())
            else:
                min_count = int(expected_range[0])
                max_count = int(expected_range[1])

            top_n = max(
                20,
                max_count,
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

            # Colour-code cells according to the preset thresholds.
            green_fill = PatternFill(
                fill_type="solid",
                fgColor="C6EFCE",
            )
            red_fill = PatternFill(
                fill_type="solid",
                fgColor="FFC7CE",
            )

            filter_config = config["screeners"][name].get(
                "filters",
                [],
            )

            header_map = {
                cell.value: cell.column
                for cell in worksheet[1]
            }

            for item in filter_config:
                metric = item["metric"]
                operator = item["operator"]
                threshold = item["value"]

                if metric not in header_map:
                    continue

                column = header_map[metric]

                for row in range(2, worksheet.max_row + 1):
                    cell = worksheet.cell(
                        row=row,
                        column=column,
                    )

                    if cell.value is None:
                        continue

                    try:
                        actual = float(cell.value)
                        expected = float(threshold)
                    except (TypeError, ValueError):
                        continue

                    passed = {
                        ">": actual > expected,
                        ">=": actual >= expected,
                        "<": actual < expected,
                        "<=": actual <= expected,
                        "==": actual == expected,
                        "!=": actual != expected,
                    }.get(operator)

                    if passed is True:
                        cell.fill = green_fill
                    elif passed is False:
                        cell.fill = red_fill

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


