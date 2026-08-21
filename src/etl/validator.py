from pathlib import Path

import pandas as pd

from src.etl.loader import load_all_files


OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def record_failure(
    failures,
    rule_id,
    severity,
    table_name,
    message,
):
    """Add one data-quality failure to the results."""

    failures.append(
        {
            "rule_id": rule_id,
            "severity": severity,
            "table": table_name,
            "message": message,
        }
    )


def validate_pk_uniqueness(df, table_name, failures):
    """
    DQ-01: Primary key uniqueness.

    Checks whether an 'id' column contains duplicate values.
    """

    if "id" not in df.columns:
        return

    duplicate_count = df["id"].duplicated().sum()

    if duplicate_count > 0:
        record_failure(
            failures,
            "DQ-01",
            "CRITICAL",
            table_name,
            f"{duplicate_count} duplicate primary-key values found",
        )


def validate_company_year_pk(df, table_name, failures):
    """
    DQ-02: (company_id, year) uniqueness.
    """

    if (
        "company_id" not in df.columns
        or "year" not in df.columns
    ):
        return

    duplicate_count = df.duplicated(
        subset=["company_id", "year"]
    ).sum()

    if duplicate_count > 0:
        record_failure(
            failures,
            "DQ-02",
            "CRITICAL",
            table_name,
            f"{duplicate_count} duplicate (company_id, year) records found",
        )


def run_validation():
    """
    Validate the raw source datasets.

    This checks the original files in data/raw.
    Raw duplicate records are reported here so that
    the ETL cleaning process can address them.
    """

    datasets = load_all_files()

    failures = []

    for filename, df in datasets.items():

        table_name = Path(filename).stem

        validate_pk_uniqueness(
            df,
            table_name,
            failures,
        )

        validate_company_year_pk(
            df,
            table_name,
            failures,
        )

    failures_df = pd.DataFrame(failures)

    output_file = (
        OUTPUT_DIR / "validation_failures.csv"
    )

    failures_df.to_csv(
        output_file,
        index=False,
    )

    print("\nRaw-data validation completed.")
    print(
        f"Failures found: {len(failures_df)}"
    )
    print(
        f"Output: {output_file}"
    )


def load_processed_files():
    """
    Load cleaned datasets from data/processed.
    """

    processed_dir = Path("data/processed")

    files = {
        "profitandloss_cleaned.csv":
            processed_dir / "profitandloss_cleaned.csv",

        "balancesheet_cleaned.csv":
            processed_dir / "balancesheet_cleaned.csv",

        "cashflow_cleaned.csv":
            processed_dir / "cashflow_cleaned.csv",
    }

    datasets = {}

    for filename, filepath in files.items():

        if not filepath.exists():

            print(
                f"WARNING: Missing processed file: "
                f"{filepath}"
            )

            continue

        datasets[filename] = pd.read_csv(
            filepath
        )

    return datasets


def run_processed_validation():
    """
    Validate the cleaned datasets produced by the ETL pipeline.

    The processed datasets should contain unique
    (company_id, year) records.
    """

    datasets = load_processed_files()

    failures = []

    for filename, df in datasets.items():

        table_name = Path(filename).stem

        validate_pk_uniqueness(
            df,
            table_name,
            failures,
        )

        validate_company_year_pk(
            df,
            table_name,
            failures,
        )

    failures_df = pd.DataFrame(failures)

    output_file = (
        OUTPUT_DIR
        / "processed_validation_failures.csv"
    )

    failures_df.to_csv(
        output_file,
        index=False,
    )

    print(
        "\nProcessed-data validation completed."
    )

    print(
        f"Failures found: {len(failures_df)}"
    )

    print(
        f"Output: {output_file}"
    )

    if failures:

        print(
            "\nProcessed-data failures:"
        )

        print(
            failures_df.to_string(
                index=False
            )
        )

    else:

        print(
            "All processed datasets passed validation. "
            "OK"
        )


if __name__ == "__main__":

    run_validation()

    run_processed_validation()