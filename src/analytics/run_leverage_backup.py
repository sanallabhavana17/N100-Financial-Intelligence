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
# 1. LOAD DATA
# ==========================================================

pnl = pd.read_excel(
    "data/raw/profitandloss.xlsx",
    header=1
)

balance = pd.read_excel(
    "data/raw/balancesheet.xlsx",
    header=1
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


# ==========================================================
# 2. KEEP REQUIRED P&L COLUMNS
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
]


# ==========================================================
# 3. KEEP REQUIRED BALANCE SHEET COLUMNS
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
]


# ==========================================================
# 4. KEEP ONLY OFFICIAL N100 COMPANIES
# ==========================================================

valid_companies = set(
    companies["id"].dropna()
)

pnl = pnl[
    pnl["company_id"].isin(valid_companies)
].copy()

balance = balance[
    balance["company_id"].isin(valid_companies)
].copy()


# ==========================================================
# 5. MERGE P&L + BALANCE SHEET
# ==========================================================

df = pd.merge(
    pnl,
    balance,
    on=["company_id", "year"],
    how="inner"
)


# ==========================================================
# 6. ADD SECTOR INFORMATION
# ==========================================================

sectors = sectors[
    [
        "company_id",
        "broad_sector",
        "sector"
    ]
].drop_duplicates(
    subset=["company_id"]
)

df = df.merge(
    sectors,
    on="company_id",
    how="left"
)


# ==========================================================
# 7. FINANCIALS SECTOR FLAG
# ==========================================================

df["is_financials_sector"] = (
    df["broad_sector"] == "Financials"
)


print("Rows after merging:", len(df))

print(
    "Companies:",
    df["company_id"].nunique()
)

print(
    "Financials company-year rows:",
    df["is_financials_sector"].sum()
)


# ==========================================================
# 8. DEBT-TO-EQUITY
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
# 9. HIGH LEVERAGE FLAG
# ==========================================================

df["high_leverage_flag"] = df.apply(
    lambda row: high_leverage_flag(
        row["debt_to_equity"],
        row["is_financials_sector"]
    ),
    axis=1
)


# ==========================================================
# 10. INTEREST COVERAGE RATIO
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
# 11. ICR LABEL
# ==========================================================

# ==========================================================
# 11. ICR LABEL
# ==========================================================

df["icr_label"] = df["interest_coverage"].apply(
    lambda x: "Debt Free" if pd.isna(x) else None
)


# ==========================================================
# 12. ICR WARNING FLAG
# ==========================================================

df["icr_warning_flag"] = df["interest_coverage"].apply(
    icr_warning_flag
)


# ==========================================================
# 13. NET DEBT
# ==========================================================

df["net_debt_cr"] = df.apply(
    lambda row: net_debt(
        row["borrowings"],
        row["investments"]
    ),
    axis=1
)


# ==========================================================
# 14. ASSET TURNOVER
# ==========================================================

df["asset_turnover"] = df.apply(
    lambda row: asset_turnover(
        row["sales"],
        row["total_assets"]
    ),
    axis=1
)


# ==========================================================
# 15. DISPLAY SAMPLE
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
# 16. BASIC CHECKS
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
# 17. SAVE OUTPUT
# ==========================================================

df.to_csv(
    "output/leverage_efficiency_ratios.csv",
    index=False
)

print("\nSaved:")
print("output/leverage_efficiency_ratios.csv")