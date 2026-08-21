from pathlib import Path

import pandas as pd

from src.etl.loader import load_all_files


PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def prepare_ratio_data():

    data = load_all_files()

    # =========================================================
    # 1. Official 92 companies
    # =========================================================

    companies = data["companies.xlsx"]

    official_companies = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    print(f"Official companies: {len(official_companies)}")

    # =========================================================
    # 2. Load source files
    # =========================================================

    pnl = data["profitandloss.xlsx"].copy()
    balance = data["balancesheet.xlsx"].copy()
    cashflow = data["cashflow.xlsx"].copy()

    # =========================================================
    # 3. Clean company IDs
    # =========================================================

    for df in [pnl, balance, cashflow]:

        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
        )

    # Cash Flow typo
    cashflow["company_id"] = cashflow["company_id"].replace(
        {"AGTL": "ATGL"}
    )

    # =========================================================
    # 4. Keep official companies only
    # =========================================================

    pnl = pnl[
        pnl["company_id"].isin(official_companies)
    ].copy()

    balance = balance[
        balance["company_id"].isin(official_companies)
    ].copy()

    cashflow = cashflow[
        cashflow["company_id"].isin(official_companies)
    ].copy()

    # =========================================================
    # 5. Clean Balance Sheet years
    #
    # Keep:
    #   Mar YYYY
    #   YYYY
    #
    # Remove:
    #   Sep YYYY
    #   Dec YYYY
    #   Jun YYYY
    #
    # =========================================================

    balance["year_raw"] = (
        balance["year"]
        .astype(str)
        .str.strip()
    )

    # Identify March records
    is_march = balance["year_raw"].str.startswith(
        "Mar",
        na=False
    )

    # Identify pure numeric years
    numeric_year = pd.to_numeric(
        balance["year_raw"],
        errors="coerce"
    )

    is_numeric_year = (
        numeric_year.notna()
        & numeric_year.between(2000, 2030)
    )

    # Keep March records OR clean numeric annual records
    balance = balance[
        is_march | is_numeric_year
    ].copy()

    # =========================================================
    # 6. Extract actual year
    # =========================================================

    balance["year"] = (
        balance["year_raw"]
        .str.extract(r"(\d{4})")[0]
    )

    # For pure numeric values where regex extraction
    # may not work correctly
    balance["year"] = balance["year"].fillna(
        numeric_year.astype("Int64").astype(str)
    )

    balance["year"] = pd.to_numeric(
        balance["year"],
        errors="coerce"
    )

    balance = balance[
        balance["year"].notna()
    ].copy()

    balance["year"] = (
        balance["year"]
        .astype(int)
    )

    # Remove temporary column
    balance.drop(
        columns=["year_raw"],
        inplace=True
    )

    # =========================================================
    # 7. Clean P&L years
    # =========================================================

    pnl["year"] = pd.to_numeric(
        pnl["year"],
        errors="coerce"
    )

    pnl = pnl[
        pnl["year"].notna()
    ].copy()

    pnl["year"] = pnl["year"].astype(int)

    # =========================================================
    # 8. Clean Cash Flow years
    # =========================================================

    cashflow["year"] = pd.to_numeric(
        cashflow["year"],
        errors="coerce"
    )

    cashflow = cashflow[
        cashflow["year"].notna()
    ].copy()

    cashflow["year"] = cashflow["year"].astype(int)

    # =========================================================
    # 9. Remove exact duplicates
    # =========================================================

    pnl_before = len(pnl)
    balance_before = len(balance)
    cashflow_before = len(cashflow)

    pnl = pnl.drop_duplicates()
    balance = balance.drop_duplicates()
    cashflow = cashflow.drop_duplicates()

    print("\nDuplicates removed:")

    print(
        f"P&L: {pnl_before - len(pnl)}"
    )

    print(
        f"Balance Sheet exact duplicates: "
        f"{balance_before - len(balance)}"
    )

    print(
        f"Cash Flow: "
        f"{cashflow_before - len(cashflow)}"
    )

    # =========================================================
    # 10. Remove repeated P&L financial records
    # =========================================================

    pnl_before_repeat = len(pnl)

    pnl_duplicate_columns = [
        "company_id",
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
    ]

    pnl = pnl.drop_duplicates(
        subset=pnl_duplicate_columns,
        keep="first",
    )

    print(
        f"P&L repeated financial records: "
        f"{pnl_before_repeat - len(pnl)}"
    )

    # =========================================================
    # 11. Remove repeated Balance Sheet records
    # =========================================================

    balance_before_repeat = len(balance)

    balance_duplicate_columns = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
        "total_liabilities",
        "fixed_assets",
        "cwip",
        "investments",
        "other_asset",
        "total_assets",
    ]

    balance = balance.drop_duplicates(
        subset=balance_duplicate_columns,
        keep="first",
    )

    print(
        f"Balance Sheet repeated financial records: "
        f"{balance_before_repeat - len(balance)}"
    )

    # =========================================================
    # 12. Remove repeated Cash Flow records
    # =========================================================

    cashflow_before_repeat = len(cashflow)

    cashflow_duplicate_columns = [
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    cashflow = cashflow.drop_duplicates(
        subset=cashflow_duplicate_columns,
        keep="first",
    )

    print(
        f"Cash Flow repeated financial records: "
        f"{cashflow_before_repeat - len(cashflow)}"
    )

    # =========================================================
    # 13. Resolve Balance Sheet company-year duplicates
    # =========================================================

    # First check duplicates
    duplicate_check = (
        balance
        .groupby(["company_id", "year"])
        .size()
        .reset_index(name="count")
    )

    remaining_duplicates = duplicate_check[
        duplicate_check["count"] > 1
    ]

    if not remaining_duplicates.empty:

        print(
            "\nBalance Sheet company-year duplicates "
            "found. Keeping first financial record."
        )

        print(
            f"Duplicate company-year groups: "
            f"{len(remaining_duplicates)}"
        )

        balance = balance.drop_duplicates(
            subset=["company_id", "year"],
            keep="first",
        )

    print(
        "Balance Sheet company-year records resolved."
    )

        # =========================================================
    # 13. Resolve Balance Sheet company-year duplicates
    # =========================================================

    duplicate_check = (
        balance
        .groupby(["company_id", "year"])
        .size()
        .reset_index(name="count")
    )

    remaining_duplicates = duplicate_check[
        duplicate_check["count"] > 1
    ]

    if not remaining_duplicates.empty:

        print(
            "\nBalance Sheet company-year duplicates "
            "found. Keeping first financial record."
        )

        print(
            f"Duplicate company-year groups: "
            f"{len(remaining_duplicates)}"
        )

        balance = balance.drop_duplicates(
            subset=["company_id", "year"],
            keep="first",
        )

    print(
        "Balance Sheet company-year records resolved."
    )

    # =========================================================
    # 14. Resolve Cash Flow company-year duplicates
    # =========================================================

    cashflow_duplicate_check = (
        cashflow
        .groupby(["company_id", "year"])
        .size()
        .reset_index(name="count")
    )

    cashflow_remaining_duplicates = cashflow_duplicate_check[
        cashflow_duplicate_check["count"] > 1
    ]

    if not cashflow_remaining_duplicates.empty:

        print(
            "\nCash Flow company-year duplicates "
            "found. Keeping first financial record."
        )

        print(
            f"Duplicate company-year groups: "
            f"{len(cashflow_remaining_duplicates)}"
        )

        cashflow = cashflow.drop_duplicates(
            subset=["company_id", "year"],
            keep="first",
        )

        print(
        "Cash Flow company-year records resolved."
    )

    # =========================================================
    # 15. Final duplicate validation
    # =========================================================

    balance_final_duplicates = (
        balance
        .duplicated(["company_id", "year"])
        .sum()
    )

    cashflow_final_duplicates = (
        cashflow
        .duplicated(["company_id", "year"])
        .sum()
    )

    if balance_final_duplicates > 0:
        raise ValueError(
            "Balance Sheet still contains duplicate "
            "(company_id, year) records."
        )

    if cashflow_final_duplicates > 0:
        raise ValueError(
            "Cash Flow still contains duplicate "
            "(company_id, year) records."
        )

    print(
        "\nFinal Balance Sheet duplicate "
        "company-year records:",
        balance_final_duplicates
    )

    print(
        "Final Cash Flow duplicate "
        "company-year records:",
        cashflow_final_duplicates
    )

    # =========================================================
    # 16. Missing official companies
    # =========================================================

    pnl_missing = (
        official_companies
        - set(pnl["company_id"])
    )

    balance_missing = (
        official_companies
        - set(balance["company_id"])
    )

    cashflow_missing = (
        official_companies
        - set(cashflow["company_id"])
    )

    # =========================================================
    # 17. Final statistics
    # =========================================================

    print("\nFinal statistics:")

    print(
        f"P&L rows: {len(pnl)}"
    )

    print(
        f"Balance Sheet rows: {len(balance)}"
    )

    print(
        f"Cash Flow rows: {len(cashflow)}"
    )

    print(
        f"P&L companies: "
        f"{pnl['company_id'].nunique()}"
    )

    print(
        f"Balance companies: "
        f"{balance['company_id'].nunique()}"
    )

    print(
        f"Cash Flow companies: "
        f"{cashflow['company_id'].nunique()}"
    )

    # =========================================================
    # 18. Missing companies
    # =========================================================

    print("\nMissing official companies:")

    print(
        "P&L:",
        sorted(pnl_missing)
    )

    print(
        "Balance Sheet:",
        sorted(balance_missing)
    )

    print(
        "Cash Flow:",
        sorted(cashflow_missing)
    )

    # =========================================================
    # 19. Year coverage
    # =========================================================

    print("\nBalance Sheet year coverage:")

    print(
        balance.groupby("year")["company_id"]
        .nunique()
    )

    # =========================================================
    # 20. SIEMENS check
    # =========================================================

    print("\nSIEMENS Balance Sheet records:")

    siemens = balance[
        balance["company_id"] == "SIEMENS"
    ]

    if siemens.empty:
        print("No SIEMENS records found.")
    else:
        print(
            siemens.to_string(index=False)
        )

    


if __name__ == "__main__":
    prepare_ratio_data()