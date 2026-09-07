"""
N100 Financial Intelligence
Sprint 5 - Day 30
NLP Pros / Cons Generator

Generates rule-based investment pros and cons for all 92 companies.

Output:
    output/pros_cons_generated.csv

Columns:
    company_id
    type
    rule_id
    text
    confidence_pct
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

OUTPUT_FILE = OUTPUT_DIR / "pros_cons_generated.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_float(value):
    """Safely convert database values to float."""
    if value is None:
        return None

    if isinstance(value, bool):
        return float(value)

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

        text = text.replace(",", "").replace("%", "")

        return float(text)
    except (TypeError, ValueError):
        return None


def is_valid(value):
    return value is not None and math.isfinite(value)


def fmt_pct(value):
    """Format percentage values cleanly."""
    if not is_valid(value):
        return "N/A"
    return f"{value:.1f}%"


def fmt_num(value):
    if not is_valid(value):
        return "N/A"
    return f"{value:.2f}"


def latest_rows(df):
    """
    Select the latest available financial-ratio row for every company.
    """
    df = df.copy()

    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = (
        df.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    return df


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

def generate_pros(row):
    """
    12 Pro rules.

    Each rule returns:
        (rule_id, text, confidence)
    """

    pros = []

    revenue_5y = to_float(row.get("revenue_cagr_5yr"))
    profit_5y = to_float(row.get("pat_cagr_5yr"))
    eps_5y = to_float(row.get("eps_cagr_5yr"))

    roe = to_float(row.get("return_on_equity_pct"))
    roce = to_float(row.get("return_on_capital_employed_pct"))
    roa = to_float(row.get("return_on_assets_pct"))

    debt_equity = to_float(row.get("debt_to_equity"))
    interest_coverage = to_float(row.get("interest_coverage"))

    cfo_quality = to_float(row.get("cfo_quality_ratio"))
    fcf_conversion = to_float(row.get("fcf_conversion_pct"))

    dividend_payout = to_float(row.get("dividend_payout_ratio_pct"))

    capex_intensity = to_float(row.get("capex_intensity_pct"))

    # ---------------------------------------------------------------
    # PRO 01 - Strong revenue growth
    # ---------------------------------------------------------------

    if is_valid(revenue_5y) and revenue_5y >= 15:
        confidence = min(98, 65 + revenue_5y)

        pros.append(
            (
                "PRO_01",
                f"Strong 5-year revenue growth of {fmt_pct(revenue_5y)} "
                f"indicates healthy business expansion.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 02 - Strong profit growth
    # ---------------------------------------------------------------

    if is_valid(profit_5y) and profit_5y >= 15:
        confidence = min(98, 65 + profit_5y)

        pros.append(
            (
                "PRO_02",
                f"Strong 5-year profit growth of {fmt_pct(profit_5y)} "
                f"shows good earnings expansion.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 03 - Strong EPS growth
    # ---------------------------------------------------------------

    if is_valid(eps_5y) and eps_5y >= 15:
        confidence = min(97, 65 + eps_5y)

        pros.append(
            (
                "PRO_03",
                f"EPS grew at {fmt_pct(eps_5y)} over 5 years, "
                f"supporting improving shareholder earnings.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 04 - Strong ROE
    # ---------------------------------------------------------------

    if is_valid(roe) and roe >= 15:
        confidence = min(98, 70 + (roe - 15) * 1.5)

        pros.append(
            (
                "PRO_04",
                f"ROE of {fmt_pct(roe)} indicates efficient use "
                f"of shareholder capital.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 05 - Strong ROCE
    # ---------------------------------------------------------------

    if is_valid(roce) and roce >= 15:
        confidence = min(98, 70 + (roce - 15) * 1.5)

        pros.append(
            (
                "PRO_05",
                f"ROCE of {fmt_pct(roce)} indicates efficient "
                f"deployment of operating capital.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 06 - Healthy ROA
    # ---------------------------------------------------------------

    if is_valid(roa) and roa >= 8:
        confidence = min(95, 70 + (roa - 8) * 2)

        pros.append(
            (
                "PRO_06",
                f"ROA of {fmt_pct(roa)} indicates productive use "
                f"of the company's asset base.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 07 - Low debt/equity
    # ---------------------------------------------------------------

    if is_valid(debt_equity) and debt_equity <= 0.5:
        confidence = min(98, 80 + (0.5 - debt_equity) * 30)

        pros.append(
            (
                "PRO_07",
                f"Low debt-to-equity of {fmt_num(debt_equity)} "
                f"indicates a relatively conservative capital structure.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 08 - Strong interest coverage
    # ---------------------------------------------------------------

    if is_valid(interest_coverage) and interest_coverage >= 5:
        confidence = min(98, 75 + min(20, interest_coverage))

        pros.append(
            (
                "PRO_08",
                f"Interest coverage of {fmt_num(interest_coverage)}x "
                f"provides a strong buffer for interest payments.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 09 - High CFO quality
    # ---------------------------------------------------------------

    if is_valid(cfo_quality) and cfo_quality > 1:
        confidence = min(98, 78 + min(20, (cfo_quality - 1) * 10))

        pros.append(
            (
                "PRO_09",
                f"CFO/PAT ratio of {fmt_num(cfo_quality)}x is classified "
                f"as High Quality, indicating strong cash backing for earnings.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 10 - Strong FCF conversion
    # ---------------------------------------------------------------

    if is_valid(fcf_conversion) and fcf_conversion >= 80:
        confidence = min(97, 70 + min(25, (fcf_conversion - 80) * 0.5))

        pros.append(
            (
                "PRO_10",
                f"FCF conversion of {fmt_pct(fcf_conversion)} indicates "
                f"good conversion of operating profit into free cash flow.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # PRO 11 - Reasonable dividend payout
    # ---------------------------------------------------------------

    if (
        is_valid(dividend_payout)
        and dividend_payout >= 10
        and dividend_payout <= 60
    ):
        pros.append(
            (
                "PRO_11",
                f"Dividend payout of {fmt_pct(dividend_payout)} "
                f"shows a balanced approach between shareholder returns "
                f"and retaining earnings.",
                72,
            )
        )

    # ---------------------------------------------------------------
    # PRO 12 - Asset-light model
    # ---------------------------------------------------------------

    if is_valid(capex_intensity) and capex_intensity < 3:
        pros.append(
            (
                "PRO_12",
                f"CapEx intensity of {fmt_pct(capex_intensity)} "
                f"indicates an asset-light business model.",
                75,
            )
        )

    return pros


def generate_cons(row):
    """
    12 Con rules.

    Each rule returns:
        (rule_id, text, confidence)
    """

    cons = []

    revenue_5y = to_float(row.get("revenue_cagr_5yr"))
    profit_5y = to_float(row.get("pat_cagr_5yr"))
    eps_5y = to_float(row.get("eps_cagr_5yr"))

    roe = to_float(row.get("return_on_equity_pct"))
    roce = to_float(row.get("return_on_capital_employed_pct"))

    debt_equity = to_float(row.get("debt_to_equity"))
    interest_coverage = to_float(row.get("interest_coverage"))

    cfo_quality = to_float(row.get("cfo_quality_ratio"))
    fcf = to_float(row.get("free_cash_flow_cr"))

    capex_intensity = to_float(row.get("capex_intensity_pct"))

    high_leverage = to_float(row.get("high_leverage_flag"))

    capital_pattern = str(
        row.get("capital_allocation_pattern") or ""
    ).strip()

    # ---------------------------------------------------------------
    # CON 01 - Weak revenue growth
    # ---------------------------------------------------------------

    if is_valid(revenue_5y) and revenue_5y < 5:
        confidence = min(96, 70 + abs(revenue_5y) * 2)

        cons.append(
            (
                "CON_01",
                f"5-year revenue growth is only {fmt_pct(revenue_5y)}, "
                f"indicating weak business expansion.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 02 - Weak profit growth
    # ---------------------------------------------------------------

    if is_valid(profit_5y) and profit_5y < 5:
        confidence = min(96, 70 + abs(profit_5y) * 2)

        cons.append(
            (
                "CON_02",
                f"5-year profit growth is only {fmt_pct(profit_5y)}, "
                f"showing limited earnings growth.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 03 - Weak EPS growth
    # ---------------------------------------------------------------

    if is_valid(eps_5y) and eps_5y < 5:
        confidence = min(95, 70 + abs(eps_5y) * 2)

        cons.append(
            (
                "CON_03",
                f"5-year EPS growth is only {fmt_pct(eps_5y)}, "
                f"which may limit shareholder earnings growth.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 04 - Low ROE
    # ---------------------------------------------------------------

    if is_valid(roe) and roe < 10:
        confidence = min(95, 72 + abs(10 - roe) * 2)

        cons.append(
            (
                "CON_04",
                f"ROE of {fmt_pct(roe)} is relatively low, "
                f"indicating weaker returns on shareholder capital.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 05 - Low ROCE
    # ---------------------------------------------------------------

    if is_valid(roce) and roce < 10:
        confidence = min(95, 72 + abs(10 - roce) * 2)

        cons.append(
            (
                "CON_05",
                f"ROCE of {fmt_pct(roce)} is relatively low, "
                f"indicating weaker capital efficiency.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 06 - High debt/equity
    # ---------------------------------------------------------------

    if is_valid(debt_equity) and debt_equity > 1:
        confidence = min(98, 75 + min(20, debt_equity * 5))

        cons.append(
            (
                "CON_06",
                f"Debt-to-equity of {fmt_num(debt_equity)} indicates "
                f"higher financial leverage.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 07 - Weak interest coverage
    # ---------------------------------------------------------------

    if is_valid(interest_coverage) and interest_coverage < 2:
        confidence = min(98, 80 + max(0, 2 - interest_coverage) * 8)

        cons.append(
            (
                "CON_07",
                f"Interest coverage of {fmt_num(interest_coverage)}x "
                f"provides a limited buffer for interest payments.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 08 - Accrual risk
    # ---------------------------------------------------------------

    if is_valid(cfo_quality) and cfo_quality < 0.5:
        cons.append(
            (
                "CON_08",
                f"CFO/PAT ratio of {fmt_num(cfo_quality)}x is classified "
                f"as Accrual Risk, suggesting earnings have weaker cash support.",
                88,
            )
        )

    # ---------------------------------------------------------------
    # CON 09 - Negative FCF
    # ---------------------------------------------------------------

    if is_valid(fcf) and fcf < 0:
        cons.append(
            (
                "CON_09",
                f"Free cash flow is negative at {fmt_num(fcf)} crore, "
                f"which can constrain internally generated funding.",
                86,
            )
        )

    # ---------------------------------------------------------------
    # CON 10 - High CapEx intensity
    # ---------------------------------------------------------------

    if is_valid(capex_intensity) and capex_intensity > 8:
        confidence = min(96, 75 + min(20, capex_intensity - 8))

        cons.append(
            (
                "CON_10",
                f"CapEx intensity of {fmt_pct(capex_intensity)} "
                f"indicates a capital-intensive business model.",
                round(confidence),
            )
        )

    # ---------------------------------------------------------------
    # CON 11 - High leverage flag
    # ---------------------------------------------------------------

    if high_leverage == 1:
        cons.append(
            (
                "CON_11",
                "The company is flagged for high leverage, "
                "which increases financial risk.",
                92,
            )
        )

    # ---------------------------------------------------------------
    # CON 12 - Distress / debt-funded pattern
    # ---------------------------------------------------------------

    if capital_pattern in {
        "Distress Signal",
        "Growth Funded by Debt",
    }:
        label = capital_pattern

        cons.append(
            (
                "CON_12",
                f"Capital allocation is classified as '{label}', "
                f"which warrants closer monitoring of cash-flow quality "
                f"and funding requirements.",
                90,
            )
        )

    return cons


# ---------------------------------------------------------------------------
# Fallback rules
# ---------------------------------------------------------------------------

def fallback_pro(row):
    """
    Guarantee at least one Pro for every company.

    The fallback uses the strongest available positive metric.
    """

    candidates = [
        ("ROE", to_float(row.get("return_on_equity_pct"))),
        ("ROCE", to_float(row.get("return_on_capital_employed_pct"))),
        ("Revenue CAGR", to_float(row.get("revenue_cagr_5yr"))),
        ("Profit CAGR", to_float(row.get("pat_cagr_5yr"))),
        ("EPS CAGR", to_float(row.get("eps_cagr_5yr"))),
        ("CFO/PAT", to_float(row.get("cfo_quality_ratio"))),
    ]

    available = [(name, value) for name, value in candidates if is_valid(value)]

    if available:
        name, value = max(available, key=lambda item: item[1])

        return (
            "PRO_12",
            f"{name} provides a measurable financial strength "
            f"with a latest available value of {fmt_num(value)}"
            f"{'%' if name != 'CFO/PAT' else 'x'}.",
            65,
        )

    return (
        "PRO_12",
        "The company has financial data available for fundamental analysis.",
        61,
    )


def fallback_con(row):
    """
    Guarantee at least one Con for every company.

    Uses the weakest available financial metric.
    """

    candidates = [
        ("ROE", to_float(row.get("return_on_equity_pct"))),
        ("ROCE", to_float(row.get("return_on_capital_employed_pct"))),
        ("Revenue CAGR", to_float(row.get("revenue_cagr_5yr"))),
        ("Profit CAGR", to_float(row.get("pat_cagr_5yr"))),
        ("EPS CAGR", to_float(row.get("eps_cagr_5yr"))),
    ]

    available = [(name, value) for name, value in candidates if is_valid(value)]

    if available:
        name, value = min(available, key=lambda item: item[1])

        return (
            "CON_12",
            f"{name} is the weakest among the available core financial "
            f"metrics, at {fmt_num(value)}%. This deserves monitoring.",
            65,
        )

    return (
        "CON_12",
        "Limited financial information is available for generating "
        "stronger rule-based risk signals.",
        61,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("N100 NLP PROS / CONS GENERATOR")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    try:
        query = """
            SELECT *
            FROM financial_ratios
            WHERE company_id IS NOT NULL
        """

        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    print(f"Financial-ratio rows loaded: {len(df):,}")

    latest = latest_rows(df)

    print(f"Latest company rows: {len(latest):,}")

    records = []

    for _, row in latest.iterrows():
        company_id = str(row["company_id"])

        pros = generate_pros(row)
        cons = generate_cons(row)

        # Only confidence > 60 is allowed.
        pros = [
            item for item in pros
            if item[2] > 60
        ]

        cons = [
            item for item in cons
            if item[2] > 60
        ]

        # Requirement: every company gets at least 1 Pro.
        if not pros:
            pros.append(fallback_pro(row))

        # Requirement: every company gets at least 1 Con.
        if not cons:
            cons.append(fallback_con(row))

        for rule_id, text, confidence in pros:
            records.append(
                {
                    "company_id": company_id,
                    "type": "Pro",
                    "rule_id": rule_id,
                    "text": text,
                    "confidence_pct": int(confidence),
                }
            )

        for rule_id, text, confidence in cons:
            records.append(
                {
                    "company_id": company_id,
                    "type": "Con",
                    "rule_id": rule_id,
                    "text": text,
                    "confidence_pct": int(confidence),
                }
            )

    result = pd.DataFrame(
        records,
        columns=[
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ],
    )

    # Final confidence filter.
    result = result[
        result["confidence_pct"] > 60
    ].copy()

    result = result.sort_values(
        ["company_id", "type", "confidence_pct", "rule_id"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)

    result.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    company_count = result["company_id"].nunique()

    pro_companies = set(
        result.loc[result["type"] == "Pro", "company_id"]
    )

    con_companies = set(
        result.loc[result["type"] == "Con", "company_id"]
    )

    all_companies = set(latest["company_id"].astype(str))

    missing_pro = sorted(all_companies - pro_companies)
    missing_con = sorted(all_companies - con_companies)

    print()
    print("OUTPUT VALIDATION")
    print("-" * 70)
    print(f"Output rows:             {len(result):,}")
    print(f"Unique companies:        {company_count}")
    print(f"Pro rows:                {(result['type'] == 'Pro').sum():,}")
    print(f"Con rows:                {(result['type'] == 'Con').sum():,}")
    print(f"Minimum confidence:      {result['confidence_pct'].min()}")
    print(f"Maximum confidence:      {result['confidence_pct'].max()}")
    print(f"Companies missing Pro:   {len(missing_pro)}")
    print(f"Companies missing Con:   {len(missing_con)}")

    print()
    print("Rule distribution:")
    print(result["rule_id"].value_counts().sort_index().to_string())

    if missing_pro:
        print()
        print("ERROR: Companies missing Pro:")
        print(missing_pro)

        raise RuntimeError(
            "Every company must have at least one Pro."
        )

    if missing_con:
        print()
        print("ERROR: Companies missing Con:")
        print(missing_con)

        raise RuntimeError(
            "Every company must have at least one Con."
        )

    if result["confidence_pct"].min() <= 60:
        raise RuntimeError(
            "Confidence filter failed: value <= 60 found."
        )

    print()
    print(f"Saved: {OUTPUT_FILE}")
    print("Day 30 NLP generation completed successfully.")


if __name__ == "__main__":
    main()