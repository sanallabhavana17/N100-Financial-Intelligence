import pandas as pd

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    check_opm_difference,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
)


# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

pnl = pd.read_excel(
    "data/raw/profitandloss.xlsx",
    header=1
)

balance = pd.read_excel(
    "data/raw/balancesheet.xlsx",
    header=1
)

# IMPORTANT:
# sectors.xlsx does NOT have a proper header row.
# We assign the column names ourselves.
sectors = pd.read_excel(
    "data/raw/sectors.xlsx",
    header=None,
    names=[
        "id",
        "company_id",
        "broad_sector",
        "sector",
        "some_metric",
        "market_cap_category"
    ]
)


# --------------------------------------------------
# 2. Keep required P&L columns
# --------------------------------------------------

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
]


# --------------------------------------------------
# 3. Keep required Balance Sheet columns
# --------------------------------------------------

balance = balance[
    [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "total_assets",
    ]
]


# --------------------------------------------------
# 4. Keep required Sector columns
# --------------------------------------------------

sectors = sectors[
    [
        "company_id",
        "broad_sector",
        "sector",
    ]
]


# --------------------------------------------------
# 5. Combine P&L + Balance Sheet
# --------------------------------------------------

df = pd.merge(
    pnl,
    balance,
    on=["company_id", "year"],
    how="inner"
)


# --------------------------------------------------
# 6. Keep only official N100 companies
# --------------------------------------------------

companies = pd.read_excel(
    "data/raw/companies.xlsx",
    header=1
)

valid_companies = set(
    companies["id"].dropna()
)

df = df[
    df["company_id"].isin(valid_companies)
].copy()


# --------------------------------------------------
# 7. Add sector information
# --------------------------------------------------

df = df.merge(
    sectors,
    on="company_id",
    how="left"
)


print("Rows after merging:", len(df))

print(
    "Companies with sector information:",
    df["broad_sector"].notna().sum()
)


# --------------------------------------------------
# 8. Financials sector identification
# --------------------------------------------------

df["is_financials_sector"] = (
    df["broad_sector"] == "Financials"
)


print(
    "Financials company-year rows:",
    df["is_financials_sector"].sum()
)


# --------------------------------------------------
# 9. Net Profit Margin
# --------------------------------------------------

df["net_profit_margin_pct"] = df.apply(
    lambda row: net_profit_margin(
        row["net_profit"],
        row["sales"]
    ),
    axis=1
)


# --------------------------------------------------
# 10. Operating Profit Margin
# --------------------------------------------------

df["operating_profit_margin_pct"] = df.apply(
    lambda row: operating_profit_margin(
        row["operating_profit"],
        row["sales"]
    ),
    axis=1
)


# --------------------------------------------------
# 11. Return on Equity
# --------------------------------------------------

df["roe_pct"] = df.apply(
    lambda row: return_on_equity(
        row["net_profit"],
        row["equity_capital"],
        row["reserves"]
    ),
    axis=1
)


# --------------------------------------------------
# 12. Return on Capital Employed
# --------------------------------------------------

df["roce_pct"] = df.apply(
    lambda row: return_on_capital_employed(
        row["operating_profit"],
        row["equity_capital"],
        row["reserves"],
        row["borrowings"]
    ),
    axis=1
)


# --------------------------------------------------
# 13. Return on Assets
# --------------------------------------------------

df["roa_pct"] = df.apply(
    lambda row: return_on_assets(
        row["net_profit"],
        row["total_assets"]
    ),
    axis=1
)


# --------------------------------------------------
# 14. OPM Cross-Check
# --------------------------------------------------

df["opm_mismatch"] = df.apply(
    lambda row: check_opm_difference(
        row["operating_profit_margin_pct"],
        row["opm_percentage"]
    ),
    axis=1
)


df["opm_difference"] = (
    df["operating_profit_margin_pct"]
    - df["opm_percentage"]
).abs()


# --------------------------------------------------
# 15. Save OPM anomalies
# --------------------------------------------------

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
    "output/opm_anomalies.csv",
    index=False
)


print(
    "OPM anomalies (>1 percentage point):",
    len(opm_anomalies)
)


# --------------------------------------------------
# 16. Display sample results
# --------------------------------------------------

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


# --------------------------------------------------
# 17. Basic checks
# --------------------------------------------------

print("\nTotal companies:", df["company_id"].nunique())

print(
    "Total company-year rows:",
    len(df)
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


# --------------------------------------------------
# 18. Save final profitability output
# --------------------------------------------------

df.to_csv(
    "output/profitability_ratios.csv",
    index=False
)


print("\nSaved:")
print("output/profitability_ratios.csv")
print("output/opm_anomalies.csv")