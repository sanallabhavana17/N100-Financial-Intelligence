from pathlib import Path
import sqlite3
import pandas as pd

from src.etl.loader import load_all_files


DB_PATH = Path("data/nifty100.db")
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("output")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Raw Excel files
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


# Cleaned financial datasets
PROCESSED_FILES = {
    "profitandloss": "profitandloss_cleaned.csv",
    "balancesheet": "balancesheet_cleaned.csv",
    "cashflow": "cashflow_cleaned.csv",
}


# Parent tables first, child tables afterwards.
LOAD_ORDER = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "financial_ratios",
    "market_cap",
    "peer_groups",
]


def clean_dataframe(df):
    """Apply database-loading normalization."""

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
    if "id" in df.columns and "company_id" not in df.columns:
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


def load_data():

    print("\nLoading raw Excel files...")

    raw_data = load_all_files()

    datasets = {}

    # ---------------------------------------------------------
    # 1. Raw datasets
    # ---------------------------------------------------------
    for filename in RAW_FILES:

        table_name = Path(filename).stem

        df = raw_data[filename]

        datasets[table_name] = clean_dataframe(df)

    # ---------------------------------------------------------
    # 2. Cleaned financial datasets
    # ---------------------------------------------------------
    for table_name, filename in PROCESSED_FILES.items():

        path = PROCESSED_DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Required processed file not found: {path}"
            )

        df = pd.read_csv(path)

        datasets[table_name] = clean_dataframe(df)

    # ---------------------------------------------------------
    # 3. Official company IDs
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 4. Filter invalid foreign-key records
    # ---------------------------------------------------------
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
            df["company_id"].isin(official_companies)
        ].copy()

        removed = before - len(df)

        datasets[table_name] = df

        if removed > 0:
            print(
                f"{table_name}: removed "
                f"{removed} invalid company records"
            )

    # ---------------------------------------------------------
    # 5. Normalize and deduplicate financial ratios
    # ---------------------------------------------------------
    ratios = datasets["financial_ratios"].copy()

    if "year" in ratios.columns:

        # Convert values such as "Mar 2014" -> 2014
        ratios["year"] = (
            ratios["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0]
        )

        ratios["year"] = pd.to_numeric(
            ratios["year"],
            errors="coerce"
        )

    before = len(ratios)

    # Keep first record for each company-year.
    ratios = ratios.drop_duplicates(
        subset=["company_id", "year"],
        keep="first"
    ).copy()

    removed = before - len(ratios)

    datasets["financial_ratios"] = ratios

    print(
        f"financial_ratios: removed "
        f"{removed} duplicate company-year records"
    )

    # ---------------------------------------------------------
    # 6. Remove invalid company IDs from ratios
    # ---------------------------------------------------------
    before = len(ratios)

    ratios = ratios[
        ratios["company_id"].isin(official_companies)
    ].copy()

    removed = before - len(ratios)

    datasets["financial_ratios"] = ratios

    if removed > 0:
        print(
            f"financial_ratios: removed "
            f"{removed} invalid company records"
        )

    return datasets


def reset_database(conn):
    """
    Clear existing database tables before reloading.

    This prevents duplicate rows from previous runs.
    """

    print("\nClearing existing database data...")

    # Child tables first because of foreign keys.
    for table_name in reversed(LOAD_ORDER):

        try:
            conn.execute(
                f"DELETE FROM [{table_name}]"
            )
        except sqlite3.OperationalError:
            pass

    conn.commit()

    print("Existing data cleared.")


def main():

    print("\n========================================")
    print("NIFTY100 DATABASE LOAD")
    print("========================================\n")

    datasets = load_data()

    # ---------------------------------------------------------
    # Open SQLite database
    # ---------------------------------------------------------
    conn = sqlite3.connect(DB_PATH)

    # SQLite foreign keys are connection-specific.
    conn.execute("PRAGMA foreign_keys = ON")

    fk_status = conn.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    print("Foreign keys:", fk_status)

    if fk_status != 1:
        raise RuntimeError(
            "SQLite foreign keys could not be enabled."
        )

    # ---------------------------------------------------------
    # Clear previous data
    # ---------------------------------------------------------
    reset_database(conn)

    audit = []

    # ---------------------------------------------------------
    # Load tables
    # ---------------------------------------------------------
    for table_name in LOAD_ORDER:

        df = datasets[table_name]

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

            conn.rollback()

            rejected_rows = source_rows
            status = "FAILED"
            message = str(exc)

            print(
                f"  ERROR: {message}"
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

    # ---------------------------------------------------------
    # Foreign key validation
    # ---------------------------------------------------------
    fk_errors = list(
        conn.execute("PRAGMA foreign_key_check")
    )

    print("\n========================================")
    print("FOREIGN KEY CHECK")
    print("========================================")

    if fk_errors:
        print("FAILED")

        for error in fk_errors:
            print(error)

    else:
        print("PASSED - 0 violations")

    # ---------------------------------------------------------
    # Save audit
    # ---------------------------------------------------------
    audit_path = OUTPUT_DIR / "load_audit.csv"

    pd.DataFrame(audit).to_csv(
        audit_path,
        index=False
    )

    print("\n========================================")
    print("LOAD AUDIT")
    print("========================================")

    print(
        pd.DataFrame(audit).to_string(index=False)
    )

    print(
        f"\nAudit saved to: {audit_path}"
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()