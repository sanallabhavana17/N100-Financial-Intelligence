from pathlib import Path

import sqlite3
import pandas as pd

from src.etl.loader import load_all_files


# ==========================================================
# PATHS
# ==========================================================

DB_PATH = Path("data/nifty100.db")
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("output")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================================
# RAW EXCEL FILES
# ==========================================================

RAW_FILES = [
    "companies.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx",
    "sectors.xlsx",
    "stock_prices.xlsx",
    "financial_ratios.xlsx",
    "market_cap.xlsx",
    "peer_groups.xlsx",
]


# ==========================================================
# CLEANED FINANCIAL DATASETS
# ==========================================================

PROCESSED_FILES = {
    "profitandloss": "profitandloss_cleaned.csv",
    "balancesheet": "balancesheet_cleaned.csv",
    "cashflow": "cashflow_cleaned.csv",
}


# ==========================================================
# ANALYTICS OUTPUT FILES
# ==========================================================

ANALYTICS_FILES = {
    "profitability": OUTPUT_DIR / "profitability_ratios.csv",
    "leverage": OUTPUT_DIR / "leverage_efficiency_ratios.csv",
    "cashflow": OUTPUT_DIR / "cashflow_kpis.csv",
    "cagr": OUTPUT_DIR / "cagr_ratios.csv",
}


# ==========================================================
# FINAL financial_ratios COLUMNS
#
# These are the 46 data columns.
# SQLite adds the "id" primary key automatically.
# ==========================================================

FINANCIAL_RATIOS_COLUMNS = [
    "company_id",
    "year",

    # Profitability
    "net_profit_margin_pct",
    "operating_profit_margin_pct",
    "return_on_equity_pct",
    "return_on_capital_employed_pct",
    "return_on_assets_pct",

    # Leverage & Efficiency
    "debt_to_equity",
    "high_leverage_flag",
    "interest_coverage",
    "icr_label",
    "icr_warning_flag",
    "net_debt_cr",
    "asset_turnover",

    # Cash Flow
    "free_cash_flow_cr",
    "capex_cr",
    "cash_from_operations_cr",
    "cfo_quality_ratio",
    "cfo_quality_label",
    "capex_intensity_pct",
    "capex_intensity_label",
    "fcf_conversion_pct",
    "capital_allocation_pattern",

    # Per-share / shareholder metrics
    "earnings_per_share",
    "book_value_per_share",
    "dividend_payout_ratio_pct",
    "total_debt_cr",

    # Revenue CAGR
    "revenue_cagr_3yr",
    "revenue_cagr_3yr_flag",
    "revenue_cagr_5yr",
    "revenue_cagr_5yr_flag",
    "revenue_cagr_10yr",
    "revenue_cagr_10yr_flag",

    # PAT CAGR
    "pat_cagr_3yr",
    "pat_cagr_3yr_flag",
    "pat_cagr_5yr",
    "pat_cagr_5yr_flag",
    "pat_cagr_10yr",
    "pat_cagr_10yr_flag",

    # EPS CAGR
    "eps_cagr_3yr",
    "eps_cagr_3yr_flag",
    "eps_cagr_5yr",
    "eps_cagr_5yr_flag",
    "eps_cagr_10yr",
    "eps_cagr_10yr_flag",

    # Quality
    "composite_quality_score",
]


# ==========================================================
# LOAD ORDER
# ==========================================================

# Parent tables first, child tables afterwards.
LOAD_ORDER = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
    "peer_groups",
]


# ==========================================================
# BASIC DATAFRAME CLEANING
# ==========================================================

