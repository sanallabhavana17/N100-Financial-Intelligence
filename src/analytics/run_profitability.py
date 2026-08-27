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
# HELPER FUNCTIONS
# ==========================================================

def normalize_company_id(series):
    """
    Normalize company identifiers.
    """
    return (
        series
        .astype(str)
        .str.strip()
        .str.upper()
    )


def normalize_year(value):
    """
    Normalize financial year values.

    Handles values such as:
        2014
        2014.0
        Mar 2014
        Dec 2012
        2012-03-31
    """

    if pd.isna(value):
        return pd.NA

    text = str(value).strip()

    # Direct numeric year
    try:
        numeric = float(text)

        if 1900 <= numeric <= 2100:
            return int(numeric)

    except ValueError:
        pass

    # Extract a 4-digit year
    import re

    match = re.search(r"(19|20)\d{2}", text)

    if match:
        return int(match.group())

    return pd.NA


# ==========================================================
# 1. LOAD CLEANED DATA
# ==========================================================

print("\nLoading cleaned financial data...")

pnl = pd.read_csv(PNL_FILE)
balance = pd.read_csv(BALANCE_FILE)

print("P&L rows loaded:", len(pnl))
print("Balance Sheet rows loaded:", len(balance))


# ==========================================================
# 2. LOAD COMPANIES
# ==========================================================

companies = pd.read_excel(
    COMPANIES_FILE,
    header=1
)

companies.columns = [
    str(col).strip().lower()
    for col in companies.columns
]

companies["id"] = normalize_company_id(
    companies["id"]
)

valid_companies = set(
    companies["id"].dropna()
)

print(
    "Official N100 companies:",
    len(valid_companies)
)


# ==========================================================
# 3. LOAD SECTOR DATA
# ==========================================================

# sectors.xlsx does not have a proper header row.

sectors = pd.read_excel(
    SECTORS_FILE,
    header=None,
    names=[
        "id",
        "company_id",
        "broad_sector",
        "sector",
        "metric",
        "market_cap_category",
    ],
)

sectors["company_id"] = normalize_company_id(
    sectors["company_id"]
)

sectors["broad_sector"] = (
    sectors["broad_sector"]
    .astype(str)
    .str.strip()
)

sectors["sector"] = (
    sectors["sector"]
    .astype(str)
    .str.strip()
)


# Keep only required sector columns.

sectors = sectors[
    [
        "company_id",
        "broad_sector",
        "sector",
    ]
].copy()


# Remove duplicate company sector mappings.

sectors = sectors.drop_duplicates(
    subset=["company_id"],
    keep="first"
)


print(
    "Unique sector companies:",
    sectors["company_id"].nunique()
)


# ==========================================================
# 4. NORMALIZE P&L
# ==========================================================

pnl.columns = [
    str(col).strip().lower()
    for col in pnl.columns
]

pnl["company_id"] = normalize_company_id(
    pnl["company_id"]
)

pnl["year"] = pnl["year"].apply(
    normalize_year
)

pnl["year"] = pd.to_numeric(
    pnl["year"],
    errors="coerce"
)

pnl = pnl.dropna(
    subset=["company_id", "year"]
).copy()

pnl["year"] = pnl["year"].astype(int)


# ==========================================================
# 5. NORMALIZE BALANCE SHEET
# ==========================================================

balance.columns = [
    str(col).strip().lower()
    for col in balance.columns
]

balance["company_id"] = normalize_company_id(
    balance["company_id"]
)

balance["year"] = balance["year"].apply(
    normalize_year
)

balance["year"] = pd.to_numeric(
    balance["year"],
    errors="coerce"
)

balance = balance.dropna(
    subset=["company_id", "year"]
).copy()

balance["year"] = balance["year"].astype(int)


# ==========================================================
# 6. KEEP ONLY OFFICIAL N100 COMPANIES
# ==========================================================

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
# 7. VERIFY P&L UNIQUENESS
# ==========================================================

pnl_duplicates = pnl.duplicated(
    subset=["company_id", "year"]
).sum()

print(
    "\nP&L company-year duplicates:",
    pnl_duplicates
)

if pnl_duplicates > 0:

    print(
        "WARNING: duplicate P&L company-year records found."
    )

    duplicate_pnl = pnl[
        pnl.duplicated(
            subset=["company_id", "year"],
            keep=False
        )
    ].sort_values(
        ["company_id", "year"]
    )

    print(
        duplicate_pnl[
            ["company_id", "year"]
        ].head(30).to_string(index=False)
    )

    raise ValueError(
        "P&L cleaned data must contain unique "
        "(company_id, year) records."
    )


