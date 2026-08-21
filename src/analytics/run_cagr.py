import pandas as pd

from src.analytics.cagr import calculate_cagr


# ==========================================================
# 1. LOAD DATA
# ==========================================================

pnl = pd.read_excel(
    "data/raw/profitandloss.xlsx",
    header=1
)

companies = pd.read_excel(
    "data/raw/companies.xlsx",
    header=1
)


# ==========================================================
# 2. KEEP OFFICIAL N100 COMPANIES
# ==========================================================

valid_companies = set(
    companies["id"].dropna()
)

pnl = pnl[
    pnl["company_id"].isin(valid_companies)
].copy()


# ==========================================================
# 3. KEEP REQUIRED COLUMNS
# ==========================================================

pnl = pnl[
    [
        "company_id",
        "year",
        "sales",
        "net_profit",
        "eps",
    ]
].copy()


# ==========================================================
# 4. CONVERT YEAR TO NUMERIC YEAR
# ==========================================================

pnl["year_num"] = (
    pnl["year"]
    .astype(str)
    .str.extract(r"(\d{4})")[0]
)

pnl["year_num"] = pd.to_numeric(
    pnl["year_num"],
    errors="coerce"
)

# Remove rows where year cannot be determined
pnl = pnl.dropna(
    subset=["year_num"]
).copy()

pnl["year_num"] = pnl["year_num"].astype(int)


# ==========================================================
# 5. REMOVE DUPLICATE COMPANY-YEAR RECORDS
# ==========================================================

pnl = pnl.sort_values(
    ["company_id", "year_num"]
)

pnl = pnl.drop_duplicates(
    subset=["company_id", "year_num"],
    keep="last"
)


# ==========================================================
# 6. CAGR HELPER
# ==========================================================

def get_cagr_for_window(
    company_data,
    value_column,
    window
):
    """
    Calculate CAGR using the earliest and latest
    available observations within the requested window.

    Example:
        5-year CAGR requires approximately 5 years
        between start and end observations.
    """

    data = company_data[
        ["year_num", value_column]
    ].dropna()

    data = data.sort_values("year_num")

    if data.empty:
        return None, "INSUFFICIENT"

    latest_year = data["year_num"].max()

    target_start_year = latest_year - window

    # Look for the observation at the target year
    start_rows = data[
        data["year_num"] == target_start_year
    ]

    end_rows = data[
        data["year_num"] == latest_year
    ]

    if start_rows.empty or end_rows.empty:
        return None, "INSUFFICIENT"

    start_value = start_rows.iloc[0][value_column]
    end_value = end_rows.iloc[0][value_column]

    return calculate_cagr(
        start_value,
        end_value,
        window
    )


# ==========================================================
# 7. CALCULATE CAGR FOR EACH COMPANY
# ==========================================================

results = []

windows = [3, 5, 10]

for company_id, company_data in pnl.groupby(
    "company_id"
):

    row = {
        "company_id": company_id
    }

    for window in windows:

        # ------------------------------
        # Revenue CAGR
        # ------------------------------

        revenue_value, revenue_flag = get_cagr_for_window(
            company_data,
            "sales",
            window
        )

        row[f"revenue_cagr_{window}yr"] = revenue_value
        row[f"revenue_cagr_{window}yr_flag"] = revenue_flag


        # ------------------------------
        # PAT CAGR
        # ------------------------------

        pat_value, pat_flag = get_cagr_for_window(
            company_data,
            "net_profit",
            window
        )

        row[f"pat_cagr_{window}yr"] = pat_value
        row[f"pat_cagr_{window}yr_flag"] = pat_flag


        # ------------------------------
        # EPS CAGR
        # ------------------------------

        eps_value, eps_flag = get_cagr_for_window(
            company_data,
            "eps",
            window
        )

        row[f"eps_cagr_{window}yr"] = eps_value
        row[f"eps_cagr_{window}yr_flag"] = eps_flag

    results.append(row)


# ==========================================================
# 8. CREATE RESULT DATAFRAME
# ==========================================================

result_df = pd.DataFrame(results)


# ==========================================================
# 9. BASIC CHECKS
# ==========================================================

print("Total companies:", result_df["company_id"].nunique())

print(
    "Result rows:",
    len(result_df)
)

print("\nSample CAGR results:")

print(
    result_df.head(10).to_string(
        index=False
    )
)


# ==========================================================
# 10. FLAG COUNTS
# ==========================================================

print("\nRevenue CAGR flags:")

print(
    result_df[
        "revenue_cagr_5yr_flag"
    ].value_counts(dropna=False)
)


print("\nPAT CAGR flags:")

print(
    result_df[
        "pat_cagr_5yr_flag"
    ].value_counts(dropna=False)
)


print("\nEPS CAGR flags:")

print(
    result_df[
        "eps_cagr_5yr_flag"
    ].value_counts(dropna=False)
)


# ==========================================================
# 11. SAVE OUTPUT
# ==========================================================

result_df.to_csv(
    "output/cagr_analysis.csv",
    index=False
)

print(
    "\nSaved:"
)

print(
    "output/cagr_analysis.csv"
)