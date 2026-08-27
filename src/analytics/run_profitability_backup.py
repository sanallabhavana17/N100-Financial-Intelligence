import pandas as pd

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

PNL_FILE = "data/processed/profitandloss_cleaned.csv"
BALANCE_FILE = "data/processed/balancesheet_cleaned.csv"
COMPANIES_FILE = "data/raw/companies.xlsx"
SECTORS_FILE = "data/raw/sectors.xlsx"

OUTPUT_FILE = "output/profitability_ratios.csv"
OPM_ANOMALIES_FILE = "output/opm_anomalies.csv"


# ==========================================================
# 1. LOAD CLEANED DATA
# ==========================================================

print("\nLoading cleaned financial data...")

pnl = pd.read_csv(PNL_FILE)
balance = pd.read_csv(BALANCE_FILE)

print("P&L rows:", len(pnl))
print("Balance Sheet rows:", len(balance))


# ==========================================================
# 2. NORMALIZE COMPANY ID AND YEAR
# ==========================================================

for df in [pnl, balance]:

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["year"] = (
        df["year"]
        .astype(str)
        .str.strip()
    )


# ==========================================================
# 3. NORMALIZE YEAR
# ==========================================================
#
# Examples:
#     "Mar 2013" -> 2013
#     "Dec 2012" -> 2012
#     2024      -> 2024
#
# This prevents year-format inconsistencies.
# ==========================================================

def normalize_year(value):

    if pd.isna(value):
        return None

    value = str(value).strip()

    # Extract four-digit year
    import re

    match = re.search(r"(19|20)\d{2}", value)

    if match:
        return int(match.group())

    return None


pnl["year"] = pnl["year"].apply(normalize_year)
balance["year"] = balance["year"].apply(normalize_year)


# Remove invalid company-year records

pnl = pnl.dropna(
    subset=["company_id", "year"]
).copy()

balance = balance.dropna(
    subset=["company_id", "year"]
).copy()


pnl["year"] = pnl["year"].astype(int)
balance["year"] = balance["year"].astype(int)


# ==========================================================
# 4. VERIFY CLEANED FINANCIAL DATA
# ==========================================================

pnl_duplicates = pnl.duplicated(
    ["company_id", "year"]
).sum()

balance_duplicates = balance.duplicated(
    ["company_id", "year"]
).sum()


print("\nFinancial data validation:")
print("P&L company-year duplicates:", pnl_duplicates)
print("Balance Sheet company-year duplicates:", balance_duplicates)


if pnl_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found in cleaned P&L."
    )


if balance_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found in cleaned Balance Sheet."
    )


# ==========================================================
# 5. KEEP REQUIRED P&L COLUMNS
# ==========================================================

pnl = pnl[
    [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "net_profit",
    ]
].copy()


# ==========================================================
# 6. KEEP REQUIRED BALANCE SHEET COLUMNS
# ==========================================================

balance = balance[
    [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "total_assets",
    ]
].copy()


# ==========================================================
# 7. LOAD OFFICIAL N100 COMPANIES
# ==========================================================

companies = pd.read_excel(
    COMPANIES_FILE,
    header=1
)


companies["id"] = (
    companies["id"]
    .astype(str)
    .str.strip()
    .str.upper()
)


valid_companies = set(
    companies["id"].dropna()
)


print("\nOfficial N100 companies:", len(valid_companies))


# ==========================================================
# 8. FILTER P&L AND BALANCE TO OFFICIAL COMPANIES
# ==========================================================

pnl = pnl[
    pnl["company_id"].isin(valid_companies)
].copy()

balance = balance[
    balance["company_id"].isin(valid_companies)
].copy()


print("Official companies in P&L:", pnl["company_id"].nunique())
print("Official companies in Balance Sheet:", balance["company_id"].nunique())


# ==========================================================
# 9. MERGE P&L + BALANCE SHEET
# ==========================================================

df = pd.merge(
    pnl,
    balance,
    on=["company_id", "year"],
    how="inner",
    validate="one_to_one"
)


print("\nRows after P&L + Balance Sheet merge:", len(df))
print(
    "Companies after P&L + Balance Sheet merge:",
    df["company_id"].nunique()
)


# ==========================================================
# 10. VERIFY NO DUPLICATES AFTER FINANCIAL MERGE
# ==========================================================

duplicates_after_financial_merge = df.duplicated(
    ["company_id", "year"]
).sum()


print(
    "Company-year duplicates after financial merge:",
    duplicates_after_financial_merge
)


if duplicates_after_financial_merge > 0:
    raise ValueError(
        "Duplicate company-year records found after "
        "P&L + Balance Sheet merge."
    )


# ==========================================================
# 11. LOAD SECTOR DATA
# ==========================================================
#
# sectors.xlsx does not contain a reliable header row.
# Therefore the column names are assigned manually.
# ==========================================================

sectors = pd.read_excel(
    SECTORS_FILE,
    header=None,
    names=[
        "id",
        "company_id",
        "broad_sector",
        "sector",
        "some_metric",
        "market_cap_category",
    ]
)


# ==========================================================
# 12. NORMALIZE SECTOR COMPANY IDS
# ==========================================================