def clean_dataframe(df):
    """
    Apply common database-loading normalization.
    """

    df = df.copy()

    # Normalize column names
    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]

    # Normalize company IDs
    if "company_id" in df.columns:
        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # companies.id is the primary key
    if (
        "id" in df.columns
        and "company_id" not in df.columns
    ):
        df["id"] = (
            df["id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # Normalize year
    if "year" in df.columns:
        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce"
        )

    return df


# ==========================================================
# NORMALIZE COMPANY-YEAR KEY
# ==========================================================

def normalize_company_year(df):
    """
    Normalize company_id and year so that all analytics
    datasets can be safely merged.
    """

    df = df.copy()

    if "company_id" in df.columns:
        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if "year" in df.columns:

        # Handles:
        # 2014
        # 2014.0
        # Mar 2014
        # Dec 2012
        df["year"] = (
            df["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0]
        )

        df["year"] = pd.to_numeric(
            df["year"],
            errors="coerce"
        )

    return df


# ==========================================================
# PREPARE ANALYTICS DATASET
# ==========================================================

def prepare_analytics_file(
    path,
    required_columns,
    dataset_name,
):
    """
    Load and normalize one analytics CSV.

    Only columns that actually exist are retained.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Missing analytics file: {path}"
        )

    df = pd.read_csv(path)

    df = normalize_company_year(df)

    required_key_columns = [
        "company_id",
        "year",
    ]

    missing_keys = [
        col
        for col in required_key_columns
        if col not in df.columns
    ]

    if missing_keys:
        raise ValueError(
            f"{dataset_name} is missing required "
            f"columns: {missing_keys}"
        )

    available_columns = [
        col
        for col in required_columns
        if col in df.columns
    ]

    df = df[
        available_columns
    ].copy()

    df = df.dropna(
        subset=[
            "company_id",
            "year",
        ]
    ).copy()

    df["year"] = df["year"].astype(int)

    # One record per company-year
    df = df.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="first"
    ).copy()

    return df


# ==========================================================
# BUILD FINAL FINANCIAL RATIOS
# ==========================================================

def build_final_financial_ratios(datasets):
    """
    Build the final financial_ratios table.

    IMPORTANT DESIGN:

    The row universe is built from the calculated analytics
    datasets rather than financial_ratios.xlsx.

    financial_ratios.xlsx is used only for supplementary
    per-share/shareholder fields.

    This allows companies such as ATGL and SBIN to remain
    in the final table even when the raw financial-ratios
    workbook does not contain them.

    Final output:
        46 data columns + SQLite id primary key.
    """

    print(
        "\nBuilding final financial_ratios table..."
    )

    # ------------------------------------------------------
    # 1. OFFICIAL COMPANIES
    # ------------------------------------------------------

    companies = datasets["companies"].copy()

    official_companies = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    print(
        "Official companies:",
        len(official_companies)
    )

    if len(official_companies) != 92:
        raise ValueError(
            "Expected 92 official companies, "
            f"found {len(official_companies)}."
        )

    # ------------------------------------------------------
    # 2. PROFITABILITY ANALYTICS
    # ------------------------------------------------------

    profitability = prepare_analytics_file(
        ANALYTICS_FILES["profitability"],
        [
            "company_id",
            "year",
            "net_profit_margin_pct",
            "operating_profit_margin_pct",
            "roe_pct",
            "roce_pct",
            "roa_pct",
        ],
        "profitability_ratios.csv",
    )

    profitability = profitability.rename(
        columns={
            "roe_pct":
                "return_on_equity_pct",

            "roce_pct":
                "return_on_capital_employed_pct",

            "roa_pct":
                "return_on_assets_pct",
        }
    )

    # Keep official companies only
    profitability = profitability[
        profitability["company_id"].isin(
            official_companies
        )
    ].copy()

    # ------------------------------------------------------
    # 3. LEVERAGE / EFFICIENCY ANALYTICS
    # ------------------------------------------------------

    leverage = prepare_analytics_file(
        ANALYTICS_FILES["leverage"],
        [
            "company_id",
            "year",
            "debt_to_equity",
            "high_leverage_flag",
            "interest_coverage",
            "icr_label",
            "icr_warning_flag",
            "net_debt_cr",
            "asset_turnover",
        ],
        "leverage_efficiency_ratios.csv",
    )

    leverage = leverage[
        leverage["company_id"].isin(
            official_companies
        )
    ].copy()

    # ------------------------------------------------------
    # 4. CASH-FLOW ANALYTICS
    # ------------------------------------------------------

    cashflow = prepare_analytics_file(
        ANALYTICS_FILES["cashflow"],
        [
            "company_id",
            "year",
            "free_cash_flow",
            "cfo_quality_ratio",
            "cfo_quality_label",
            "capex_intensity_pct",
            "capex_intensity_label",
            "fcf_conversion_pct",
            "capital_allocation_pattern",
        ],
        "cashflow_kpis.csv",
    )

    cashflow = cashflow.rename(
        columns={
            "free_cash_flow":
                "free_cash_flow_cr",
        }
    )

    cashflow = cashflow[
        cashflow["company_id"].isin(
            official_companies
        )
    ].copy()

    # ------------------------------------------------------
    # 5. RAW CASH-FLOW FIELDS
    # ------------------------------------------------------

    raw_cashflow = datasets[
        "cashflow"
    ].copy()

    raw_cashflow = normalize_company_year(
        raw_cashflow
    )

    raw_cashflow = raw_cashflow[
        raw_cashflow["company_id"].isin(
            official_companies
        )
    ].copy()

    # We need source fields for:
    # capex_cr
    # cash_from_operations_cr

    raw_cf_columns = [
        "company_id",
        "year",
    ]

    for column in [
        "capex",
        "cfo",
        "cash_from_operations",
    ]:
        if column in raw_cashflow.columns:
            raw_cf_columns.append(column)

    raw_cf = raw_cashflow[
        raw_cf_columns
    ].copy()

    raw_cf = raw_cf.dropna(
        subset=[
            "company_id",
            "year",
        ]
    ).copy()

    raw_cf["year"] = raw_cf[
        "year"
    ].astype(int)

    # Rename source columns
    rename_map = {}

    if "capex" in raw_cf.columns:
        rename_map["capex"] = "capex_cr"

    if "cfo" in raw_cf.columns:
        rename_map["cfo"] = (
            "cash_from_operations_cr"
        )

    if "cash_from_operations" in raw_cf.columns:
        rename_map[
            "cash_from_operations"
        ] = "cash_from_operations_cr"

    raw_cf = raw_cf.rename(
        columns=rename_map
    )

    # If both cfo and cash_from_operations existed,
    # remove duplicate target column names safely.
    if raw_cf.columns.duplicated().any():
        raw_cf = raw_cf.loc[
            :,
            ~raw_cf.columns.duplicated()
        ]

    raw_cf = raw_cf.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="first"
    )

    # Merge raw cash-flow values into cashflow analytics
    cashflow = cashflow.merge(
        raw_cf,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    # ------------------------------------------------------
    # 6. CAGR ANALYTICS
    # ------------------------------------------------------

    cagr = prepare_analytics_file(
        ANALYTICS_FILES["cagr"],
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
            "pat_cagr_3yr_flag",
            "pat_cagr_5yr",
            "pat_cagr_5yr_flag",
            "pat_cagr_10yr",
            "pat_cagr_10yr_flag",

            "eps_cagr_3yr",
            "eps_cagr_3yr_flag",
            "eps_cagr_5yr",
            "eps_cagr_5yr_flag",
            "eps_cagr_10yr",
            "eps_cagr_10yr_flag",
        ],
        "cagr_ratios.csv",
    )

    cagr = cagr[
        cagr["company_id"].isin(
            official_companies
        )
    ].copy()

    # ------------------------------------------------------
    # 7. RAW FINANCIAL-RATIO SUPPLEMENTARY FIELDS
    # ------------------------------------------------------
    #
    # financial_ratios.xlsx is NOT the base anymore.
    #
    # It only supplies fields which aren't generated by
    # the analytics modules:
    #
    # earnings_per_share
    # book_value_per_share
    # dividend_payout_ratio_pct
    # total_debt_cr
    #

    raw_ratios = datasets[
        "financial_ratios"
    ].copy()

    raw_ratios = normalize_company_year(
        raw_ratios
    )

    raw_ratios = raw_ratios[
        raw_ratios["company_id"].isin(
            official_companies
        )
    ].copy()

    raw_ratio_columns = [
        "company_id",
        "year",
        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",
        "total_debt_cr",
    ]

    raw_ratio_columns = [
        col
        for col in raw_ratio_columns
        if col in raw_ratios.columns
    ]

    raw_ratios = raw_ratios[
        raw_ratio_columns
    ].copy()

    raw_ratios = raw_ratios.dropna(
        subset=[
            "company_id",
            "year",
        ]
    ).copy()

    raw_ratios["year"] = raw_ratios[
        "year"
    ].astype(int)

    # One raw ratio record per company-year
    raw_ratios = raw_ratios.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="first"
    ).copy()

    # ------------------------------------------------------
    # 8. BUILD ROW UNIVERSE
    # ------------------------------------------------------
    #
    # IMPORTANT:
    #
    # We create the row universe from ALL analytics files.
    #
    # This is what fixes the ATGL/SBIN problem.
    #

    key_frames = []

    for df in [
        profitability,
        leverage,
        cashflow,
        cagr,
    ]:

        keys = df[
            [
                "company_id",
                "year",
            ]
        ].copy()

        key_frames.append(keys)

    key_universe = pd.concat(
        key_frames,
        ignore_index=True,
    )

    key_universe = key_universe[
        key_universe["company_id"].isin(
            official_companies
        )
    ].copy()

    key_universe = key_universe.dropna(
        subset=[
            "company_id",
            "year",
        ]
    ).copy()

    key_universe["year"] = key_universe[
        "year"
    ].astype(int)

    key_universe = key_universe.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="first"
    ).copy()

    print(
        "Analytics company-year universe:",
        len(key_universe)
    )

    print(
        "Analytics companies:",
        key_universe["company_id"].nunique()
    )

    # ------------------------------------------------------
    # 9. MERGE ALL ANALYTICS
    # ------------------------------------------------------

    final = key_universe.copy()

    final = final.merge(
        profitability,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    final = final.merge(
        leverage,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    final = final.merge(
        cashflow,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    final = final.merge(
        cagr,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    final = final.merge(
        raw_ratios,
        on=[
            "company_id",
            "year",
        ],
        how="left",
    )

    # ------------------------------------------------------
    # 10. ENSURE ALL REQUIRED DATABASE COLUMNS EXIST
    # ------------------------------------------------------

    for column in FINANCIAL_RATIOS_COLUMNS:

        if column not in final.columns:
            final[column] = None

    # ------------------------------------------------------
    # 11. KEEP EXACT DATABASE COLUMN ORDER
    # ------------------------------------------------------

    final = final[
        FINANCIAL_RATIOS_COLUMNS
    ].copy()

    # ------------------------------------------------------
    # 12. FINAL DUPLICATE CHECK
    # ------------------------------------------------------

    final = final.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="first",
    ).copy()

    duplicate_count = final.duplicated(
        subset=[
            "company_id",
            "year",
        ]
    ).sum()

    # ------------------------------------------------------
    # 13. FINAL COMPANY VALIDATION
    # ------------------------------------------------------

    final_companies = set(
        final["company_id"]
        .dropna()
        .astype(str)
        .str.upper()
    )

    missing_companies = sorted(
        official_companies - final_companies
    )

    extra_companies = sorted(
        final_companies - official_companies
    )

    company_count = final[
        "company_id"
    ].nunique()

    # ------------------------------------------------------
    # 14. REPORT
    # ------------------------------------------------------

    print(
        "\nFinal financial_ratios:"
    )

    print(
        "Rows:",
        len(final)
    )

    print(
        "Companies:",
        company_count
    )

    print(
        "Columns:",
        len(final.columns)
    )

    print(
        "Company-year duplicates:",
        duplicate_count
    )

    if missing_companies:
        print(
            "Missing official companies:",
            missing_companies
        )

    if extra_companies:
        print(
            "Unexpected companies:",
            extra_companies
        )

    # Duplicate company-year records are never allowed.
    if duplicate_count != 0:
        raise ValueError(
            "Final financial_ratios contains "
            "company-year duplicates."
        )

    # Every official company should ideally appear.
    if company_count != len(official_companies):
        print(
            "WARNING: Expected "
            f"{len(official_companies)} companies, "
            f"found {company_count}."
        )

    return final


# ==========================================================
# LOAD ALL DATA
# ==========================================================

def load_data():

    print(
        "\nLoading raw Excel files..."
    )

    raw_data = load_all_files()

    datasets = {}

    # ------------------------------------------------------
    # 1. RAW DATASETS
    # ------------------------------------------------------

    for filename in RAW_FILES:

        table_name = Path(
            filename
        ).stem

        datasets[table_name] = (
            clean_dataframe(
                raw_data[filename]
            )
        )

    # ------------------------------------------------------
    # 2. CLEANED FINANCIAL DATASETS
    # ------------------------------------------------------

    for table_name, filename in PROCESSED_FILES.items():

        path = PROCESSED_DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Required processed file not found: "
                f"{path}"
            )

        df = pd.read_csv(path)

        datasets[table_name] = (
            clean_dataframe(df)
        )

    # ------------------------------------------------------
    # 3. OFFICIAL COMPANY IDs
    # ------------------------------------------------------

    official_companies = set(
        datasets["companies"]["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    print(
        f"\nOfficial companies: "
        f"{len(official_companies)}"
    )

    # ------------------------------------------------------
    # 4. FILTER INVALID FOREIGN-KEY RECORDS
    # ------------------------------------------------------

    fk_tables = [
        "analysis",
        "documents",
        "prosandcons",
    ]

    for table_name in fk_tables:

        df = datasets[table_name]

        if "company_id" not in df.columns:
            continue

        before = len(df)

        df = df[
            df["company_id"].isin(
                official_companies
            )
        ].copy()

        removed = before - len(df)

        datasets[table_name] = df

        if removed > 0:
            print(
                f"{table_name}: removed "
                f"{removed} invalid company records"
            )

    # ------------------------------------------------------
    # 5. NORMALIZE FINANCIAL RATIOS SOURCE
    # ------------------------------------------------------

    ratios = datasets[
        "financial_ratios"
    ].copy()

    ratios = normalize_company_year(
        ratios
    )

    # Keep only official companies
    ratios = ratios[
        ratios["company_id"].isin(
            official_companies
        )
    ].copy()

    # Remove invalid years
    ratios = ratios.dropna(
        subset=[
            "company_id",
            "year",
        ]
    ).copy()

    ratios["year"] = ratios[
        "year"
    ].astype(int)

    before = len(ratios)

    # Raw ratio workbook can contain multiple rows
    # for the same company-year.
    ratios = ratios.drop_duplicates(
        subset=[
            "company_id",
            "year",
        ],
        keep="first",
    ).copy()

    removed = before - len(ratios)

    datasets[
        "financial_ratios"
    ] = ratios

    print(
        f"financial_ratios: removed "
        f"{removed} duplicate company-year records"
    )

    return datasets


# ==========================================================
# RESET DATABASE
# ==========================================================

def reset_database(conn):

    """
    Clear existing database tables before reloading.

    Child tables are cleared first because foreign keys
    are enabled.
    """

    print(
        "\nClearing existing database data..."
    )

    for table_name in reversed(
        LOAD_ORDER
    ):

        try:
            conn.execute(
                f"DELETE FROM [{table_name}]"
            )

        except sqlite3.OperationalError:
            # Allows the loader to work if a table does not
            # exist yet.
            pass

    conn.commit()

    print(
        "Existing data cleared."
    )


# ==========================================================
# MAIN DATABASE LOADER
# ==========================================================

def main():

    print(
        "\n========================================"
    )

    print(
        "NIFTY100 DATABASE LOAD"
    )

    print(
        "========================================\n"
    )

    # ------------------------------------------------------
    # Load source data
    # ------------------------------------------------------

    datasets = load_data()

    # ------------------------------------------------------
    # Build final financial_ratios FIRST
    # ------------------------------------------------------

    final_financial_ratios = (
        build_final_financial_ratios(
            datasets
        )
    )

    datasets[
        "financial_ratios"
    ] = final_financial_ratios

    # ------------------------------------------------------
    # Open SQLite database
    # ------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    # SQLite foreign keys are connection-specific.
    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    fk_status = conn.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    print(
        "Foreign keys:",
        fk_status
    )

    if fk_status != 1:
        conn.close()

        raise RuntimeError(
            "SQLite foreign keys could not "
            "be enabled."
        )

    # ------------------------------------------------------
    # Clear previous data
    # ------------------------------------------------------

    reset_database(
        conn
    )

    audit = []

    # ------------------------------------------------------
    # Load tables
    # ------------------------------------------------------

    for table_name in LOAD_ORDER:

        df = datasets[
            table_name
        ]

        source_rows = len(df)

        loaded_rows = 0
        rejected_rows = 0

        status = "OK"
        message = ""

        print(
            f"Loading {table_name:<20} "
            f"rows={source_rows}"
        )

        try:

            df.to_sql(
                table_name,
                conn,
                if_exists="append",
                index=False,
            )

            loaded_rows = len(df)

        except Exception as exc:

            status = "FAILED"

            message = str(exc)

            # Roll back this failed transaction.
            conn.rollback()

            print(
                f"ERROR loading "
                f"{table_name}: "
                f"{exc}"
            )

        audit.append(
            {
                "table": table_name,
                "source_rows": source_rows,
                "loaded_rows": loaded_rows,
                "rejected_rows": rejected_rows,
                "status": status,
                "message": message,
            }
        )

        if status == "FAILED":
            conn.close()

            raise RuntimeError(
                f"Database load failed for "
                f"table: {table_name}"
            )

    # ------------------------------------------------------
    # Foreign-key validation
    # ------------------------------------------------------

    print(
        "\n========================================"
    )

    print(
        "FOREIGN KEY CHECK"
    )

    print(
        "========================================"
    )

    violations = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if violations:

        print(
            f"FAILED - "
            f"{len(violations)} violations"
        )

        for violation in violations[:20]:
            print(
                violation
            )

        conn.close()

        raise ValueError(
            "Foreign-key validation failed."
        )

    print(
        "PASSED - 0 violations"
    )

    # ------------------------------------------------------
    # Save audit
    # ------------------------------------------------------

    audit_df = pd.DataFrame(
        audit
    )

    audit_path = (
        OUTPUT_DIR /
        "load_audit.csv"
    )

    audit_df.to_csv(
        audit_path,
        index=False,
    )

    # ------------------------------------------------------
    # Audit display
    # ------------------------------------------------------

    print(
        "\n========================================"
    )

    print(
        "LOAD AUDIT"
    )

    print(
        "========================================"
    )

    print(
        audit_df.to_string(
            index=False
        )
    )

    print(
        f"\nAudit saved to: "
        f"{audit_path}"
    )

    # ------------------------------------------------------
    # Close database
    # ------------------------------------------------------

    conn.commit()
    conn.close()


# ==========================================================
# ENTRY POINT
# ==========================================================

if __name__ == "__main__":
    main()