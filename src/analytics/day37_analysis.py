"""
N100 Financial Intelligence
Sprint 6 - Day 37
Cluster Profiles, KPI Correlation, Sector Outliers and Portfolio Statistics
"""

from pathlib import Path
import sqlite3
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"

OUTPUT_DIR = PROJECT_ROOT / "output"
REPORT_DIR = PROJECT_ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------


def get_connection():
    """Return a SQLite connection to the N100 database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    return sqlite3.connect(DB_PATH)


def read_sql(query: str) -> pd.DataFrame:
    """Execute a SQL query and return a DataFrame."""
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


# ---------------------------------------------------------------------
# Numeric conversion
# ---------------------------------------------------------------------


def numeric(series: pd.Series) -> pd.Series:
    """Convert a financial series to numeric values safely."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace(
            {
                "": np.nan,
                "nan": np.nan,
                "None": np.nan,
                "NULL": np.nan,
                "-": np.nan,
            }
        ),
        errors="coerce",
    )


# ---------------------------------------------------------------------
# FCF CAGR
# ---------------------------------------------------------------------


def calculate_fcf_cagr(financial_ratios: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 5-year FCF CAGR from historical free_cash_flow_cr.

    CAGR is only calculated when:
    - both endpoint values are positive
    - the endpoint years are five years apart
    """
    df = financial_ratios.copy()

    df["free_cash_flow_cr"] = numeric(df["free_cash_flow_cr"])
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    records = []

    for company_id, group in df.groupby("company_id"):
        group = group.dropna(subset=["year"]).sort_values("year")

        if group.empty:
            records.append(
                {
                    "company_id": company_id,
                    "fcf_cagr_5yr": np.nan,
                }
            )
            continue

        latest_year = int(group["year"].max())
        start_year = latest_year - 5

        latest_rows = group[group["year"] == latest_year]
        start_rows = group[group["year"] == start_year]

        if latest_rows.empty or start_rows.empty:
            records.append(
                {
                    "company_id": company_id,
                    "fcf_cagr_5yr": np.nan,
                }
            )
            continue

        latest_fcf = latest_rows.iloc[-1]["free_cash_flow_cr"]
        start_fcf = start_rows.iloc[-1]["free_cash_flow_cr"]

        if (
            pd.notna(start_fcf)
            and pd.notna(latest_fcf)
            and start_fcf > 0
            and latest_fcf > 0
        ):
            cagr = ((latest_fcf / start_fcf) ** (1 / 5) - 1) * 100
        else:
            cagr = np.nan

        records.append(
            {
                "company_id": company_id,
                "fcf_cagr_5yr": cagr,
            }
        )

    return pd.DataFrame(records)


# ---------------------------------------------------------------------
# Latest financial ratios
# ---------------------------------------------------------------------


def load_latest_financials() -> pd.DataFrame:
    """Load the latest financial ratio record for every company."""
    query = """
        SELECT
            company_id,
            year,
            net_profit_margin_pct,
            operating_profit_margin_pct,
            return_on_equity_pct,
            return_on_capital_employed_pct,
            return_on_assets_pct,
            debt_to_equity,
            interest_coverage,
            net_debt_cr,
            asset_turnover,
            free_cash_flow_cr,
            cash_from_operations_cr,
            cfo_quality_ratio,
            capex_intensity_pct,
            fcf_conversion_pct,
            earnings_per_share,
            book_value_per_share,
            dividend_payout_ratio_pct,
            total_debt_cr,
            revenue_cagr_5yr,
            pat_cagr_5yr,
            eps_cagr_5yr,
            composite_quality_score
        FROM financial_ratios
    """

    ratios = read_sql(query)

    ratios["year"] = pd.to_numeric(ratios["year"], errors="coerce")

    numeric_columns = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "return_on_assets_pct",
        "debt_to_equity",
        "interest_coverage",
        "net_debt_cr",
        "asset_turnover",
        "free_cash_flow_cr",
        "cash_from_operations_cr",
        "cfo_quality_ratio",
        "capex_intensity_pct",
        "fcf_conversion_pct",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "eps_cagr_5yr",
        "composite_quality_score",
    ]

    for column in numeric_columns:
        ratios[column] = numeric(ratios[column])

    ratios = ratios.sort_values(["company_id", "year"])

    latest = (
        ratios.groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest = latest.reset_index(drop=True)

    fcf_cagr = calculate_fcf_cagr(ratios)

    latest = latest.merge(
        fcf_cagr,
        on="company_id",
        how="left",
    )

    return latest


# ---------------------------------------------------------------------
# Company and sector data
# ---------------------------------------------------------------------


def load_company_sector_data() -> pd.DataFrame:
    """Load company names and broad sector classifications."""
    query = """
        SELECT
            c.id AS company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
    """

    df = read_sql(query)

    if df["company_id"].duplicated().any():
        df = (
            df.sort_values(["company_id", "index_weight_pct"])
            .drop_duplicates("company_id", keep="last")
        )

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------
# Cluster profiles
# ---------------------------------------------------------------------


def create_cluster_profiles() -> pd.DataFrame:
    """Create detailed profiles for the five KMeans clusters."""
    cluster_path = OUTPUT_DIR / "cluster_labels.csv"

    if not cluster_path.exists():
        raise FileNotFoundError(
            f"Cluster labels not found: {cluster_path}. "
            "Run Day 36 clustering first."
        )

    clusters = pd.read_csv(cluster_path)

    latest = load_latest_financials()
    company_sector = load_company_sector_data()

    df = clusters.merge(
        latest,
        on="company_id",
        how="left",
        validate="one_to_one",
    )

    df = df.merge(
        company_sector,
        on="company_id",
        how="left",
        validate="one_to_one",
    )

    feature_columns = [
        "return_on_equity_pct",
        "debt_to_equity",
        "revenue_cagr_5yr",
        "fcf_cagr_5yr",
        "operating_profit_margin_pct",
    ]

    rows = []

    for cluster_id, group in df.groupby("cluster_id", sort=True):
        cluster_name = group["cluster_name"].iloc[0]

        row = {
            "cluster_id": int(cluster_id),
            "cluster_name": cluster_name,
            "company_count": int(len(group)),
        }

        for feature in feature_columns:
            row[f"{feature}_mean"] = group[feature].mean()
            row[f"{feature}_median"] = group[feature].median()

        rows.append(row)

    profiles = pd.DataFrame(rows)

    profiles = profiles.sort_values("cluster_id").reset_index(drop=True)

    return profiles


# ---------------------------------------------------------------------
# KPI correlation
# ---------------------------------------------------------------------


KPI_COLUMNS = {
    "net_profit_margin_pct": "Net Profit Margin",
    "operating_profit_margin_pct": "Operating Profit Margin",
    "return_on_equity_pct": "ROE",
    "return_on_capital_employed_pct": "ROCE",
    "return_on_assets_pct": "ROA",
    "debt_to_equity": "Debt to Equity",
    "interest_coverage": "Interest Coverage",
    "asset_turnover": "Asset Turnover",
    "revenue_cagr_5yr": "Revenue CAGR 5Y",
    "eps_cagr_5yr": "EPS CAGR 5Y",
}


def create_kpi_correlation() -> pd.DataFrame:
    """Calculate the Pearson correlation matrix for ten KPIs."""
    latest = load_latest_financials()

    available = [
        column
        for column in KPI_COLUMNS
        if column in latest.columns
    ]

    kpi_df = latest[available].copy()

    correlation = kpi_df.corr(method="pearson")

    correlation.index = [
        KPI_COLUMNS[column]
        for column in correlation.index
    ]

    correlation.columns = [
        KPI_COLUMNS[column]
        for column in correlation.columns
    ]

    return correlation


def create_correlation_heatmap(correlation: pd.DataFrame) -> Path:
    """Create and save the 10-KPI Pearson correlation heatmap."""
    output_path = REPORT_DIR / "kpi_correlation_heatmap.png"

    fig, ax = plt.subplots(
        figsize=(12, 10)
    )

    image = ax.imshow(
        correlation.values,
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(range(len(correlation.columns)))
    ax.set_yticks(range(len(correlation.index)))

    ax.set_xticklabels(
        correlation.columns,
        rotation=45,
        ha="right",
        fontsize=9,
    )

    ax.set_yticklabels(
        correlation.index,
        fontsize=9,
    )

    for i in range(correlation.shape[0]):
        for j in range(correlation.shape[1]):
            value = correlation.iloc[i, j]

            if pd.notna(value):
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                )

    ax.set_title(
        "N100 Financial KPI Pearson Correlation",
        fontsize=14,
        pad=15,
    )

    fig.colorbar(
        image,
        ax=ax,
        fraction=0.046,
        pad=0.04,
        label="Pearson correlation",
    )

    fig.tight_layout()
    fig.savefig(
        output_path,
        dpi=160,
        bbox_inches="tight",
    )
    plt.close(fig)

    return output_path


# ---------------------------------------------------------------------
# Sector Z-score outliers
# ---------------------------------------------------------------------


OUTLIER_KPIS = {
    "net_profit_margin_pct": "Net Profit Margin",
    "operating_profit_margin_pct": "Operating Profit Margin",
    "return_on_equity_pct": "ROE",
    "return_on_capital_employed_pct": "ROCE",
    "return_on_assets_pct": "ROA",
    "debt_to_equity": "Debt to Equity",
    "interest_coverage": "Interest Coverage",
    "asset_turnover": "Asset Turnover",
    "revenue_cagr_5yr": "Revenue CAGR 5Y",
    "eps_cagr_5yr": "EPS CAGR 5Y",
}


def calculate_sector_outliers() -> pd.DataFrame:
    """
    Calculate sector-level Z-scores for ten financial KPIs.

    A row is flagged when the absolute Z-score is >= 2.0.
    Sectors with fewer than three observations are excluded from
    statistical Z-score flagging because their estimates are unstable.
    """
    latest = load_latest_financials()
    company_sector = load_company_sector_data()

    df = latest.merge(
        company_sector[
            [
                "company_id",
                "company_name",
                "broad_sector",
            ]
        ],
        on="company_id",
        how="left",
        validate="one_to_one",
    )

    results = []

    for sector, sector_group in df.groupby(
        "broad_sector",
        dropna=False,
    ):
        sector_group = sector_group.copy()

        sector_size = len(sector_group)

        if sector_size < 3:
            continue

        for column, label in OUTLIER_KPIS.items():
            values = sector_group[column].dropna()

            if len(values) < 3:
                continue

            mean = values.mean()
            std = values.std(ddof=0)

            if pd.isna(std) or std == 0:
                continue

            sector_group[f"{column}_z"] = (
                (sector_group[column] - mean) / std
            )

            for _, row in sector_group.dropna(
                subset=[f"{column}_z"]
            ).iterrows():

                z_score = row[f"{column}_z"]

                if abs(z_score) >= 2.0:
                    direction = (
                        "High"
                        if z_score > 0
                        else "Low"
                    )

                    results.append(
                        {
                            "company_id": row["company_id"],
                            "company_name": row["company_name"],
                            "broad_sector": sector,
                            "kpi": label,
                            "kpi_column": column,
                            "value": row[column],
                            "sector_mean": mean,
                            "sector_std": std,
                            "z_score": z_score,
                            "direction": direction,
                            "outlier_flag": True,
                        }
                    )

    result = pd.DataFrame(results)

    if result.empty:
        result = pd.DataFrame(
            columns=[
                "company_id",
                "company_name",
                "broad_sector",
                "kpi",
                "kpi_column",
                "value",
                "sector_mean",
                "sector_std",
                "z_score",
                "direction",
                "outlier_flag",
            ]
        )
    else:
        result = result.sort_values(
            ["broad_sector", "kpi", "z_score"],
            key=lambda s: (
                s.abs()
                if s.name == "z_score"
                else s
            ),
        ).reset_index(drop=True)

    return result


# ---------------------------------------------------------------------
# Portfolio statistics
# ---------------------------------------------------------------------


def create_portfolio_statistics() -> pd.DataFrame:
    """Create portfolio-wide financial statistics."""
    latest = load_latest_financials()
    company_sector = load_company_sector_data()

    df = latest.merge(
        company_sector,
        on="company_id",
        how="left",
        validate="one_to_one",
    )

    statistics = []

    metric_columns = {
        "return_on_equity_pct": "ROE",
        "return_on_capital_employed_pct": "ROCE",
        "return_on_assets_pct": "ROA",
        "debt_to_equity": "Debt to Equity",
        "interest_coverage": "Interest Coverage",
        "asset_turnover": "Asset Turnover",
        "net_profit_margin_pct": "Net Profit Margin",
        "operating_profit_margin_pct": "Operating Profit Margin",
        "revenue_cagr_5yr": "Revenue CAGR 5Y",
        "pat_cagr_5yr": "PAT CAGR 5Y",
        "eps_cagr_5yr": "EPS CAGR 5Y",
        "fcf_cagr_5yr": "FCF CAGR 5Y",
        "cfo_quality_ratio": "CFO Quality Ratio",
        "capex_intensity_pct": "CapEx Intensity",
        "fcf_conversion_pct": "FCF Conversion",
        "composite_quality_score": "Composite Quality Score",
    }

    for column, label in metric_columns.items():
        values = numeric(df[column]).dropna()

        if values.empty:
            continue

        statistics.extend(
            [
                {
                    "statistic_group": "Portfolio KPI",
                    "metric": label,
                    "statistic": "count",
                    "value": float(values.count()),
                },
                {
                    "statistic_group": "Portfolio KPI",
                    "metric": label,
                    "statistic": "mean",
                    "value": float(values.mean()),
                },
                {
                    "statistic_group": "Portfolio KPI",
                    "metric": label,
                    "statistic": "median",
                    "value": float(values.median()),
                },
                {
                    "statistic_group": "Portfolio KPI",
                    "metric": label,
                    "statistic": "min",
                    "value": float(values.min()),
                },
                {
                    "statistic_group": "Portfolio KPI",
                    "metric": label,
                    "statistic": "max",
                    "value": float(values.max()),
                },
            ]
        )

    sector_counts = (
        df["broad_sector"]
        .value_counts()
        .sort_index()
    )

    for sector, count in sector_counts.items():
        statistics.append(
            {
                "statistic_group": "Sector Distribution",
                "metric": sector,
                "statistic": "company_count",
                "value": float(count),
            }
        )

    market_cap_counts = (
        df["market_cap_category"]
        .fillna("Unknown")
        .value_counts()
        .sort_index()
    )

    for category, count in market_cap_counts.items():
        statistics.append(
            {
                "statistic_group": "Market Cap Distribution",
                "metric": category,
                "statistic": "company_count",
                "value": float(count),
            }
        )

    return pd.DataFrame(statistics)


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def validate_outputs(
    profiles: pd.DataFrame,
    correlation: pd.DataFrame,
    outliers: pd.DataFrame,
    portfolio: pd.DataFrame,
) -> None:
    """Validate all Day 37 outputs."""
    print()
    print("DAY 37 VALIDATION")
    print("=" * 70)

    # Cluster profiles
    assert len(profiles) == 5, (
        f"Expected 5 cluster profiles, found {len(profiles)}"
    )

    assert profiles["cluster_id"].nunique() == 5

    print(f"Cluster profiles : {len(profiles)}")

    # Correlation
    assert correlation.shape == (10, 10), (
        f"Expected 10x10 correlation matrix, found {correlation.shape}"
    )

    assert np.allclose(
        correlation.values,
        correlation.values.T,
        equal_nan=True,
    )

    print(f"Correlation matrix: {correlation.shape}")

    # Outliers
    print(f"Sector outliers  : {len(outliers)}")

    # Portfolio
    assert len(portfolio) > 0

    print(f"Portfolio stats  : {len(portfolio)} rows")

    print()
    print("Cluster distribution:")
    print(
        profiles[
            [
                "cluster_id",
                "cluster_name",
                "company_count",
            ]
        ].to_string(index=False)
    )

    print()
    print("Sector outlier count:")
    if outliers.empty:
        print("No |Z| >= 2.0 sector outliers detected.")
    else:
        print(
            outliers["broad_sector"]
            .value_counts()
            .sort_index()
            .to_string()
        )

    print()
    print("Day 37 validation completed successfully.")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


def main() -> None:
    """Run the complete Sprint 6 Day 37 analysis."""
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
    )

    print()
    print("N100 FINANCIAL INTELLIGENCE")
    print("SPRINT 6 - DAY 37")
    print("CLUSTER PROFILES / KPI CORRELATION / OUTLIERS / PORTFOLIO")
    print("=" * 70)
    print(f"Database: {DB_PATH}")

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    # ---------------------------------------------------------------
    # Cluster profiles
    # ---------------------------------------------------------------

    print()
    print("1. Creating cluster profiles...")

    profiles = create_cluster_profiles()

    profiles_path = OUTPUT_DIR / "cluster_profiles.csv"
    profiles.to_csv(
        profiles_path,
        index=False,
        float_format="%.6f",
    )

    print(
        f"   Saved: {profiles_path}"
    )

    # ---------------------------------------------------------------
    # KPI correlation
    # ---------------------------------------------------------------

    print()
    print("2. Creating 10-KPI Pearson correlation matrix...")

    correlation = create_kpi_correlation()

    correlation_path = OUTPUT_DIR / "kpi_correlation.csv"

    correlation.to_csv(
        correlation_path,
        index=True,
        float_format="%.6f",
    )

    heatmap_path = create_correlation_heatmap(
        correlation
    )

    print(
        f"   Saved: {correlation_path}"
    )
    print(
        f"   Saved: {heatmap_path}"
    )

    # ---------------------------------------------------------------
    # Sector outliers
    # ---------------------------------------------------------------

    print()
    print("3. Detecting sector-level Z-score outliers...")

    outliers = calculate_sector_outliers()

    outliers_path = OUTPUT_DIR / "sector_outliers.csv"

    outliers.to_csv(
        outliers_path,
        index=False,
        float_format="%.6f",
    )

    print(
        f"   Saved: {outliers_path}"
    )

    # ---------------------------------------------------------------
    # Portfolio statistics
    # ---------------------------------------------------------------

    print()
    print("4. Creating portfolio statistics...")

    portfolio = create_portfolio_statistics()

    portfolio_path = OUTPUT_DIR / "portfolio_statistics.csv"

    portfolio.to_csv(
        portfolio_path,
        index=False,
        float_format="%.6f",
    )

    print(
        f"   Saved: {portfolio_path}"
    )

    # ---------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------

    validate_outputs(
        profiles,
        correlation,
        outliers,
        portfolio,
    )

    print()
    print("OUTPUT FILES")
    print("=" * 70)
    print(profiles_path)
    print(correlation_path)
    print(outliers_path)
    print(portfolio_path)
    print(heatmap_path)

    print()
    print("Sprint 6 Day 37 completed successfully.")


if __name__ == "__main__":
    main()