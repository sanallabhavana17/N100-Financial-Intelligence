import pandas as pd

from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

CASHFLOW_FILE = "data/processed/cashflow_cleaned.csv"
PNL_FILE = "data/processed/profitandloss_cleaned.csv"
OUTPUT_FILE = "output/cashflow_kpis.csv"


# ==========================================================
# 1. LOAD DATA
# ==========================================================

print("\nLoading cleaned financial data...")

cashflow = pd.read_csv(CASHFLOW_FILE)
pnl = pd.read_csv(PNL_FILE)

print("Cash Flow rows:", len(cashflow))
print("P&L rows:", len(pnl))


# ==========================================================
# 2. NORMALIZE COLUMNS
# ==========================================================

cashflow.columns = [
    str(col).strip().lower()
    for col in cashflow.columns
]

pnl.columns = [
    str(col).strip().lower()
    for col in pnl.columns
]


# ==========================================================
# 3. NORMALIZE COMPANY IDs
# ==========================================================

for df in [cashflow, pnl]:

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


# Remove invalid years

cashflow = cashflow.dropna(
    subset=["company_id", "year"]
).copy()

pnl = pnl.dropna(
    subset=["company_id", "year"]
).copy()

cashflow["year"] = cashflow["year"].astype(int)
pnl["year"] = pnl["year"].astype(int)


# ==========================================================
# 4. VERIFY UNIQUENESS
# ==========================================================

cashflow_duplicates = cashflow.duplicated(
    ["company_id", "year"]
).sum()

pnl_duplicates = pnl.duplicated(
    ["company_id", "year"]
).sum()

print(
    "Cash Flow company-year duplicates:",
    cashflow_duplicates
)

print(
    "P&L company-year duplicates:",
    pnl_duplicates
)

if cashflow_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found "
        "in Cash Flow data."
    )

if pnl_duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found "
        "in P&L data."
    )


# ==========================================================
# 5. SELECT REQUIRED COLUMNS
# ==========================================================

cashflow = cashflow[
    [
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    ]
].copy()

pnl = pnl[
    [
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "net_profit",
    ]
].copy()


# ==========================================================
# 6. MERGE CASH FLOW WITH P&L
# ==========================================================

df = cashflow.merge(
    pnl,
    on=["company_id", "year"],
    how="left",
    validate="one_to_one",
)

print(
    "\nMerged rows:",
    len(df)
)

print(
    "Companies:",
    df["company_id"].nunique()
)


# ==========================================================
# 7. CALCULATE CASH FLOW KPIs
# ==========================================================

results = []

for _, row in df.iterrows():

    cfo = row["operating_activity"]
    cfi = row["investing_activity"]
    cff = row["financing_activity"]

    sales = row["sales"]
    operating_profit = row["operating_profit"]
    pat = row["net_profit"]


    # ------------------------------------------------------
    # Free Cash Flow
    # ------------------------------------------------------

    fcf = free_cash_flow(
        cfo,
        cfi,
    )


    # ------------------------------------------------------
    # CFO Quality
    # ------------------------------------------------------

    cfo_quality_ratio, cfo_quality_label = (
        cfo_quality_score(
            cfo,
            pat,
        )
    )


    # ------------------------------------------------------
    # CapEx Intensity
    # ------------------------------------------------------

    capex_intensity_pct, capex_intensity_label = (
        capex_intensity(
            cfi,
            sales,
        )
    )


    # ------------------------------------------------------
    # FCF Conversion
    # ------------------------------------------------------

    fcf_conversion_pct = fcf_conversion_rate(
        fcf,
        operating_profit,
    )


    # ------------------------------------------------------
    # Capital Allocation
    # ------------------------------------------------------

    pattern_label = capital_allocation_pattern(
        cfo,
        cfi,
        cff,
        cfo_quality_ratio,
    )


    results.append(
        {
            "company_id": row["company_id"],
            "year": row["year"],
            "cfo": cfo,
            "cfi": cfi,
            "cff": cff,
            "sales": sales,
            "operating_profit": operating_profit,
            "pat": pat,
            "free_cash_flow": fcf,
            "cfo_quality_ratio": cfo_quality_ratio,
            "cfo_quality_label": cfo_quality_label,
            "capex_intensity_pct": capex_intensity_pct,
            "capex_intensity_label": capex_intensity_label,
            "fcf_conversion_pct": fcf_conversion_pct,
            "capital_allocation_pattern": pattern_label,
        }
    )


# ==========================================================
# 8. CREATE RESULT DATAFRAME
# ==========================================================

result = pd.DataFrame(results)


# ==========================================================
# 9. VALIDATION
# ==========================================================

print("\n========================================")
print("CASH FLOW KPI VALIDATION")
print("========================================")

print(
    "Rows:",
    len(result)
)

print(
    "Companies:",
    result["company_id"].nunique()
)

print(
    "Company-year duplicates:",
    result.duplicated(
        ["company_id", "year"]
    ).sum()
)


# ==========================================================
# 10. KPI DISTRIBUTIONS
# ==========================================================

print("\nCFO Quality Distribution:")

print(
    result[
        "cfo_quality_label"
    ].value_counts(dropna=False)
)


print("\nCapEx Intensity Distribution:")

print(
    result[
        "capex_intensity_label"
    ].value_counts(dropna=False)
)


print("\nCapital Allocation Distribution:")

print(
    result[
        "capital_allocation_pattern"
    ].value_counts(dropna=False)
)


# ==========================================================
# 11. SAVE OUTPUT
# ==========================================================

result.to_csv(
    OUTPUT_FILE,
    index=False,
)

print(
    f"\nSaved: {OUTPUT_FILE}"
)


# ==========================================================
# 12. SAMPLE OUTPUT
# ==========================================================

print("\nSample results:")

print(
    result.head(10).to_string(
        index=False
    )
)