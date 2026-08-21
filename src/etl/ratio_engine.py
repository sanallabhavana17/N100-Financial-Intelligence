from pathlib import Path

import numpy as np
import pandas as pd


PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def safe_divide(numerator, denominator):
    """
    Safely divide numerator by denominator.

    Returns NaN when denominator is zero or missing.
    """
    return np.where(
        denominator.notna() & (denominator != 0),
        numerator / denominator,
        np.nan,
    )


def prepare_cashflow(cashflow):
    """
    Make Cash Flow unique at company-year level.

    Some source records contain multiple cash-flow rows
    for the same company and year. Aggregate them so that
    the Ratio Engine does not create duplicate rows.
    """

    cashflow = cashflow.copy()

    duplicate_count = cashflow.duplicated(
        subset=["company_id", "year"]
    ).sum()

    print(
        f"Cash Flow duplicate company-year rows before "
        f"aggregation: {duplicate_count}"
    )

    cashflow = (
        cashflow
        .groupby(
            ["company_id", "year"],
            as_index=False
        )[
            [
                "operating_activity",
                "investing_activity",
                "financing_activity",
                "net_cash_flow",
            ]
        ]
        .sum(min_count=1)
    )

    remaining = cashflow.duplicated(
        subset=["company_id", "year"]
    ).sum()

    if remaining > 0:
        raise ValueError(
            "Cash Flow still contains duplicate "
            "(company_id, year) records."
        )

    print(
        f"Cash Flow rows after company-year aggregation: "
        f"{len(cashflow)}"
    )

    return cashflow


