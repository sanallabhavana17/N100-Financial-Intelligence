import pandas as pd

from src.analytics.cagr import (
    revenue_cagr,
    pat_cagr,
    eps_cagr,
)


# ==========================================================
# 1. LOAD CLEANED P&L DATA
# ==========================================================

print("\nLoading cleaned P&L data...")

pnl = pd.read_csv(
    "data/processed/profitandloss_cleaned.csv"
)

print("P&L rows loaded:", len(pnl))


# ==========================================================
# 2. KEEP REQUIRED COLUMNS
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
# 3. NORMALIZE YEAR
# ==========================================================

def normalize_year(value):

    if pd.isna(value):
        return None

    value = str(value)

    import re

    match = re.search(r"\d{4}", value)

    if match:
        return int(match.group())

    return None


pnl["year"] = pnl["year"].apply(normalize_year)

pnl = pnl.dropna(
    subset=["company_id", "year"]
).copy()

pnl["year"] = pnl["year"].astype(int)


# ==========================================================
# 4. NORMALIZE COMPANY ID
# ==========================================================

pnl["company_id"] = (
    pnl["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# ==========================================================
# 5. REMOVE COMPANY-YEAR DUPLICATES
# ==========================================================

pnl = pnl.drop_duplicates(
    subset=["company_id", "year"],
    keep="first"
).copy()


# ==========================================================
# 6. SORT DATA
# ==========================================================

pnl = pnl.sort_values(
    ["company_id", "year"]
).reset_index(drop=True)


print(
    "Companies:",
    pnl["company_id"].nunique()
)

print(
    "Company-year rows:",
    len(pnl)
)

print(
    "Company-year duplicates:",
    pnl.duplicated(
        ["company_id", "year"]
    ).sum()
)


# ==========================================================
# 7. CAGR CALCULATION FUNCTION
# ==========================================================

def calculate_company_cagrs(company_id, group):

    group = group.sort_values("year").copy()

    results = []

    for _, row in group.iterrows():

        current_year = int(row["year"])

        result = {
            "company_id": company_id,
            "year": current_year,
        }

        # --------------------------------------------------
        # Calculate 3-year, 5-year and 10-year CAGR
        # --------------------------------------------------

        for window in [3, 5, 10]:

            target_year = current_year - window

            previous = group[
                group["year"] == target_year
            ]

            # --------------------------------------------------
            # If exact target year does not exist
            # --------------------------------------------------

            if len(previous) == 0:

                revenue_value = None
                revenue_flag = "INSUFFICIENT"

                pat_value = None
                pat_flag = "INSUFFICIENT"

                eps_value = None
                eps_flag = "INSUFFICIENT"

            else:

                previous_row = previous.iloc[0]

                # --------------------------------------------------
                # Revenue CAGR
                # --------------------------------------------------

                revenue_value, revenue_flag = revenue_cagr(
                    previous_row["sales"],
                    row["sales"],
                    window
                )

                # --------------------------------------------------
                # PAT CAGR
                # --------------------------------------------------

                pat_value, pat_flag = pat_cagr(
                    previous_row["net_profit"],
                    row["net_profit"],
                    window
                )

                # --------------------------------------------------
                # EPS CAGR
                # --------------------------------------------------

                eps_value, eps_flag = eps_cagr(
                    previous_row["eps"],
                    row["eps"],
                    window
                )

            # --------------------------------------------------
            # Revenue
            # --------------------------------------------------

            result[
                f"revenue_cagr_{window}yr"
            ] = revenue_value

            result[
                f"revenue_cagr_{window}yr_flag"
            ] = revenue_flag

            # --------------------------------------------------
            # PAT
            # --------------------------------------------------

            result[
                f"pat_cagr_{window}yr"
            ] = pat_value

            result[
                f"pat_cagr_{window}yr_flag"
            ] = pat_flag

            # --------------------------------------------------
            # EPS
            # --------------------------------------------------

            result[
                f"eps_cagr_{window}yr"
            ] = eps_value

            result[
                f"eps_cagr_{window}yr_flag"
            ] = eps_flag

        results.append(result)

    return results


# ==========================================================
# 8. CALCULATE CAGR FOR ALL COMPANIES
# ==========================================================

print("\nCalculating CAGR...")

all_results = []

for company_id, group in pnl.groupby("company_id"):

    company_results = calculate_company_cagrs(
        company_id,
        group
    )

    all_results.extend(company_results)


result = pd.DataFrame(all_results)


# ==========================================================
# 9. SORT FINAL RESULT
# ==========================================================

result = result.sort_values(
    ["company_id", "year"]
).reset_index(drop=True)


# ==========================================================
# 10. SAVE OUTPUT
# ==========================================================

output_path = "output/cagr_ratios.csv"

result.to_csv(
    output_path,
    index=False
)


# ==========================================================
# 11. VALIDATION
# ==========================================================

print("\n========================================")
print("CAGR VALIDATION")
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
# 12. CHECK COMPANY-YEAR COVERAGE
# ==========================================================

expected_rows = (
    pnl[
        ["company_id", "year"]
    ]
    .drop_duplicates()
    .shape[0]
)

print(
    "Expected company-year rows:",
    expected_rows
)

print(
    "Actual CAGR rows:",
    len(result)
)


# ==========================================================
# 13. FLAG COUNTS
# ==========================================================

for metric in [
    "revenue",
    "pat",
    "eps",
]:

    for window in [3, 5, 10]:

        column = (
            f"{metric}_cagr_{window}yr_flag"
        )

        print(
            f"\n{column}:"
        )

        print(
            result[column]
            .value_counts(dropna=False)
            .to_string()
        )


# ==========================================================
# 14. SAMPLE RESULTS
# ==========================================================

print("\nSample results:")

print(
    result[
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
            "pat_cagr_5yr",
            "pat_cagr_10yr",
            "eps_cagr_3yr",
            "eps_cagr_5yr",
            "eps_cagr_10yr",
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ==========================================================
# 15. OUTPUT
# ==========================================================

print("\nSaved:")
print(output_path)

print("\n========================================")
print("CAGR ANALYSIS COMPLETED")
print("========================================")