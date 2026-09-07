"""
N100 Financial Intelligence
Sprint 5 - Day 31
Cash Flow Intelligence Engine

Outputs:
    output/cashflow_intelligence.xlsx
    output/distress_alerts.csv

Covers all 92 NIFTY 100 companies.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"

INTELLIGENCE_FILE = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_FILE = OUTPUT_DIR / "distress_alerts.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_float(value):
    """Safely convert a value to float."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    try:
        text = str(value).strip()

        if not text or text.lower() in {
            "nan",
            "none",
            "null",
            "n/a",
            "na",
            "-",
        }:
            return None

        return float(text.replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def is_valid(value):
    return value is not None and math.isfinite(value)


# ---------------------------------------------------------------------------
# Classification functions
# ---------------------------------------------------------------------------

def classify_cfo_quality(cfo_pat):
    """
    CFO / PAT:

        > 1.0       High Quality
        0.5 - 1.0   Moderate
        < 0.5       Accrual Risk
    """

    if not is_valid(cfo_pat):
        return None

    if cfo_pat > 1.0:
        return "High Quality"

    if cfo_pat >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def calculate_capex_intensity(investing_activity, sales):
    """
    CapEx Intensity = abs(investing activity) / sales * 100
    """

    if not is_valid(investing_activity):
        return None

    if not is_valid(sales) or sales == 0:
        return None

    return abs(investing_activity) / abs(sales) * 100


def classify_capex(capex_intensity):
    """
        < 3%       Asset Light
        3 - 8%     Moderate
        > 8%       Capital Intensive
    """

    if not is_valid(capex_intensity):
        return None

    if capex_intensity < 3:
        return "Asset Light"

    if capex_intensity <= 8:
        return "Moderate"

    return "Capital Intensive"


def calculate_cagr(start_value, end_value, years=5):
    """
    CAGR calculation.

    CAGR is meaningful only when both endpoints are positive.
    """

    if not is_valid(start_value) or not is_valid(end_value):
        return None

    if start_value <= 0 or end_value <= 0:
        return None

    if years <= 0:
        return None

    return ((end_value / start_value) ** (1 / years) - 1) * 100


# ---------------------------------------------------------------------------
# Capital allocation
# ---------------------------------------------------------------------------

def sign(value):
    if not is_valid(value):
        return "0"

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


def capital_allocation_pattern(cfo, cfi, cff, cfo_pat_ratio=None):
    """
    Capital allocation classification.

    (+,-,-) -> Reinvestor
    (+,-,-) with CFO/PAT > 1 -> Shareholder Returns
    (+,+,-) -> Liquidating Assets
    (-,+,+) -> Distress Signal
    (-,-,+) -> Growth Funded by Debt
    (+,+,+) -> Cash Accumulator
    (-,-,-) -> Pre-Revenue
    (+,-,+) -> Mixed
    """

    pattern = (
        sign(cfo),
        sign(cfi),
        sign(cff),
    )

    if pattern == ("+", "-", "-"):
        if (
            is_valid(cfo_pat_ratio)
            and cfo_pat_ratio > 1.0
        ):
            return "Shareholder Returns"

        return "Reinvestor"

    labels = {
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }

    return labels.get(pattern, "Mixed")


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_data():
    conn = sqlite3.connect(DB_PATH)

    try:
        cashflow = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                operating_activity,
                investing_activity,
                financing_activity,
                net_cash_flow
            FROM cashflow
            WHERE company_id IS NOT NULL
            ORDER BY company_id, year
            """,
            conn,
        )

        ratios = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                free_cash_flow_cr,
                cash_from_operations_cr,
                cfo_quality_ratio,
                cfo_quality_label,
                capex_intensity_pct,
                capex_intensity_label,
                fcf_conversion_pct,
                capital_allocation_pattern
            FROM financial_ratios
            WHERE company_id IS NOT NULL
            ORDER BY company_id, year
            """,
            conn,
        )

        balancesheet = pd.read_sql_query(
            """
            SELECT
                company_id,
                year,
                borrowings
            FROM balancesheet
            WHERE company_id IS NOT NULL
            ORDER BY company_id, year
            """,
            conn,
        )

        sectors = pd.read_sql_query(
            """
            SELECT
                company_id,
                broad_sector,
                sub_sector
            FROM sectors
            WHERE company_id IS NOT NULL
            """,
            conn,
        )

        profit_loss = pd.read_sql_query(
            """
            SELECT *
            FROM profitandloss
            WHERE company_id IS NOT NULL
            """,
            conn,
        )

    finally:
        conn.close()

    return (
        cashflow,
        ratios,
        balancesheet,
        sectors,
        profit_loss,
    )


