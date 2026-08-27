import sqlite3
from pathlib import Path

import pandas as pd


DB_PATH = Path("data/nifty100.db")

PROFITABILITY_FILE = Path("output/profitability_ratios.csv")
LEVERAGE_FILE = Path("output/leverage_efficiency_ratios.csv")
CAGR_FILE = Path("output/cagr_ratios.csv")
CASHFLOW_FILE = Path("output/cashflow_kpis.csv")


def load_csv(path):
    print(f"Loading {path}...")
    df = pd.read_csv(path)

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["company_id", "year"]
    ).copy()

    df["year"] = df["year"].astype(int)

    df = df.drop_duplicates(
        ["company_id", "year"],
        keep="first"
    )

    print(
        f"  rows={len(df)}, "
        f"companies={df['company_id'].nunique()}"
    )

    return df


def main():

    print("\n========================================")
    print("POPULATE FINANCIAL RATIOS")
    print("========================================")

    # ---------------------------------------------------------
    # 1. Load calculated outputs
    # ---------------------------------------------------------

    profitability = load_csv(PROFITABILITY_FILE)
    leverage = load_csv(LEVERAGE_FILE)
    cagr = load_csv(CAGR_FILE)
    cashflow = load_csv(CASHFLOW_FILE)

    # ---------------------------------------------------------
    # 2. Select required columns
    # ---------------------------------------------------------

    profitability = profitability[
        [
            "company_id",
            "year",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "roe_pct",
            "roce_pct",
            "roa_pct",
        ]
    ].rename(
        columns={
            "roe_pct": "return_on_equity_pct",
            "roce_pct": "return_on_capital_employed_pct",
            "roa_pct": "return_on_assets_pct",
        }
    )

    leverage = leverage[
        [
            "company_id",
            "year",
            "debt_to_equity",
            "high_leverage_flag",
            "interest_coverage",
            "icr_label",
            "icr_warning_flag",
            "net_debt_cr",
            "asset_turnover",
            "borrowings",
        ]
    ].rename(
        columns={
            "borrowings": "total_debt_cr",
        }
    )

    cashflow = cashflow[
        [
            "company_id",
            "year",
            "free_cash_flow",
            "cfo_quality_ratio",
            "cfo_quality_label",
            "capex_intensity_pct",
            "capex_intensity_label",
            "fcf_conversion_pct",
            "capital_allocation_pattern",
            "cfo",
        ]
    ].rename(
        columns={
            "free_cash_flow": "free_cash_flow_cr",
            "cfo": "cash_from_operations_cr",
        }
    )

    cagr = cagr[
        [
            "company_id",
            "year",

            "revenue_cagr_3yr",
            "revenue_cagr_3yr_flag",
            "revenue_cagr_5yr",
            "revenue_cagr_5yr_flag",
            "revenue_cagr_10yr",
            "revenue_cagr_10yr_flag",

            "pat_cagr_3yr",
            "pat_cagr_3yr_flag",
            "pat_cagr_5yr",
            "pat_cagr_5yr_flag",
            "pat_cagr_10yr",
            "pat_cagr_10yr_flag",

            "eps_cagr_3yr",
            "eps_cagr_3yr_flag",
            "eps_cagr_5yr",
            "eps_cagr_5yr_flag",
            "eps_cagr_10yr",
            "eps_cagr_10yr_flag",
        ]
    ]

    # ---------------------------------------------------------
    # 3. Merge all calculated KPI outputs
    # ---------------------------------------------------------

    print("\nMerging calculated KPI outputs...")

    result = profitability.merge(
        leverage,
        on=["company_id", "year"],
        how="outer",
    )

    result = result.merge(
        cashflow,
        on=["company_id", "year"],
        how="outer",
    )

    result = result.merge(
        cagr,
        on=["company_id", "year"],
        how="outer",
    )

    result = result.drop_duplicates(
        ["company_id", "year"],
        keep="first"
    )

    print("Final merged rows:", len(result))
    print(
        "Final companies:",
        result["company_id"].nunique()
    )

    print(
        "Company-year duplicates:",
        result.duplicated(
            ["company_id", "year"]
        ).sum()
    )

    # ---------------------------------------------------------
    # 4. Add source per-share metrics from P&L / companies
    # ---------------------------------------------------------

    print("\nLoading source data for additional KPIs...")

    pnl = pd.read_csv(
        "data/processed/profitandloss_cleaned.csv"
    )

    pnl["company_id"] = (
        pnl["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    pnl["year"] = pd.to_numeric(
        pnl["year"],
        errors="coerce"
    )

    pnl = pnl.dropna(
        subset=["company_id", "year"]
    )

    pnl["year"] = pnl["year"].astype(int)

    pnl = pnl.drop_duplicates(
        ["company_id", "year"],
        keep="first"
    )

    pnl_extra = pnl[
        [
            "company_id",
            "year",
            "eps",
            "dividend_payout",
        ]
    ].rename(
        columns={
            "eps": "earnings_per_share",
            "dividend_payout":
                "dividend_payout_ratio_pct",
        }
    )

    result = result.merge(
        pnl_extra,
        on=["company_id", "year"],
        how="left",
    )

    # ---------------------------------------------------------
    # 5. Book value per share
    # ---------------------------------------------------------

    companies = pd.read_excel(
        "data/raw/companies.xlsx"
    )

    companies.columns = [
        str(c).strip().lower()
        for c in companies.columns
    ]

    companies["id"] = (
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    book_values = companies[
        [
            "id",
            "book_value",
        ]
    ].rename(
        columns={
            "id": "company_id",
            "book_value": "book_value_per_share",
        }
    )

    result = result.merge(
        book_values,
        on="company_id",
        how="left",
    )

    # ---------------------------------------------------------
    # 6. CapEx
    # ---------------------------------------------------------

    result["capex_cr"] = (
        result["capex_intensity_pct"]
    )

    # We keep capex_intensity separately.
    # Actual CapEx will be calculated from cash-flow data
    # below where possible.

    cf = pd.read_csv(
        "data/processed/cashflow_cleaned.csv"
    )

    cf["company_id"] = (
        cf["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    cf["year"] = pd.to_numeric(
        cf["year"],
        errors="coerce"
    )

    cf = cf.dropna(
        subset=["company_id", "year"]
    )

    cf["year"] = cf["year"].astype(int)

    cf = cf.drop_duplicates(
        ["company_id", "year"],
        keep="first"
    )

    # Investing activity is used as CapEx proxy
    cf_capex = cf[
        [
            "company_id",
            "year",
            "investing_activity",
        ]
    ].rename(
        columns={
            "investing_activity": "capex_cr_source"
        }
    )

    result = result.merge(
        cf_capex,
        on=["company_id", "year"],
        how="left",
    )

    result["capex_cr"] = (
        result["capex_cr_source"].abs()
    )

    result = result.drop(
        columns=["capex_cr_source"],
        errors="ignore"
    )

    # ---------------------------------------------------------
    # 7. Composite quality score
    # ---------------------------------------------------------

    result["composite_quality_score"] = (
        result[
            [
                "return_on_equity_pct",
                "debt_to_equity",
                "asset_turnover",
                "revenue_cagr_5yr",
                "pat_cagr_5yr",
            ]
        ]
        .rank(pct=True)
        .mean(axis=1)
        * 100
    )

    # ---------------------------------------------------------
    # 8. Select final database columns
    # ---------------------------------------------------------

    final_columns = [
        "company_id",
        "year",

        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "return_on_assets_pct",

        "debt_to_equity",
        "high_leverage_flag",
        "interest_coverage",
        "icr_label",
        "icr_warning_flag",
        "net_debt_cr",
        "asset_turnover",

        "free_cash_flow_cr",
        "capex_cr",
        "cash_from_operations_cr",
        "cfo_quality_ratio",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_intensity_label",
        "fcf_conversion_pct",
        "capital_allocation_pattern",

        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",

        "revenue_cagr_3yr",
        "revenue_cagr_3yr_flag",
        "revenue_cagr_5yr",
        "revenue_cagr_5yr_flag",
        "revenue_cagr_10yr",
        "revenue_cagr_10yr_flag",

        "pat_cagr_3yr",
        "pat_cagr_3yr_flag",
        "pat_cagr_5yr",
        "pat_cagr_5yr_flag",
        "pat_cagr_10yr",
        "pat_cagr_10yr_flag",

        "eps_cagr_3yr",
        "eps_cagr_3yr_flag",
        "eps_cagr_5yr",
        "eps_cagr_5yr_flag",
        "eps_cagr_10yr",
        "eps_cagr_10yr_flag",

        "composite_quality_score",
    ]

    result = result[
        final_columns
    ]

    # ---------------------------------------------------------
    # 9. Save combined output
    # ---------------------------------------------------------

    output_path = Path(
        "output/final_financial_ratios.csv"
    )

    result.to_csv(
        output_path,
        index=False
    )

    print(
        f"\nSaved combined ratios to: "
        f"{output_path}"
    )

    # ---------------------------------------------------------
    # 10. Database update
    # ---------------------------------------------------------

    print("\nUpdating SQLite database...")

    conn = sqlite3.connect(DB_PATH)

    # Clear old source ratios
    conn.execute(
        "DELETE FROM financial_ratios"
    )

    # Insert calculated ratios
    result.to_sql(
        "financial_ratios",
        conn,
        if_exists="append",
        index=False,
    )

    conn.commit()

    # ---------------------------------------------------------
    # 11. Final validation
    # ---------------------------------------------------------

    count = conn.execute(
        "SELECT COUNT(*) FROM financial_ratios"
    ).fetchone()[0]

    companies_count = conn.execute(
        "SELECT COUNT(DISTINCT company_id) "
        "FROM financial_ratios"
    ).fetchone()[0]

    duplicates = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT company_id, year
            FROM financial_ratios
            GROUP BY company_id, year
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    print("\n========================================")
    print("FINAL DATABASE VALIDATION")
    print("========================================")

    print("financial_ratios rows:", count)
    print("companies:", companies_count)
    print("duplicate company-year groups:", duplicates)

    conn.close()

    print("\n========================================")
    print("FINANCIAL RATIOS POPULATION COMPLETED")
    print("========================================")


if __name__ == "__main__":
    main()