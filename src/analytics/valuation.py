from pathlib import Path

import numpy as np
import pandas as pd

from src.dashboard.data_loader import load_db


OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def build_valuation_summary():
    query = """
    SELECT
        m.company_id,
        c.company_name,
        s.broad_sector,
        m.year,
        m.market_cap_crore,
        m.enterprise_value_crore,
        m.pe_ratio,
        m.pb_ratio,
        m.ev_ebitda,
        m.dividend_yield_pct,
        r.free_cash_flow_cr
    FROM market_cap m
    LEFT JOIN companies c
        ON m.company_id = c.id
    LEFT JOIN sectors s
        ON m.company_id = s.company_id
    LEFT JOIN financial_ratios r
        ON m.company_id = r.company_id
        AND m.year = r.year
    ORDER BY m.company_id, m.year
    """

    df = load_db(query)

    if df.empty:
        raise ValueError("No valuation data found.")

    numeric_columns = [
        "year",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "free_cash_flow_cr",
    ]

    for column in numeric_columns:
        df[column] = safe_numeric(df[column])

    # ---------------------------------------------------------
    # Remove invalid valuation multiples
    # ---------------------------------------------------------

    for column in ["pe_ratio", "pb_ratio", "ev_ebitda"]:
        df.loc[df[column] <= 0, column] = np.nan

    # ---------------------------------------------------------
    # Current/latest valuation observation per company
    # ---------------------------------------------------------

    current = (
        df.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    current = current.rename(
        columns={
            "year": "current_year",
            "pe_ratio": "current_pe",
            "pb_ratio": "current_pb",
            "ev_ebitda": "current_ev_ebitda",
            "market_cap_crore": "current_market_cap_crore",
            "enterprise_value_crore": "current_enterprise_value_crore",
            "dividend_yield_pct": "current_dividend_yield_pct",
            "free_cash_flow_cr": "current_fcf_cr",
        }
    )

    # ---------------------------------------------------------
    # Five-year historical medians
    # ---------------------------------------------------------

    five_year_rows = []

    for company_id, company_df in df.groupby("company_id"):
        company_df = company_df.sort_values("year")

        recent = company_df.tail(5)

        row = {
            "company_id": company_id,
            "pe_5yr_median": recent["pe_ratio"].median(),
            "pb_5yr_median": recent["pb_ratio"].median(),
            "ev_ebitda_5yr_median": recent["ev_ebitda"].median(),
        }

        five_year_rows.append(row)

    historical = pd.DataFrame(five_year_rows)

    result = current.merge(
        historical,
        on="company_id",
        how="left",
    )

    # ---------------------------------------------------------
    # Sector medians
    # ---------------------------------------------------------

    sector_current = (
        df.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    sector_medians = (
        sector_current
        .groupby("broad_sector", dropna=False)
        .agg(
            sector_median_pe=("pe_ratio", "median"),
            sector_median_pb=("pb_ratio", "median"),
            sector_median_ev_ebitda=("ev_ebitda", "median"),
        )
        .reset_index()
    )

    result = result.merge(
        sector_medians,
        on="broad_sector",
        how="left",
    )

    # ---------------------------------------------------------
    # Sector P/E rank
    # ---------------------------------------------------------

    result["sector_pe_rank"] = (
        result.groupby("broad_sector")["current_pe"]
        .rank(
            method="min",
            ascending=True,
            na_option="bottom",
        )
    )

    result["sector_company_count"] = (
        result.groupby("broad_sector")["company_id"]
        .transform("count")
    )

    # ---------------------------------------------------------
    # P/E valuation flag
    # ---------------------------------------------------------

    result["pe_valuation_flag"] = "Neutral"

    caution_mask = (
        result["current_pe"].notna()
        & result["sector_median_pe"].notna()
        & (
            result["current_pe"]
            > result["sector_median_pe"] * 1.5
        )
    )

    discount_mask = (
        result["current_pe"].notna()
        & result["sector_median_pe"].notna()
        & (
            result["current_pe"]
            < result["sector_median_pe"] * 0.7
        )
    )

    result.loc[caution_mask, "pe_valuation_flag"] = "Caution"
    result.loc[discount_mask, "pe_valuation_flag"] = "Discount"

    # ---------------------------------------------------------
    # Historical P/E comparison
    # ---------------------------------------------------------

    result["pe_vs_5yr_median_pct"] = (
        (
            result["current_pe"]
            / result["pe_5yr_median"]
        ) - 1
    ) * 100

    result["pb_vs_5yr_median_pct"] = (
        (
            result["current_pb"]
            / result["pb_5yr_median"]
        ) - 1
    ) * 100

    result["ev_ebitda_vs_5yr_median_pct"] = (
        (
            result["current_ev_ebitda"]
            / result["ev_ebitda_5yr_median"]
        ) - 1
    ) * 100

    # ---------------------------------------------------------
    # EV/EBITDA sector flag
    # ---------------------------------------------------------

    result["ev_ebitda_flag"] = "Normal"

    ev_caution_mask = (
        result["current_ev_ebitda"].notna()
        & result["sector_median_ev_ebitda"].notna()
        & (
            result["current_ev_ebitda"]
            > result["sector_median_ev_ebitda"] * 1.20
        )
    )

    result.loc[
        ev_caution_mask,
        "ev_ebitda_flag",
    ] = "Above Sector +20%"

    # ---------------------------------------------------------
    # FCF Yield
    # Definition:
    # FCF / Market Cap * 100
    # ---------------------------------------------------------

    result["fcf_yield_pct"] = np.where(
        (result["current_market_cap_crore"] > 0)
        & result["current_fcf_cr"].notna(),
        (
            result["current_fcf_cr"]
            / result["current_market_cap_crore"]
        ) * 100,
        np.nan,
    )

    # ---------------------------------------------------------
    # Dividend Yield Rank
    # Higher dividend yield = better rank
    # ---------------------------------------------------------

    result["dividend_yield_rank"] = (
        result["current_dividend_yield_pct"]
        .rank(
            method="min",
            ascending=False,
            na_option="bottom",
        )
    )

    # ---------------------------------------------------------
    # Overall valuation badge
    # ---------------------------------------------------------

    result["valuation_badge"] = "Neutral"

    result.loc[
        result["pe_valuation_flag"] == "Caution",
        "valuation_badge",
    ] = "Caution"

    result.loc[
        result["pe_valuation_flag"] == "Discount",
        "valuation_badge",
    ] = "Discount"

    # If EV/EBITDA is significantly above sector,
    # mark as Caution unless already Discount.
    result.loc[
        (
            result["ev_ebitda_flag"] == "Above Sector +20%"
        )
        & (
            result["valuation_badge"] != "Discount"
        ),
        "valuation_badge",
    ] = "Caution"

    # ---------------------------------------------------------
    # Rationale
    # ---------------------------------------------------------

    def make_rationale(row):
        reasons = []

        if row["pe_valuation_flag"] == "Caution":
            reasons.append(
                "P/E is above 1.5x sector median"
            )

        elif row["pe_valuation_flag"] == "Discount":
            reasons.append(
                "P/E is below 0.7x sector median"
            )

        if row["ev_ebitda_flag"] == "Above Sector +20%":
            reasons.append(
                "EV/EBITDA is more than 20% above sector median"
            )

        if not reasons:
            return "No valuation threshold breached"

        return "; ".join(reasons)

    result["valuation_rationale"] = result.apply(
        make_rationale,
        axis=1,
    )

    # ---------------------------------------------------------
    # Final columns
    # ---------------------------------------------------------

    columns = [
        "company_id",
        "company_name",
        "broad_sector",
        "current_year",
        "current_market_cap_crore",
        "current_enterprise_value_crore",
        "current_pe",
        "pe_5yr_median",
        "pe_vs_5yr_median_pct",
        "sector_median_pe",
        "sector_pe_rank",
        "sector_company_count",
        "current_pb",
        "pb_5yr_median",
        "pb_vs_5yr_median_pct",
        "sector_median_pb",
        "current_ev_ebitda",
        "ev_ebitda_5yr_median",
        "ev_ebitda_vs_5yr_median_pct",
        "sector_median_ev_ebitda",
        "ev_ebitda_flag",
        "current_fcf_cr",
        "fcf_yield_pct",
        "current_dividend_yield_pct",
        "dividend_yield_rank",
        "pe_valuation_flag",
        "valuation_badge",
        "valuation_rationale",
    ]

    result = result[columns].sort_values(
        ["valuation_badge", "company_name"],
        ascending=[True, True],
    )

    return result


def main():
    result = build_valuation_summary()

    xlsx_path = OUTPUT_DIR / "valuation_summary.xlsx"
    flags_path = OUTPUT_DIR / "valuation_flags.csv"

    result.to_excel(
        xlsx_path,
        index=False,
    )

    flags = result[
        result["valuation_badge"].isin(
            ["Caution", "Discount"]
        )
    ].copy()

    flags.to_csv(
        flags_path,
        index=False,
    )

    print("VALUATION SUMMARY")
    print("=" * 60)
    print(f"Companies: {len(result)}")
    print(f"Summary:   {xlsx_path}")
    print(f"Flags:     {flags_path}")
    print()
    print("BADGES:")
    print(
        result["valuation_badge"]
        .value_counts()
        .to_string()
    )
    print()
    print("FLAGGED COMPANIES:")
    print(
        flags[
            [
                "company_id",
                "company_name",
                "valuation_badge",
                "valuation_rationale",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