# ---------------------------------------------------------------------------
# Sales lookup
# ---------------------------------------------------------------------------

def find_sales_column(df):
    """
    Identify the sales/revenue column in profitandloss.

    Returns None when no suitable column exists.
    """

    preferred = [
        "sales",
        "revenue",
        "revenue_cr",
        "sales_cr",
        "total_revenue",
    ]

    lower_map = {
        str(column).lower(): column
        for column in df.columns
    }

    for name in preferred:
        if name in lower_map:
            return lower_map[name]

    for column in df.columns:
        lower = str(column).lower()

        if "sales" in lower or "revenue" in lower:
            return column

    return None


# ---------------------------------------------------------------------------
# Build intelligence
# ---------------------------------------------------------------------------

def build_intelligence(
    cashflow,
    ratios,
    balancesheet,
    sectors,
    profit_loss,
):
    cashflow = cashflow.copy()
    ratios = ratios.copy()
    balancesheet = balancesheet.copy()

    for df in [cashflow, ratios, balancesheet]:
        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce",
        )

    # Numeric conversion
    for column in [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]:
        cashflow[column] = pd.to_numeric(
            cashflow[column],
            errors="coerce",
        )

    for column in [
        "free_cash_flow_cr",
        "cash_from_operations_cr",
        "cfo_quality_ratio",
        "capex_intensity_pct",
        "fcf_conversion_pct",
    ]:
        ratios[column] = pd.to_numeric(
            ratios[column],
            errors="coerce",
        )

    balancesheet["borrowings"] = pd.to_numeric(
        balancesheet["borrowings"],
        errors="coerce",
    )

    # -----------------------------------------------------------------------
    # FCF CAGR
    # -----------------------------------------------------------------------

    fcf_data = ratios[
        [
            "company_id",
            "year",
            "free_cash_flow_cr",
        ]
    ].copy()

    fcf_data = fcf_data.sort_values(
        ["company_id", "year"]
    )

    fcf_cagr = {}

    for company_id, group in fcf_data.groupby("company_id"):
        group = group.dropna(
            subset=["year", "free_cash_flow_cr"]
        ).sort_values("year")

        if group.empty:
            fcf_cagr[str(company_id)] = None
            continue

        latest = group.iloc[-1]

        target_year = latest["year"] - 5

        prior = group[
            group["year"] <= target_year
        ]

        if prior.empty:
            fcf_cagr[str(company_id)] = None
            continue

        start = prior.iloc[-1]["free_cash_flow_cr"]
        end = latest["free_cash_flow_cr"]

        fcf_cagr[str(company_id)] = calculate_cagr(
            start,
            end,
            5,
        )

    # -----------------------------------------------------------------------
    # Latest cash-flow row
    # -----------------------------------------------------------------------

    latest_cashflow = (
        cashflow
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    # -----------------------------------------------------------------------
    # Latest ratio row
    # -----------------------------------------------------------------------

    latest_ratios = (
        ratios
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    # -----------------------------------------------------------------------
    # Borrowings / deleveraging
    # -----------------------------------------------------------------------

    bs = balancesheet.sort_values(
        ["company_id", "year"]
    )

    deleveraging = {}

    for company_id, group in bs.groupby("company_id"):
        group = group.dropna(
            subset=["year"]
        ).sort_values("year")

        if len(group) < 2:
            deleveraging[str(company_id)] = False
            continue

        latest = group.iloc[-1]

        previous = group[
            group["year"] < latest["year"]
        ]

        if previous.empty:
            deleveraging[str(company_id)] = False
            continue

        previous = previous.iloc[-1]

        latest_borrowings = latest["borrowings"]
        previous_borrowings = previous["borrowings"]

        # Need both values to be known.
        if (
            not is_valid(latest_borrowings)
            or not is_valid(previous_borrowings)
        ):
            deleveraging[str(company_id)] = False
            continue

        # CFF condition is checked separately below.
        latest_cff = cashflow[
            (cashflow["company_id"] == company_id)
            & (cashflow["year"] == latest["year"])
        ]

        cff_negative = False

        if not latest_cff.empty:
            cff = latest_cff.iloc[0]["financing_activity"]
            cff_negative = (
                is_valid(cff) and cff < 0
            )

        deleveraging[str(company_id)] = (
            cff_negative
            and latest_borrowings < previous_borrowings
        )

    # -----------------------------------------------------------------------
    # Merge sector
    # -----------------------------------------------------------------------

    sectors = sectors.copy()

    sector_map = (
        sectors.drop_duplicates("company_id")
        .set_index("company_id")["broad_sector"]
        .to_dict()
    )

    # -----------------------------------------------------------------------
    # Build final records
    # -----------------------------------------------------------------------

    records = []

    for _, ratio_row in latest_ratios.iterrows():
        company_id = str(ratio_row["company_id"])

        cf_match = latest_cashflow[
            latest_cashflow["company_id"].astype(str)
            == company_id
        ]

        if cf_match.empty:
            continue

        cf_row = cf_match.iloc[0]

        cfo = to_float(
            cf_row["operating_activity"]
        )

        cfi = to_float(
            cf_row["investing_activity"]
        )

        cff = to_float(
            cf_row["financing_activity"]
        )

        # Existing ratio-engine values are preferred because they
        # preserve consistency with earlier sprints.
        cfo_quality_score = to_float(
            ratio_row["cfo_quality_ratio"]
        )

        if cfo_quality_score is None:
            # Fall back to CFO/PAT only when available elsewhere.
            cfo_quality_score = None

        cfo_label = classify_cfo_quality(
            cfo_quality_score
        )

        capex_pct = to_float(
            ratio_row["capex_intensity_pct"]
        )

        capex_label = classify_capex(
            capex_pct
        )

        # Distress:
        # latest CFO < 0 AND latest CFF > 0
        distress_flag = bool(
            is_valid(cfo)
            and is_valid(cff)
            and cfo < 0
            and cff > 0
        )

        # Capital allocation
        allocation_label = capital_allocation_pattern(
            cfo,
            cfi,
            cff,
            cfo_quality_score,
        )

        # Existing FCF conversion calculation.
        fcf_conversion = to_float(
            ratio_row["fcf_conversion_pct"]
        )

        records.append(
            {
                "company_id": company_id,
                "sector": sector_map.get(
                    company_id,
                    "Unknown",
                ),
                "cfo_quality_score": cfo_quality_score,
                "cfo_quality_label": cfo_label,
                "capex_intensity_pct": capex_pct,
                "capex_label": capex_label,
                "fcf_cagr_5yr": fcf_cagr.get(
                    company_id
                ),
                "fcf_conversion_pct": fcf_conversion,
                "distress_flag": distress_flag,
                "deleveraging_flag": bool(
                    deleveraging.get(
                        company_id,
                        False,
                    )
                ),
                "capital_allocation_label": allocation_label,
            }
        )

    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("N100 CASH FLOW INTELLIGENCE")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        cashflow,
        ratios,
        balancesheet,
        sectors,
        profit_loss,
    ) = load_data()

    print(f"Cash-flow rows:       {len(cashflow):,}")
    print(f"Ratio rows:           {len(ratios):,}")
    print(f"Balance-sheet rows:   {len(balancesheet):,}")
    print(f"Sector rows:          {len(sectors):,}")

    result = build_intelligence(
        cashflow,
        ratios,
        balancesheet,
        sectors,
        profit_loss,
    )

    expected_columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    result = result[expected_columns]

    result = result.sort_values(
        ["sector", "company_id"]
    ).reset_index(drop=True)

    # -----------------------------------------------------------------------
    # Distress alerts
    # -----------------------------------------------------------------------

    distress = result[
        result["distress_flag"] == True
    ].copy()

    # -----------------------------------------------------------------------
    # Save Excel
    # -----------------------------------------------------------------------

    with pd.ExcelWriter(
        INTELLIGENCE_FILE,
        engine="openpyxl",
    ) as writer:
        result.to_excel(
            writer,
            sheet_name="cashflow_intelligence",
            index=False,
        )

        # Distribution summary
        summary = pd.DataFrame(
            {
                "Metric": [
                    "Companies",
                    "High Quality CFO",
                    "Moderate CFO",
                    "Accrual Risk CFO",
                    "Asset Light",
                    "Moderate CapEx",
                    "Capital Intensive",
                    "Distress Flags",
                    "Deleveraging Flags",
                ],
                "Count": [
                    result["company_id"].nunique(),
                    (
                        result["cfo_quality_label"]
                        == "High Quality"
                    ).sum(),
                    (
                        result["cfo_quality_label"]
                        == "Moderate"
                    ).sum(),
                    (
                        result["cfo_quality_label"]
                        == "Accrual Risk"
                    ).sum(),
                    (
                        result["capex_label"]
                        == "Asset Light"
                    ).sum(),
                    (
                        result["capex_label"]
                        == "Moderate"
                    ).sum(),
                    (
                        result["capex_label"]
                        == "Capital Intensive"
                    ).sum(),
                    result["distress_flag"].sum(),
                    result["deleveraging_flag"].sum(),
                ],
            }
        )

        summary.to_excel(
            writer,
            sheet_name="summary",
            index=False,
        )

    # -----------------------------------------------------------------------
    # Save distress CSV
    # -----------------------------------------------------------------------

    distress.to_csv(
        DISTRESS_FILE,
        index=False,
        encoding="utf-8",
    )

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    print()
    print("OUTPUT VALIDATION")
    print("-" * 70)

    print(
        f"Companies in intelligence: "
        f"{result['company_id'].nunique()}"
    )

    print(
        f"Output rows:               "
        f"{len(result)}"
    )

    print(
        f"Distress alerts:           "
        f"{len(distress)}"
    )

    print(
        f"Deleveraging companies:    "
        f"{result['deleveraging_flag'].sum()}"
    )

    print()
    print("CFO Quality:")
    print(
        result["cfo_quality_label"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("CapEx:")
    print(
        result["capex_label"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("Capital Allocation:")
    print(
        result["capital_allocation_label"]
        .value_counts(dropna=False)
        .to_string()
    )

    print()
    print("Distress / Deleveraging:")
    print(
        result[
            [
                "distress_flag",
                "deleveraging_flag",
            ]
        ]
        .sum()
        .to_string()
    )

    print()

    missing_companies = 92 - result["company_id"].nunique()

    if missing_companies != 0:
        raise RuntimeError(
            f"Expected 92 companies but found "
            f"{result['company_id'].nunique()}."
        )

    print(f"Saved: {INTELLIGENCE_FILE}")
    print(f"Saved: {DISTRESS_FILE}")
    print()
    print("Day 31 Cash Flow Intelligence completed successfully.")


if __name__ == "__main__":
    main()