sectors["company_id"] = (
    sectors["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# ==========================================================
# 13. KEEP ONLY REQUIRED SECTOR COLUMNS
# ==========================================================

sectors = sectors[
    [
        "company_id",
        "broad_sector",
        "sector",
    ]
].copy()


# ==========================================================
# 14. REMOVE DUPLICATE SECTOR RECORDS
# ==========================================================
#
# IMPORTANT:
# A company must have only ONE sector record.
#
# Without this step:
#
# Financial row
#       +
# multiple sector rows
#       =
# duplicate company-year rows
#
# This was the source of your 96 duplicates.
# ==========================================================

sector_duplicates = sectors.duplicated(
    subset=["company_id"]
).sum()


print("\nSector validation:")
print(
    "Duplicate company sector records:",
    sector_duplicates
)


# Keep one sector record per company

sectors = sectors.drop_duplicates(
    subset=["company_id"],
    keep="first"
).copy()


print(
    "Unique companies in sector data:",
    sectors["company_id"].nunique()
)


# ==========================================================
# 15. MERGE SECTOR INFORMATION
# ==========================================================

df = df.merge(
    sectors,
    on="company_id",
    how="left",
    validate="many_to_one"
)


# ==========================================================
# 16. VERIFY NO DUPLICATES AFTER SECTOR MERGE
# ==========================================================

duplicates_after_sector_merge = df.duplicated(
    ["company_id", "year"]
).sum()


print(
    "\nCompany-year duplicates after sector merge:",
    duplicates_after_sector_merge
)


if duplicates_after_sector_merge > 0:
    raise ValueError(
        "Duplicate company-year records detected after "
        "sector merge. Sector data is still not unique."
    )


# ==========================================================
# 17. SECTOR COVERAGE
# ==========================================================

print(
    "Rows with sector information:",
    df["broad_sector"].notna().sum()
)

print(
    "Rows without sector information:",
    df["broad_sector"].isna().sum()
)


# ==========================================================
# 18. FINANCIALS SECTOR FLAG
# ==========================================================

df["is_financials_sector"] = (
    df["broad_sector"]
    .astype(str)
    .str.strip()
    .str.casefold()
    == "financials"
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
# 19. NET PROFIT MARGIN
# ==========================================================

df["net_profit_margin_pct"] = df.apply(
    lambda row: net_profit_margin(
        row["net_profit"],
        row["sales"],
    ),
    axis=1,
)


# ==========================================================
# 20. OPERATING PROFIT MARGIN
# ==========================================================

df["operating_profit_margin_pct"] = df.apply(
    lambda row: operating_profit_margin(
        row["operating_profit"],
        row["sales"],
    ),
    axis=1,
)


# ==========================================================
# 21. RETURN ON EQUITY
# ==========================================================

df["roe_pct"] = df.apply(
    lambda row: return_on_equity(
        row["net_profit"],
        row["equity_capital"],
        row["reserves"],
    ),
    axis=1,
)


# ==========================================================
# 22. RETURN ON CAPITAL EMPLOYED
# ==========================================================

df["roce_pct"] = df.apply(
    lambda row: return_on_capital_employed(
        row["operating_profit"],
        row["equity_capital"],
        row["reserves"],
        row["borrowings"],
    ),
    axis=1,
)


# ==========================================================
# 23. RETURN ON ASSETS
# ==========================================================

df["roa_pct"] = df.apply(
    lambda row: return_on_assets(
        row["net_profit"],
        row["total_assets"],
    ),
    axis=1,
)


# ==========================================================
# 24. OPM CROSS-CHECK
# ==========================================================

df["opm_mismatch"] = df.apply(
    lambda row: check_opm_difference(
        row["operating_profit_margin_pct"],
        row["opm_percentage"],
    ),
    axis=1,
)


# Absolute difference between calculated and source OPM

df["opm_difference"] = (
    df["operating_profit_margin_pct"]
    - df["opm_percentage"]
).abs()


# ==========================================================
# 25. OPM ANOMALIES
# ==========================================================

opm_anomalies = df[
    df["opm_difference"] > 1
].copy()


opm_anomalies[
    [
        "company_id",
        "year",
        "operating_profit_margin_pct",
        "opm_percentage",
        "opm_difference",
    ]
].to_csv(
    OPM_ANOMALIES_FILE,
    index=False,
)


print(
    "\nOPM anomalies (>1 percentage point):",
    len(opm_anomalies)
)


# ==========================================================
# 26. FINAL VALIDATION
# ==========================================================

print("\n========================================")
print("PROFITABILITY RATIO VALIDATION")
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
    "Financials companies:",
    df.loc[
        df["is_financials_sector"],
        "company_id"
    ].nunique()
)


print(
    "OPM mismatches:",
    df["opm_mismatch"].sum()
)


print(
    "OPM differences > 1:",
    (df["opm_difference"] > 1).sum()
)


# ==========================================================
# 27. CHECK MISSING OFFICIAL COMPANIES
# ==========================================================

output_companies = set(
    df["company_id"].unique()
)

missing_companies = sorted(
    valid_companies - output_companies
)


print(
    "\nOfficial companies missing from profitability output:",
    missing_companies
)


# ==========================================================
# 28. DISPLAY SAMPLE RESULTS
# ==========================================================

print("\nSample results:")

print(
    df[
        [
            "company_id",
            "year",
            "broad_sector",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "roe_pct",
            "roce_pct",
            "roa_pct",
            "opm_mismatch",
            "opm_difference",
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ==========================================================
# 29. SAVE FINAL OUTPUT
# ==========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
)


print("\nSaved:")
print(OUTPUT_FILE)
print(OPM_ANOMALIES_FILE)


# ==========================================================
# 30. FINAL SUCCESS CHECK
# ==========================================================

final_duplicates = df.duplicated(
    ["company_id", "year"]
).sum()


if final_duplicates != 0:
    raise ValueError(
        "FINAL VALIDATION FAILED: "
        f"{final_duplicates} company-year duplicates remain."
    )


print("\n========================================")
print("FINAL VALIDATION PASSED")
print("========================================")