def calculate_ratios():

    # =========================================================
    # 1. Load cleaned datasets
    # =========================================================

    pnl = pd.read_csv(
        PROCESSED_DIR / "profitandloss_cleaned.csv"
    )

    balance = pd.read_csv(
        PROCESSED_DIR / "balancesheet_cleaned.csv"
    )

    cashflow = pd.read_csv(
        PROCESSED_DIR / "cashflow_cleaned.csv"
    )

    print("Cleaned datasets loaded successfully.")

    print(f"P&L rows: {len(pnl)}")
    print(f"Balance Sheet rows: {len(balance)}")
    print(f"Cash Flow rows: {len(cashflow)}")

    # =========================================================
    # 2. Standardize company_id and year
    # =========================================================

    for df in [pnl, balance, cashflow]:

        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
        )

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce"
        )

    # Remove rows where company/year is missing
    pnl = pnl.dropna(
        subset=["company_id", "year"]
    ).copy()

    balance = balance.dropna(
        subset=["company_id", "year"]
    ).copy()

    cashflow = cashflow.dropna(
        subset=["company_id", "year"]
    ).copy()

    # Convert year to integer
    pnl["year"] = pnl["year"].astype(int)
    balance["year"] = balance["year"].astype(int)
    cashflow["year"] = cashflow["year"].astype(int)

    # =========================================================
    # 3. Validate P&L uniqueness
    # =========================================================

    pnl_duplicates = pnl.duplicated(
        subset=["company_id", "year"]
    ).sum()

    print(
        f"P&L duplicate company-year rows: "
        f"{pnl_duplicates}"
    )

    if pnl_duplicates > 0:

        print(
            "\nWarning: P&L contains multiple records "
            "for the same company-year."
        )

        pnl = (
            pnl
            .drop_duplicates(
                subset=["company_id", "year"],
                keep="first"
            )
            .copy()
        )

    # =========================================================
    # 4. Validate Balance Sheet uniqueness
    # =========================================================

    balance_duplicates = balance.duplicated(
        subset=["company_id", "year"]
    ).sum()

    print(
        f"Balance Sheet duplicate company-year rows: "
        f"{balance_duplicates}"
    )

    if balance_duplicates > 0:

        print(
            "\nWarning: Balance Sheet contains duplicate "
            "(company_id, year) records."
        )

        balance = (
            balance
            .drop_duplicates(
                subset=["company_id", "year"],
                keep="first"
            )
            .copy()
        )

    # =========================================================
    # 5. Prepare Cash Flow
    # =========================================================

    cashflow = prepare_cashflow(cashflow)

    # =========================================================
    # 6. Select P&L columns
    # =========================================================

    pnl_required = [
        "company_id",
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "other_income",
        "interest",
        "depreciation",
        "profit_before_tax",
        "tax_percentage",
        "net_profit",
        "eps",
        "dividend_payout",
    ]

    pnl = pnl[pnl_required].copy()

    # =========================================================
    # 7. Select Balance Sheet columns
    # =========================================================

    balance_required = [
        "company_id",
        "year",
        "equity_capital",
        "reserves",
        "borrowings",
        "total_liabilities",
        "total_assets",
    ]

    balance = balance[balance_required].copy()

    # =========================================================
    # 8. Select Cash Flow columns
    # =========================================================

    cashflow_required = [
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    cashflow = cashflow[cashflow_required].copy()

    # =========================================================
    # 9. Merge P&L + Balance Sheet
    # =========================================================

    ratios = pnl.merge(
        balance,
        on=["company_id", "year"],
        how="left",
        validate="one_to_one",
    )

    print(
        f"\nAfter P&L + Balance Sheet merge: "
        f"{len(ratios)} rows"
    )

    # =========================================================
    # 10. Merge Cash Flow
    # =========================================================

    ratios = ratios.merge(
        cashflow,
        on=["company_id", "year"],
        how="left",
        validate="one_to_one",
    )

    print(
        f"After Cash Flow merge: "
        f"{len(ratios)} rows"
    )

    # =========================================================
    # 11. Calculate Shareholders' Equity
    # =========================================================

    ratios["shareholders_equity"] = (
        ratios["equity_capital"]
        + ratios["reserves"]
    )

    # =========================================================
    # 12. Operating Profit Margin
    # =========================================================

    ratios["operating_profit_margin"] = (
        safe_divide(
            ratios["operating_profit"],
            ratios["sales"],
        )
        * 100
    )

    # =========================================================
    # 13. Net Profit Margin
    # =========================================================

    ratios["net_profit_margin"] = (
        safe_divide(
            ratios["net_profit"],
            ratios["sales"],
        )
        * 100
    )

    # =========================================================
    # 14. Return on Assets
    # =========================================================

    ratios["roa"] = (
        safe_divide(
            ratios["net_profit"],
            ratios["total_assets"],
        )
        * 100
    )

    # =========================================================
    # 15. Return on Equity
    # =========================================================

    ratios["roe"] = (
        safe_divide(
            ratios["net_profit"],
            ratios["shareholders_equity"],
        )
        * 100
    )

    # =========================================================
    # 16. Debt-to-Equity
    # =========================================================

    ratios["debt_to_equity"] = safe_divide(
        ratios["borrowings"],
        ratios["shareholders_equity"],
    )

    # =========================================================
    # 17. Interest Coverage
    # =========================================================

    ratios["interest_coverage"] = safe_divide(
        ratios["operating_profit"],
        ratios["interest"],
    )

    # =========================================================
    # 18. Asset Turnover
    # =========================================================

    ratios["asset_turnover"] = safe_divide(
        ratios["sales"],
        ratios["total_assets"],
    )

    # =========================================================
    # 19. Tax Rate
    # =========================================================

    ratios["tax_rate"] = ratios["tax_percentage"]

    # =========================================================
    # 19A. Clean known invalid sentinel values
    # =========================================================

    # -99 and 99 are placeholder/invalid values
    # and should be treated as missing.
    ratios["tax_rate"] = ratios["tax_rate"].replace(
        [-99, 99],
        np.nan
    )

    # -999 is an invalid dividend payout placeholder.
    ratios["dividend_payout"] = (
        ratios["dividend_payout"]
        .replace(-999, np.nan)
    )

    # Negative EPS is valid.
    #
    # Example:
    # INDIGO 2022:
    # Net Profit = -317
    # EPS = -160
    #
    # Therefore, do NOT replace negative EPS values.

    # =========================================================
    # 20. EPS
    # =========================================================

    ratios["eps"] = ratios["eps"]

    # =========================================================
    # 21. Dividend Payout
    # =========================================================

    ratios["dividend_payout"] = ratios["dividend_payout"]

    # =========================================================
    # 22. Cash Flow indicators
    # =========================================================

    ratios["operating_cash_flow"] = (
        ratios["operating_activity"]
    )

    ratios["net_cash_flow"] = (
        ratios["net_cash_flow"]
    )

    # =========================================================
    # 23. Final columns
    # =========================================================

    final_columns = [

        "company_id",
        "year",

        # -------------------------
        # Profitability
        # -------------------------
        "operating_profit_margin",
        "net_profit_margin",
        "roa",
        "roe",

        # -------------------------
        # Leverage
        # -------------------------
        "debt_to_equity",
        "interest_coverage",

        # -------------------------
        # Efficiency
        # -------------------------
        "asset_turnover",

        # -------------------------
        # Shareholder metrics
        # -------------------------
        "tax_rate",
        "eps",
        "dividend_payout",

        # -------------------------
        # Supporting financial data
        # -------------------------
        "sales",
        "operating_profit",
        "net_profit",
        "borrowings",
        "shareholders_equity",
        "total_assets",

        # -------------------------
        # Cash Flow
        # -------------------------
        "operating_cash_flow",
        "net_cash_flow",
    ]

    ratios = ratios[final_columns].copy()

    # =========================================================
    # 24. Final duplicate validation
    # =========================================================

    final_duplicates = ratios.duplicated(
        subset=["company_id", "year"]
    ).sum()

    print(
        f"\nFinal duplicate company-year records: "
        f"{final_duplicates}"
    )

    if final_duplicates > 0:

        raise ValueError(
            "Final ratio dataset contains duplicate "
            "(company_id, year) records."
        )

    # =========================================================
    # 25. Sort
    # =========================================================

    ratios = (
        ratios
        .sort_values(
            ["company_id", "year"]
        )
        .reset_index(drop=True)
    )

    # =========================================================
    # 26. Save
    # =========================================================

    output_file = (
        PROCESSED_DIR
        / "financial_ratios_calculated.csv"
    )

    ratios.to_csv(
        output_file,
        index=False,
    )

    # =========================================================
    # 27. Final statistics
    # =========================================================

    print(
        "\nFinancial Ratio Engine completed successfully."
    )

    print(
        f"Output file: {output_file}"
    )

    print(
        f"Rows: {len(ratios)}"
    )

    print(
        f"Companies: "
        f"{ratios['company_id'].nunique()}"
    )

    print("\nRatio columns:")

    print(
        [
            "operating_profit_margin",
            "net_profit_margin",
            "roa",
            "roe",
            "debt_to_equity",
            "interest_coverage",
            "asset_turnover",
            "tax_rate",
            "eps",
            "dividend_payout",
        ]
    )

    # =========================================================
    # 28. Balance Sheet coverage
    # =========================================================

    missing_balance = sorted(
        set(pnl["company_id"])
        - set(balance["company_id"])
    )

    if missing_balance:

        print(
            "\nCompanies without Balance Sheet data:"
        )

        print(missing_balance)

    else:

        print(
            "\nAll P&L companies have Balance Sheet data."
        )

    # =========================================================
    # 29. Cash Flow coverage
    # =========================================================

    missing_cashflow = sorted(
        set(pnl["company_id"])
        - set(cashflow["company_id"])
    )

    if missing_cashflow:

        print(
            "\nCompanies without Cash Flow data:"
        )

        print(missing_cashflow)

    else:

        print(
            "All P&L companies have Cash Flow data."
        )

    # =========================================================
    # 30. Sample
    # =========================================================

    print("\nSample ratio records:")

    print(
        ratios.head(10).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    calculate_ratios()