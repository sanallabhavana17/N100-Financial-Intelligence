import pandas as pd

from src.analytics.ratios import (
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)


# ==========================================================
# LEVERAGE & EFFICIENCY ANALYSIS
# ==========================================================


# ==========================================================
# 1. LOAD CLEANED FINANCIAL DATA
# ==========================================================

print("\nLoading cleaned financial data...")

pnl = pd.read_csv(
    "data/processed/profitandloss_cleaned.csv"
)

balance = pd.read_csv(
    "data/processed/balancesheet_cleaned.csv"
)

companies = pd.read_excel(
    "data/raw/companies.xlsx",
    header=1
)

sectors = pd.read_excel(
    "data/raw/sectors.xlsx",
    header=None,
    names=[
        "id",
        "company_id",
        "broad_sector",
        "sector",
        "metric",
        "market_cap_category"
    ]
)


print("P&L rows loaded:", len(pnl))
print("Balance Sheet rows loaded:", len(balance))


# ==========================================================
# 2. NORMALIZE IDENTIFIERS
# ==========================================================

def normalize_company_id(value):
    if pd.isna(value):
        return None

    return str(value).strip().upper()


def normalize_year(value):
    """
    Convert year values such as:

        2012
        2012.0
        Mar 2012
        Dec 2012

    into integer year values.
    """

    if pd.isna(value):
        return None

    text = str(value).strip()

    # Direct numeric year
    try:
        number = float(text)

        if 1900 <= number <= 2100:
            return int(number)
    except (ValueError, TypeError):
        pass

    # Extract four-digit year
    import re

    match = re.search(
        r"(19|20)\d{2}",
        text
    )

    if match:
        return int(match.group())

    return None


pnl["company_id"] = (
    pnl["company_id"]
    .apply(normalize_company_id)
)

balance["company_id"] = (
    balance["company_id"]
    .apply(normalize_company_id)
)

companies["id"] = (
    companies["id"]
    .apply(normalize_company_id)
)

sectors["company_id"] = (
    sectors["company_id"]
    .apply(normalize_company_id)
)

pnl["year"] = (
    pnl["year"]
    .apply(normalize_year)
)

balance["year"] = (
    balance["year"]
    .apply(normalize_year)
)


# Remove unusable company-year rows
pnl = pnl.dropna(
    subset=["company_id", "year"]
).copy()

balance = balance.dropna(
    subset=["company_id", "year"]
).copy()

pnl["year"] = pnl["year"].astype(int)
balance["year"] = balance["year"].astype(int)


# ==========================================================
# 3. KEEP REQUIRED P&L COLUMNS
# ==========================================================

pnl = pnl[
    [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "other_income",
        "interest",
        "net_profit",
    ]
].copy()


# ==========================================================
# 4. KEEP REQUIRED BALANCE SHEET COLUMNS
# ==========================================================

balance = balance[
    [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "investments",
        "total_assets",
    ]
].copy()


# ==========================================================
# 5. KEEP OFFICIAL N100 COMPANIES
# ==========================================================

valid_companies = set(
    companies["id"].dropna()
)

print(
    "Official N100 companies:",
    len(valid_companies)
)


pnl = pnl[
    pnl["company_id"].isin(valid_companies)
].copy()

balance = balance[
    balance["company_id"].isin(valid_companies)
].copy()


print("\nAfter official-company filtering:")

print(
    "P&L rows:",
    len(pnl)
)

print(
    "Balance Sheet rows:",
    len(balance)
)

print(
    "P&L companies:",
    pnl["company_id"].nunique()
)

print(
    "Balance Sheet companies:",
    balance["company_id"].nunique()
)


# ==========================================================
# 6. VERIFY COMPANY-YEAR UNIQUENESS
# ==========================================================

pnl_duplicates = pnl.duplicated(
    subset=["company_id", "year"]
).sum()

balance_duplicates = balance.duplicated(
    subset=["company_id", "year"]
).sum()


print(
    "\nP&L company-year duplicates:",
    pnl_duplicates
)

print(
    "Balance Sheet company-year duplicates:",
    balance_duplicates
)


if pnl_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found "
        "in cleaned P&L data."
    )


if balance_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found "
        "in cleaned Balance Sheet data."
    )


# ==========================================================
# 7. MERGE P&L + BALANCE SHEET
# ==========================================================

df = pd.merge(
    pnl,
    balance,
    on=["company_id", "year"],
    how="inner",
    validate="one_to_one"
)


print(
    "\nRows after P&L + Balance Sheet merge:",
    len(df)
)

print(
    "Companies after merge:",
    df["company_id"].nunique()
)


# ==========================================================
# 8. VERIFY MERGED UNIQUENESS
# ==========================================================

merged_duplicates = df.duplicated(
    subset=["company_id", "year"]
).sum()


print(
    "Merged company-year duplicates:",
    merged_duplicates
)


if merged_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found "
        "after P&L + Balance Sheet merge."
    )


# ==========================================================
# 9. PREPARE SECTOR DATA
# ==========================================================

sectors = sectors[
    [
        "company_id",
        "broad_sector",
        "sector"
    ]
].copy()


# One sector record per company
sectors = sectors.drop_duplicates(
    subset=["company_id"]
)


