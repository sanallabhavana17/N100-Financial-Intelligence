"""
Sprint 3 - Day 18
Peer Comparison Module

Creates a peer-group percentile table using:
- financial_ratios table
- peer_groups table

Output:
    output/peer_percentile_table.csv
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_FILE = OUTPUT_DIR / "peer_percentile_table.csv"


# ============================================================
# METRIC CONFIGURATION
# ============================================================

# True  = higher value is better
# False = lower value is better

HIGHER_IS_BETTER = {
    "return_on_equity_pct": True,
    "return_on_capital_employed_pct": True,
    "return_on_assets_pct": True,
    "net_profit_margin_pct": True,
    "operating_profit_margin_pct": True,
    "debt_to_equity": False,
    "interest_coverage": True,
    "revenue_cagr_5yr": True,
    "pat_cagr_5yr": True,
    "eps_cagr_5yr": True,
    "free_cash_flow_cr": True,
    "asset_turnover": True,
    "composite_quality_score": True,
}

PEER_METRICS = list(HIGHER_IS_BETTER.keys())


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """Create SQLite database connection."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


# ============================================================
# LOAD DATA
# ============================================================

def load_peer_data():
    """
    Load peer-group membership and financial ratio data.
    """

    query = """
        SELECT
            pg.peer_group_name,
            pg.company_id,
            pg.is_benchmark,
            fr.year,

            fr.return_on_equity_pct,
            fr.return_on_capital_employed_pct,
            fr.return_on_assets_pct,
            fr.net_profit_margin_pct,
            fr.operating_profit_margin_pct,
            fr.debt_to_equity,
            fr.interest_coverage,

            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr,
            fr.eps_cagr_5yr,

            fr.free_cash_flow_cr,
            fr.asset_turnover,
            fr.composite_quality_score

        FROM peer_groups AS pg

        INNER JOIN financial_ratios AS fr
            ON pg.company_id = fr.company_id

        ORDER BY
            pg.peer_group_name,
            fr.year,
            pg.company_id
    """

    with get_connection() as con:
        df = pd.read_sql_query(query, con)

    return df


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_input_data(df):
    """Validate input peer-group data."""

    required_columns = [
        "peer_group_name",
        "company_id",
        "is_benchmark",
        "year",
        *PEER_METRICS,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError(
            "Peer input data is empty."
        )

    duplicate_count = (
        df.groupby(
            [
                "peer_group_name",
                "company_id",
                "year",
            ]
        )
        .size()
        .gt(1)
        .sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            f"Found {duplicate_count} duplicate "
            "peer-group/company/year combinations."
        )

    print(
        f"Peer groups found: "
        f"{df['peer_group_name'].nunique()}"
    )

    print(
        f"Companies in peer memberships: "
        f"{df['company_id'].nunique()}"
    )

    print(
        f"Rows loaded: {len(df)}"
    )


# ============================================================
# PERCENTILE CALCULATION
# ============================================================

def calculate_percentile(
    series,
    higher_is_better=True,
):
    """
    Calculate percentile rank from 0 to 100.

    Higher-is-better:
        highest value receives highest percentile.

    Lower-is-better:
        lowest value receives highest percentile.
    """

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid_count = numeric.notna().sum()

    if valid_count == 0:
        return pd.Series(
            np.nan,
            index=series.index,
        )

    if valid_count == 1:
        return pd.Series(
            np.where(
                numeric.notna(),
                100.0,
                np.nan,
            ),
            index=series.index,
        )

    if higher_is_better:
        percentile = (
            numeric.rank(
                method="average",
                ascending=True,
                pct=True,
            )
            * 100
        )

    else:
        percentile = (
            numeric.rank(
                method="average",
                ascending=False,
                pct=True,
            )
            * 100
        )

    return percentile


def calculate_peer_percentiles(df):
    """
    Calculate percentile rankings within each
    peer group and year.
    """

    result = df.copy()

    group_columns = [
        "peer_group_name",
        "year",
    ]

    for metric in PEER_METRICS:

        percentile_column = (
            f"{metric}_percentile"
        )

        result[percentile_column] = (
            result.groupby(
                group_columns,
                group_keys=False,
            )[metric]
            .transform(
                lambda series: calculate_percentile(
                    series,
                    HIGHER_IS_BETTER[metric],
                )
            )
        )

    percentile_columns = [
        f"{metric}_percentile"
        for metric in PEER_METRICS
    ]

    result["peer_composite_percentile"] = (
        result[percentile_columns]
        .mean(
            axis=1,
            skipna=True,
        )
    )

    return result


# ============================================================
# PEER RANKING
# ============================================================

def add_peer_rank(df):
    """Add peer rank and peer-group size."""

    result = df.copy()

    result["peer_rank"] = (
        result.groupby(
            [
                "peer_group_name",
                "year",
            ]
        )["peer_composite_percentile"]
        .rank(
            method="min",
            ascending=False,
        )
    )

    result["peer_group_size"] = (
        result.groupby(
            [
                "peer_group_name",
                "year",
            ]
        )["company_id"]
        .transform("count")
    )

    return result


# ============================================================
# BENCHMARK COMPARISON
# ============================================================

def add_benchmark_comparison(df):
    """
    Identify benchmark company for each peer group/year
    and calculate difference from benchmark.
    """

    result = df.copy()

    result["is_benchmark"] = (
        pd.to_numeric(
            result["is_benchmark"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    benchmark_rows = result[
        result["is_benchmark"] == 1
    ].copy()

    benchmark_lookup = (
        benchmark_rows[
            [
                "peer_group_name",
                "year",
                "company_id",
                "peer_composite_percentile",
            ]
        ]
        .rename(
            columns={
                "company_id": "benchmark_company_id",
                "peer_composite_percentile":
                    "benchmark_composite_percentile",
            }
        )
    )

    result = result.merge(
        benchmark_lookup,
        on=[
            "peer_group_name",
            "year",
        ],
        how="left",
    )

    result["vs_benchmark_percentile"] = (
        result["peer_composite_percentile"]
        - result["benchmark_composite_percentile"]
    )

    result["above_benchmark"] = (
        result["peer_composite_percentile"]
        > result["benchmark_composite_percentile"]
    )

    return result


# ============================================================
# OUTPUT FORMATTING
# ============================================================

def format_output(df):
    """Select and order final output columns."""

    percentile_columns = [
        f"{metric}_percentile"
        for metric in PEER_METRICS
    ]

    output_columns = [
        "peer_group_name",
        "company_id",
        "year",
        "is_benchmark",
        "peer_rank",
        "peer_group_size",
        "peer_composite_percentile",
        "benchmark_company_id",
        "benchmark_composite_percentile",
        "vs_benchmark_percentile",
        "above_benchmark",

        *PEER_METRICS,

        *percentile_columns,
    ]

    output = df[
        output_columns
    ].copy()

    output = output.sort_values(
        [
            "peer_group_name",
            "year",
            "peer_rank",
            "company_id",
        ],
        na_position="last",
    )

    return output


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_output(df):
    """Validate generated peer percentile table."""

    print("\nOUTPUT VALIDATION")
    print("-" * 60)

    # --------------------------------------------------------
    # Duplicate validation
    # --------------------------------------------------------

    duplicate_count = (
        df.groupby(
            [
                "peer_group_name",
                "company_id",
                "year",
            ]
        )
        .size()
        .gt(1)
        .sum()
    )

    print(
        f"Duplicate peer/company/year groups: "
        f"{duplicate_count}"
    )

    if duplicate_count != 0:
        raise ValueError(
            "Output contains duplicate "
            "peer/company/year rows."
        )

    # --------------------------------------------------------
    # Percentile validation
    # --------------------------------------------------------

    # Only actual metric percentile columns are checked.
    # vs_benchmark_percentile is intentionally excluded
    # because it can legitimately be negative.

    percentile_columns = [
        f"{metric}_percentile"
        for metric in PEER_METRICS
    ]

    invalid_percentiles = 0

    for column in percentile_columns:

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        ).dropna()

        invalid = (
            (values < 0)
            | (values > 100)
        ).sum()

        invalid_percentiles += int(invalid)

    print(
        f"Invalid metric percentile values: "
        f"{invalid_percentiles}"
    )

    if invalid_percentiles != 0:
        raise ValueError(
            "Metric percentile values outside "
            "0-100 detected."
        )

    # --------------------------------------------------------
    # Peer group validation
    # --------------------------------------------------------

    total_peer_groups = (
        df["peer_group_name"]
        .nunique()
    )

    benchmark_peer_groups = (
        df[
            df["is_benchmark"] == 1
        ]["peer_group_name"]
        .nunique()
    )

    print(
        f"Peer groups with benchmark: "
        f"{benchmark_peer_groups}/"
        f"{total_peer_groups}"
    )

    # --------------------------------------------------------
    # Composite percentile validation
    # --------------------------------------------------------

    composite_values = (
        pd.to_numeric(
            df["peer_composite_percentile"],
            errors="coerce",
        )
        .dropna()
    )

    invalid_composite = (
        (composite_values < 0)
        | (composite_values > 100)
    ).sum()

    print(
        f"Invalid composite percentile values: "
        f"{invalid_composite}"
    )

    if invalid_composite != 0:
        raise ValueError(
            "Composite percentile values outside "
            "0-100 detected."
        )

    # --------------------------------------------------------
    # Range
    # --------------------------------------------------------

    if len(composite_values) > 0:

        print(
            f"Composite percentile range: "
            f"{composite_values.min():.2f} - "
            f"{composite_values.max():.2f}"
        )

    print(
        f"Final rows: {len(df)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("NIFTY100 PEER COMPARISON MODULE")
    print("SPRINT 3 - DAY 18")
    print("=" * 60)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print(
        "\nLoading peer-group and financial "
        "ratio data..."
    )

    df = load_peer_data()

    validate_input_data(df)

    # --------------------------------------------------------
    # Percentiles
    # --------------------------------------------------------

    print(
        "\nCalculating peer-group percentiles..."
    )

    df = calculate_peer_percentiles(df)

    # --------------------------------------------------------
    # Rank
    # --------------------------------------------------------

    print(
        "Adding peer ranks..."
    )

    df = add_peer_rank(df)

    # --------------------------------------------------------
    # Benchmark
    # --------------------------------------------------------

    print(
        "Adding benchmark comparison..."
    )

    df = add_benchmark_comparison(df)

    # --------------------------------------------------------
    # Format
    # --------------------------------------------------------

    output = format_output(df)

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_output(output)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("PEER COMPARISON COMPLETE")
    print("=" * 60)

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Rows: {len(output)}"
    )

    print(
        f"Peer groups: "
        f"{output['peer_group_name'].nunique()}"
    )

    print(
        f"Companies: "
        f"{output['company_id'].nunique()}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()