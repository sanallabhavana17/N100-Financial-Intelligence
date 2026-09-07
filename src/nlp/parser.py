from pathlib import Path
import re
import sqlite3

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURATION
# ============================================================

TARGET_FIELDS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

# Required Sprint 5 pattern:
# 10 Years: 21%
# 5 Years: 24%
# 3 Years: 17%
#
# Also allows negative values such as:
# 1 Year: -2%
#
# The parser deliberately does NOT parse TTM or Last Year
# because the Sprint 5 target is period-based CAGR text.
PATTERN = re.compile(
    r"(\d+)\s*Years?:?\s*(-?\d+(?:\.\d+)?)\s*%"
)


# ============================================================
# DATABASE
# ============================================================

def load_analysis() -> pd.DataFrame:
    """Load analysis records from SQLite."""

    conn = sqlite3.connect(DB_PATH)

    try:
        return pd.read_sql_query(
            """
            SELECT
                company_id,
                compounded_sales_growth,
                compounded_profit_growth,
                stock_price_cagr,
                roe
            FROM analysis
            ORDER BY company_id, id
            """,
            conn,
        )
    finally:
        conn.close()


# ============================================================
# PARSER
# ============================================================

def parse_value(text):
    """
    Parse period and percentage from analysis text.

    Examples:
        '10 Years: 21%' -> (10, 21.0)
        '5 Years: 24%'  -> (5, 24.0)
        '3 Years: -2%'  -> (3, -2.0)

    Returns:
        (period_years, value_pct)
        or None if the text does not match.
    """

    if text is None or pd.isna(text):
        return None

    text = str(text).strip()

    match = PATTERN.search(text)

    if not match:
        return None

    period_years = int(match.group(1))
    value_pct = float(match.group(2))

    return period_years, value_pct


# ============================================================
# BUILD PARSED OUTPUT
# ============================================================

def build_parsed_output(df: pd.DataFrame):
    """Parse all target analysis fields."""

    parsed_rows = []
    failure_rows = []

    for _, row in df.iterrows():

        company_id = row["company_id"]

        for metric_type in TARGET_FIELDS:

            raw_text = row[metric_type]

            if raw_text is None or pd.isna(raw_text):
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "raw_text": raw_text,
                        "reason": "Missing value",
                    }
                )
                continue

            parsed = parse_value(raw_text)

            if parsed is None:

                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "raw_text": str(raw_text),
                        "reason": "Pattern not matched",
                    }
                )

                continue

            period_years, value_pct = parsed

            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failures_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "raw_text",
            "reason",
        ],
    )

    return parsed_df, failures_df


# ============================================================
# CROSS VALIDATION
# ============================================================

def cross_validate(parsed_df: pd.DataFrame):
    """
    Compare parsed CAGR values against the financial ratio
    engine where matching 3/5/10-year CAGR fields exist.

    Divergence greater than 5 percentage points is reported
    for manual review.
    """

    conn = sqlite3.connect(DB_PATH)

    try:
        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                revenue_cagr_3yr,
                revenue_cagr_5yr,
                revenue_cagr_10yr,
                pat_cagr_3yr,
                pat_cagr_5yr,
                pat_cagr_10yr,
                eps_cagr_3yr,
                eps_cagr_10yr,
                return_on_equity_pct
            FROM financial_ratios
            """,
            conn,
        )
    finally:
        conn.close()

    if ratios.empty or parsed_df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "metric_type",
                "period_years",
                "parsed_value_pct",
                "computed_value_pct",
                "divergence_pct",
                "review_flag",
            ]
        )

    # Use the latest available ratio record for each company.
    ratios = (
        ratios
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    ratio_map = {
        "compounded_sales_growth": {
            3: "revenue_cagr_3yr",
            5: "revenue_cagr_5yr",
            10: "revenue_cagr_10yr",
        },
        "compounded_profit_growth": {
            3: "pat_cagr_3yr",
            5: "pat_cagr_5yr",
            10: "pat_cagr_10yr",
        },
        "stock_price_cagr": {},
        "roe": {},
    }

    comparison_rows = []

    for _, row in parsed_df.iterrows():

        company_id = row["company_id"]
        metric_type = row["metric_type"]
        period_years = int(row["period_years"])
        parsed_value = float(row["value_pct"])

        mapping = ratio_map.get(metric_type, {})
        ratio_column = mapping.get(period_years)

        if ratio_column is None:
            continue

        company_ratios = ratios[
            ratios["company_id"] == company_id
        ]

        if company_ratios.empty:
            continue

        computed_value = company_ratios.iloc[0][ratio_column]

        if pd.isna(computed_value):
            continue

        computed_value = float(computed_value)

        divergence = abs(parsed_value - computed_value)

        comparison_rows.append(
            {
                "company_id": company_id,
                "metric_type": metric_type,
                "period_years": period_years,
                "parsed_value_pct": parsed_value,
                "computed_value_pct": computed_value,
                "divergence_pct": divergence,
                "review_flag": divergence > 5,
            }
        )

    return pd.DataFrame(comparison_rows)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("N100 NLP ANALYSIS PARSER")
    print("=" * 60)

    df = load_analysis()

    print(f"Analysis rows loaded: {len(df)}")

    parsed_df, failures_df = build_parsed_output(df)

    # --------------------------------------------------------
    # Save parsed data
    # --------------------------------------------------------

    parsed_path = OUTPUT_DIR / "analysis_parsed.csv"

    parsed_df.to_csv(
        parsed_path,
        index=False,
    )

    # --------------------------------------------------------
    # Save parse failures
    # --------------------------------------------------------

    failures_path = OUTPUT_DIR / "parse_failures.csv"

    failures_df.to_csv(
        failures_path,
        index=False,
    )

    # --------------------------------------------------------
    # Cross-validation
    # --------------------------------------------------------

    comparison_df = cross_validate(parsed_df)

    review_df = comparison_df[
        comparison_df["review_flag"] == True
    ].copy()

    review_path = OUTPUT_DIR / "parse_divergence_review.csv"

    review_df.to_csv(
        review_path,
        index=False,
    )

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print(f"Parsed rows:   {len(parsed_df)}")
    print(f"Parse failures: {len(failures_df)}")
    print(f"Divergence checks: {len(comparison_df)}")
    print(f"Manual reviews (>5): {len(review_df)}")

    print()
    print(f"Parsed output: {parsed_path}")
    print(f"Failure log:   {failures_path}")
    print(f"Review output: {review_path}")

    print()
    print("Metric distribution:")

    if not parsed_df.empty:
        print(
            parsed_df[
                "metric_type"
            ]
            .value_counts()
            .to_string()
        )

    print()
    print("Period distribution:")

    if not parsed_df.empty:
        print(
            parsed_df[
                "period_years"
            ]
            .value_counts()
            .sort_index()
            .to_string()
        )


if __name__ == "__main__":
    main()