# ==========================================================
# 8. VERIFY BALANCE SHEET UNIQUENESS
# ==========================================================

balance_duplicates = balance.duplicated(
    subset=["company_id", "year"]
).sum()

print(
    "Balance Sheet company-year duplicates:",
    balance_duplicates
)

if balance_duplicates > 0:

    print(
        "WARNING: duplicate Balance Sheet company-year "
        "records found."
    )

    duplicate_balance = balance[
        balance.duplicated(
            subset=["company_id", "year"],
            keep=False
        )
    ].sort_values(
        ["company_id", "year"]
    )

    print(
        duplicate_balance[
            ["company_id", "year"]
        ].head(30).to_string(index=False)
    )

    raise ValueError(
        "Balance Sheet cleaned data must contain unique "
        "(company_id, year) records."
    )


# ==========================================================
# 9. SELECT REQUIRED P&L COLUMNS
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
# 10. SELECT REQUIRED BALANCE SHEET COLUMNS
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
# 11. MERGE P&L + BALANCE SHEET
# ==========================================================

df = pd.merge(
    pnl,
    balance,
    on=["company_id", "year"],
    how="inner",
    validate="one_to_one",
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
# 12. VERIFY MERGED UNIQUENESS
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
        "Duplicate company-year records detected "
        "after P&L + Balance Sheet merge."
    )


# ==========================================================
# 13. ADD SECTOR INFORMATION
# ==========================================================

df = df.merge(
    sectors,
    on="company_id",
    how="left",
    validate="many_to_one",
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
# 14. FINANCIALS SECTOR IDENTIFICATION
# ==========================================================

df["is_financials_sector"] = (
    df["broad_sector"]
    .str.strip()
    .str.lower()
    .eq("financials")
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
# 15. NET PROFIT MARGIN
# ==========================================================

df["net_profit_margin_pct"] = df.apply(
    lambda row: net_profit_margin(
        row["net_profit"],
        row["sales"],
    ),
    axis=1,
)


# ==========================================================
# 16. OPERATING PROFIT MARGIN
# ==========================================================

df["operating_profit_margin_pct"] = df.apply(
    lambda row: operating_profit_margin(
        row["operating_profit"],
        row["sales"],
    ),
    axis=1,
)


# ==========================================================
# 17. RETURN ON EQUITY
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
# 18. RETURN ON CAPITAL EMPLOYED
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
# 19. RETURN ON ASSETS
# ==========================================================

df["roa_pct"] = df.apply(
    lambda row: return_on_assets(
        row["net_profit"],
        row["total_assets"],
    ),
    axis=1,
)


# ==========================================================
# 20. OPM CROSS-CHECK
# ==========================================================

df["opm_mismatch"] = df.apply(
    lambda row: check_opm_difference(
        row["operating_profit_margin_pct"],
        row["opm_percentage"],
    ),
    axis=1,
)


df["opm_difference"] = (
    df["operating_profit_margin_pct"]
    - df["opm_percentage"]
).abs()


# ==========================================================
# 21. SAVE OPM ANOMALIES
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
# 22. FINAL VALIDATION
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
        subset=["company_id", "year"]
    ).sum()
)


print(
    "Expected official companies:",
    len(valid_companies)
)


# ==========================================================
# 23. CHECK DUPLICATE RECORDS
# ==========================================================

final_duplicates = df[
    df.duplicated(
        subset=["company_id", "year"],
        keep=False,
    )
].sort_values(
    ["company_id", "year"]
)


if len(final_duplicates) > 0:

    print("\nDuplicate company-year records:")

    print(
        final_duplicates[
            ["company_id", "year"]
        ].to_string(index=False)
    )

    raise ValueError(
        "Final profitability output contains "
        "duplicate company-year records."
    )


# ==========================================================
# 24. CHECK MISSING OFFICIAL COMPANIES
# ==========================================================

output_companies = set(
    df["company_id"].unique()
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
# 25. OPM VALIDATION
# ==========================================================

print(
    "\nOPM mismatches:",
    df["opm_mismatch"].sum()
)

print(
    "OPM differences > 1:",
    (
        df["opm_difference"] > 1
    ).sum()
)


# ==========================================================
# 26. SAMPLE RESULTS
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
# 27. SAVE FINAL OUTPUT
# ==========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
)


print("\nSaved:")
print(OUTPUT_FILE)
print(OPM_ANOMALIES_FILE)


# ==========================================================
# 28. FINAL SUCCESS MESSAGE
# ==========================================================

print("\n========================================")
print("PROFITABILITY ANALYSIS COMPLETED")
print("========================================")