import pandas as pd

from src.analytics.cagr import calculate_growth_metrics


# ==========================================================
# CONFIGURATION
# ==========================================================

pnl_path = "data/processed/profitandloss_cleaned.csv"
output_path = "output/cagr_analysis.csv"

analysis_year = 2024


# ==========================================================
# 1. LOAD CLEANED P&L DATA
# ==========================================================

print("\nLoading cleaned P&L data...")

pnl = pd.read_csv(pnl_path)

print("Rows loaded:", len(pnl))


# ==========================================================
# 2. NORMALIZE REQUIRED COLUMNS
# ==========================================================

pnl.columns = [
    str(col).strip().lower()
    for col in pnl.columns
]

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
).copy()

pnl["year"] = pnl["year"].astype(int)


# ==========================================================
# 3. KEEP REQUIRED COLUMNS
# ==========================================================

required_columns = [
    "company_id",
    "year",
    "sales",
    "net_profit",
    "eps",
]

missing_columns = [
    column
    for column in required_columns
    if column not in pnl.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

pnl = pnl[required_columns].copy()


# ==========================================================
# 4. VERIFY COMPANY-YEAR UNIQUENESS
# ==========================================================

duplicates = pnl.duplicated(
    subset=["company_id", "year"]
).sum()

print(
    "Company-year duplicates:",
    duplicates
)

if duplicates > 0:
    raise ValueError(
        "Duplicate company-year records found "
        "in cleaned P&L data."
    )


# ==========================================================
# 5. VERIFY ANALYSIS YEAR
# ==========================================================

available_years = set(
    pnl["year"].unique()
)

if analysis_year not in available_years:
    raise ValueError(
        f"Analysis year {analysis_year} "
        "is not available in P&L data."
    )


# ==========================================================
# 6. CALCULATE CAGR
# ==========================================================

results = []

companies = sorted(
    pnl["company_id"].unique()
)

print(
    f"\nCalculating CAGR for "
    f"{len(companies)} companies..."
)

for company_id in companies:

    metrics = calculate_growth_metrics(
        df=pnl,
        company_id=company_id,
        end_year=analysis_year,
    )

    row = {
        "company_id": company_id,
        **metrics,
    }

    results.append(row)


# ==========================================================
# 7. CREATE RESULT DATAFRAME
# ==========================================================

result_df = pd.DataFrame(results)


# ==========================================================
# 8. BASIC VALIDATION
# ==========================================================

print("\n========================================")
print("CAGR VALIDATION")
print("========================================")

print(
    "Total companies:",
    result_df["company_id"].nunique()
)

print(
    "Result rows:",
    len(result_df)
)

print(
    "Expected companies:",
    len(companies)
)


# ==========================================================
# 9. FLAG COUNTS
# ==========================================================

for metric in [
    "revenue",
    "pat",
    "eps",
]:

    print(
        f"\n{metric.upper()} CAGR 5Y flags:"
    )

    print(
        result_df[
            f"{metric}_cagr_5yr_flag"
        ].value_counts(dropna=False)
    )


# ==========================================================
# 10. SAVE OUTPUT
# ==========================================================

result_df.to_csv(
    output_path,
    index=False
)

print(
    f"\nSaved: {output_path}"
)

print("\nSample results:")

print(
    result_df.head(10).to_string(
        index=False
    )
)