print(
    "Unique sector companies:",
    sectors["company_id"].nunique()
)


# ==========================================================
# 10. MERGE SECTOR INFORMATION
# ==========================================================

df = df.merge(
    sectors,
    on="company_id",
    how="left",
    validate="many_to_one"
)


print(
    "Rows after sector merge:",
    len(df)
)

print(
    "Companies with sector information:",
    df["broad_sector"].notna().sum()
)

print(
    "Companies without sector information:",
    df["broad_sector"].isna().sum()
)


# ==========================================================
# 11. FINANCIALS SECTOR FLAG
# ==========================================================

df["is_financials_sector"] = (
    df["broad_sector"]
    .astype(str)
    .str.strip()
    .eq("Financials")
)


print(
    "Financials company-year rows:",
    df["is_financials_sector"].sum()
)

print(
    "Financials companies:",
    df.loc[
        df["is_financials_sector"],
        "company_id"
    ].nunique()
)


# ==========================================================
# 12. DEBT-TO-EQUITY
# ==========================================================

df["debt_to_equity"] = df.apply(
    lambda row: debt_to_equity(
        row["borrowings"],
        row["equity_capital"],
        row["reserves"]
    ),
    axis=1
)


# ==========================================================
# 13. HIGH LEVERAGE FLAG
# ==========================================================

df["high_leverage_flag"] = df.apply(
    lambda row: high_leverage_flag(
        row["debt_to_equity"],
        row["is_financials_sector"]
    ),
    axis=1
)


# ==========================================================
# 14. INTEREST COVERAGE RATIO
# ==========================================================

df["interest_coverage"] = df.apply(
    lambda row: interest_coverage_ratio(
        row["operating_profit"],
        row["other_income"],
        row["interest"]
    ),
    axis=1
)


# ==========================================================
# 15. ICR LABEL
# ==========================================================
#
# IMPORTANT:
# Use the project function from ratios.py.
#
# If ICR is None because interest expense = 0,
# the company is labelled "Debt Free".
#

df["icr_label"] = df["interest_coverage"].apply(
    icr_label
)


# ==========================================================
# 16. ICR WARNING FLAG
# ==========================================================

df["icr_warning_flag"] = df["interest_coverage"].apply(
    icr_warning_flag
)


# ==========================================================
# 17. NET DEBT
# ==========================================================

df["net_debt_cr"] = df.apply(
    lambda row: net_debt(
        row["borrowings"],
        row["investments"]
    ),
    axis=1
)


# ==========================================================
# 18. ASSET TURNOVER
# ==========================================================

df["asset_turnover"] = df.apply(
    lambda row: asset_turnover(
        row["sales"],
        row["total_assets"]
    ),
    axis=1
)


# ==========================================================
# 19. FINAL VALIDATION
# ==========================================================

print("\n========================================")
print("LEVERAGE & EFFICIENCY VALIDATION")
print("========================================")


print(
    "Total companies:",
    df["company_id"].nunique()
)

print(
    "Total company-year rows:",
    len(df)
)

print(
    "Company-year duplicates:",
    df.duplicated(
        ["company_id", "year"]
    ).sum()
)

print(
    "Expected official companies:",
    len(valid_companies)
)


# Missing official companies
output_companies = set(
    df["company_id"].dropna()
)

missing_companies = sorted(
    valid_companies - output_companies
)

print(
    "\nMissing official companies:",
    missing_companies
)

print(
    "Missing company count:",
    len(missing_companies)
)


# ==========================================================
# 20. BASIC RATIO CHECKS
# ==========================================================

print("\nBasic checks:")


print(
    "Debt-free company-years:",
    (df["debt_to_equity"] == 0).sum()
)


print(
    "High leverage flags:",
    df["high_leverage_flag"].sum()
)


print(
    "Debt-free ICR labels:",
    (df["icr_label"] == "Debt Free").sum()
)


print(
    "ICR warning flags:",
    df["icr_warning_flag"].sum()
)


print(
    "Null ICR:",
    df["interest_coverage"].isna().sum()
)


print(
    "Null Asset Turnover:",
    df["asset_turnover"].isna().sum()
)


# ==========================================================
# 21. SAMPLE RESULTS
# ==========================================================

print("\nSample results:")

print(
    df[
        [
            "company_id",
            "year",
            "broad_sector",
            "debt_to_equity",
            "high_leverage_flag",
            "interest_coverage",
            "icr_label",
            "icr_warning_flag",
            "net_debt_cr",
            "asset_turnover",
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ==========================================================
# 22. FINAL OUTPUT UNIQUENESS CHECK
# ==========================================================

final_duplicates = df.duplicated(
    subset=["company_id", "year"]
).sum()


if final_duplicates > 0:
    raise ValueError(
        "Final leverage output contains "
        "duplicate company-year records."
    )


# ==========================================================
# 23. SAVE OUTPUT
# ==========================================================

output_path = (
    "output/leverage_efficiency_ratios.csv"
)

df.to_csv(
    output_path,
    index=False
)


print("\nSaved:")
print(output_path)


# ==========================================================
# 24. COMPLETION MESSAGE
# ==========================================================

print("\n========================================")
print("LEVERAGE ANALYSIS COMPLETED")
print("========================================")