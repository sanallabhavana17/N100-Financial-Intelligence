from pathlib import Path

import pandas as pd


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


# ---------------------------------------------------------------------
# DQ-01: Company PK Uniqueness
# ---------------------------------------------------------------------

def validate_pk_uniqueness(df, table_name, failures):
    """DQ-01: Primary-key values must be unique."""

    if "id" not in df.columns:
        return

    duplicate_count = int(df["id"].duplicated().sum())

    if duplicate_count > 0:
        record_failure(
            failures,
            "DQ-01",
            "CRITICAL",
            table_name,
            f"{duplicate_count} duplicate primary-key values found",
        )


# ---------------------------------------------------------------------
# DQ-02: Annual PK Uniqueness
# ---------------------------------------------------------------------

def validate_company_year_pk(df, table_name, failures):
    """DQ-02: No duplicate (company_id, year) records."""

    if "company_id" not in df.columns or "year" not in df.columns:
        return

    duplicate_count = int(
        df.duplicated(
            subset=["company_id", "year"]
        ).sum()
    )

    if duplicate_count > 0:
        record_failure(
            failures,
            "DQ-02",
            "CRITICAL",
            table_name,
            f"{duplicate_count} duplicate (company_id, year) records found",
        )


# ---------------------------------------------------------------------
# DQ-03: Foreign-Key Integrity
# ---------------------------------------------------------------------

def validate_fk_integrity(
    child_df,
    companies_df,
    table_name,
    failures,
):
    """
    DQ-03: Every company_id in a child table must exist
    in companies.id.
    """

    if "company_id" not in child_df.columns:
        return

    if "id" not in companies_df.columns:
        return

    valid_ids = set(
        companies_df["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    child_ids = (
        child_df["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    orphan_ids = sorted(
        set(child_ids) - valid_ids
    )

    if orphan_ids:
        record_failure(
            failures,
            "DQ-03",
            "CRITICAL",
            table_name,
            f"{len(orphan_ids)} orphan company_id values found: "
            f"{', '.join(orphan_ids[:10])}",
        )


# ---------------------------------------------------------------------
# DQ-04: Balance Sheet Balance
# ---------------------------------------------------------------------

def validate_balance_sheet_balance(
    df,
    table_name,
    failures,
):
    """
    DQ-04:
    |total_assets - total_liabilities| / total_assets < 0.01
    """

    required = {
        "total_assets",
        "total_liabilities",
    }

    if not required.issubset(df.columns):
        return

    assets = pd.to_numeric(
        df["total_assets"],
        errors="coerce",
    )

    liabilities = pd.to_numeric(
        df["total_liabilities"],
        errors="coerce",
    )

    valid = assets.notna() & liabilities.notna() & (assets != 0)

    difference = (
        (assets - liabilities).abs() / assets.abs()
    )

    violations = valid & (difference >= 0.01)

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-04",
            "WARNING",
            table_name,
            f"{count} balance-sheet rows exceed the 1% "
            "asset/liability tolerance",
        )


# ---------------------------------------------------------------------
# DQ-05: OPM Cross-Check
# ---------------------------------------------------------------------

def validate_opm_cross_check(
    df,
    table_name,
    failures,
):
    """
    DQ-05:
    |opm_percentage - (operating_profit / sales * 100)| < 1.0
    """

    required = {
        "opm_percentage",
        "operating_profit",
        "sales",
    }

    if not required.issubset(df.columns):
        return

    sales = pd.to_numeric(
        df["sales"],
        errors="coerce",
    )

    operating_profit = pd.to_numeric(
        df["operating_profit"],
        errors="coerce",
    )

    source_opm = pd.to_numeric(
        df["opm_percentage"],
        errors="coerce",
    )

    valid = (
        sales.notna()
        & operating_profit.notna()
        & source_opm.notna()
        & (sales != 0)
    )

    computed_opm = (
        operating_profit / sales * 100
    )

    violations = (
        valid
        & (
            (source_opm - computed_opm).abs()
            >= 1.0
        )
    )

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-05",
            "WARNING",
            table_name,
            f"{count} rows failed the OPM cross-check",
        )


# ---------------------------------------------------------------------
# DQ-06: Positive Sales
# ---------------------------------------------------------------------

def validate_positive_sales(
    df,
    table_name,
    failures,
    is_financials=False,
):
    """
    DQ-06:
    sales > 0 for non-bank companies.

    Financial-sector rows are excluded from this rule.
    """

    if is_financials or "sales" not in df.columns:
        return

    sales = pd.to_numeric(
        df["sales"],
        errors="coerce",
    )

    violations = sales.notna() & (sales <= 0)

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-06",
            "WARNING",
            table_name,
            f"{count} rows have sales <= 0",
        )


# ---------------------------------------------------------------------
# DQ-07: Year Format
# ---------------------------------------------------------------------

def validate_year_format(
    df,
    table_name,
    failures,
):
    """
    DQ-07:
    After normalize_year(), every year must match YYYY-MM.
    """

    if "year" not in df.columns:
        return

    values = df["year"].astype("string")

    valid = values.str.fullmatch(
        r"\d{4}-\d{2}",
        na=False,
    )

    count = int((~valid).sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-07",
            "CRITICAL",
            table_name,
            f"{count} rows contain invalid year format",
        )


# ---------------------------------------------------------------------
# DQ-08: Ticker Format
# ---------------------------------------------------------------------

def validate_ticker_format(
    df,
    table_name,
    failures,
):
    """
    DQ-08:
    company_id is stripped and upper-cased and must contain
    2-12 characters.
    """

    if "company_id" not in df.columns:
        return

    tickers = (
        df["company_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    invalid = (
        tickers.isna()
        | (tickers.str.len() < 2)
        | (tickers.str.len() > 12)
    )

    count = int(invalid.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-08",
            "CRITICAL",
            table_name,
            f"{count} rows contain invalid ticker length",
        )


# ---------------------------------------------------------------------
# DQ-09: Net Cash Check
# ---------------------------------------------------------------------

def validate_net_cash(
    df,
    table_name,
    failures,
    tolerance=10.0,
):
    """
    DQ-09:
    |net_cash_flow - (CFO + CFI + CFF)| <= 10 Cr.
    """

    required = {
        "net_cash_flow",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    }

    if not required.issubset(df.columns):
        return

    net_cash = pd.to_numeric(
        df["net_cash_flow"],
        errors="coerce",
    )

    cfo = pd.to_numeric(
        df["operating_activity"],
        errors="coerce",
    )

    cfi = pd.to_numeric(
        df["investing_activity"],
        errors="coerce",
    )

    cff = pd.to_numeric(
        df["financing_activity"],
        errors="coerce",
    )

    expected = cfo + cfi + cff

    valid = (
        net_cash.notna()
        & expected.notna()
    )

    violations = (
        valid
        & ((net_cash - expected).abs() > tolerance)
    )

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-09",
            "WARNING",
            table_name,
            f"{count} rows have net cash-flow mismatch "
            f"greater than {tolerance} Cr",
        )


# ---------------------------------------------------------------------
# DQ-10: Non-Negative Fixed Assets
# ---------------------------------------------------------------------

def validate_fixed_assets(
    df,
    table_name,
    failures,
):
    """DQ-10: fixed_assets must be >= 0."""

    if "fixed_assets" not in df.columns:
        return

    fixed_assets = pd.to_numeric(
        df["fixed_assets"],
        errors="coerce",
    )

    violations = (
        fixed_assets.notna()
        & (fixed_assets < 0)
    )

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-10",
            "WARNING",
            table_name,
            f"{count} rows contain negative fixed assets",
        )


# ---------------------------------------------------------------------
# DQ-11: Tax Rate Range
# ---------------------------------------------------------------------

def validate_tax_rate(
    df,
    table_name,
    failures,
):
    """DQ-11: tax_percentage must be between 0 and 60."""

    if "tax_percentage" not in df.columns:
        return

    tax = pd.to_numeric(
        df["tax_percentage"],
        errors="coerce",
    )

    violations = (
        tax.notna()
        & (
            (tax < 0)
            | (tax > 60)
        )
    )

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-11",
            "WARNING",
            table_name,
            f"{count} rows contain tax rates outside 0-60%",
        )


# ---------------------------------------------------------------------
# DQ-12: Dividend Payout Cap
# ---------------------------------------------------------------------

def validate_dividend_payout(
    df,
    table_name,
    failures,
):
    """DQ-12: dividend_payout must be <= 200%."""

    if "dividend_payout" not in df.columns:
        return

    payout = pd.to_numeric(
        df["dividend_payout"],
        errors="coerce",
    )

    violations = (
        payout.notna()
        & (payout > 200)
    )

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-12",
            "WARNING",
            table_name,
            f"{count} rows contain dividend payout > 200%",
        )


# ---------------------------------------------------------------------
# DQ-13: URL Validity
# ---------------------------------------------------------------------

def validate_document_urls(
    df,
    table_name,
    failures,
    request_head=None,
):
    """
    DQ-13:
    Annual_Report URL should return HTTP 200.

    A request_head callable can be injected during testing.
    """

    if "Annual_Report" not in df.columns:
        return

    if request_head is None:
        try:
            import requests

            request_head = requests.head
        except ImportError:
            return

    invalid_count = 0

    for url in df["Annual_Report"].dropna():

        url = str(url).strip()

        if not url:
            continue

        try:
            response = request_head(
                url,
                timeout=5,
                allow_redirects=True,
            )

            if response.status_code != 200:
                invalid_count += 1

        except Exception:
            invalid_count += 1

    if invalid_count > 0:
        record_failure(
            failures,
            "DQ-13",
            "WARNING",
            table_name,
            f"{invalid_count} document URLs did not return HTTP 200",
        )


# ---------------------------------------------------------------------
# DQ-14: EPS Sign Consistency
# ---------------------------------------------------------------------

def validate_eps_sign(
    df,
    table_name,
    failures,
):
    """
    DQ-14:
    EPS should be positive when net_profit is positive.
    """

    required = {
        "eps",
        "net_profit",
    }

    if not required.issubset(df.columns):
        return

    eps = pd.to_numeric(
        df["eps"],
        errors="coerce",
    )

    net_profit = pd.to_numeric(
        df["net_profit"],
        errors="coerce",
    )

    violations = (
        net_profit.notna()
        & eps.notna()
        & (net_profit > 0)
        & (eps <= 0)
    )

    count = int(violations.sum())

    if count > 0:
        record_failure(
            failures,
            "DQ-14",
            "WARNING",
            table_name,
            f"{count} rows have positive net profit but non-positive EPS",
        )


# ---------------------------------------------------------------------
# Validation runners
# ---------------------------------------------------------------------

def run_validation():
    """Validate raw source datasets against DQ-01 through DQ-14."""

    from src.etl.loader import load_all_files

    datasets = load_all_files()

    failures = []

    companies_df = datasets.get("companies.xlsx")

    for filename, df in datasets.items():

        table_name = Path(filename).stem

        # DQ-01
        validate_pk_uniqueness(
            df,
            table_name,
            failures,
        )

        # DQ-02
        validate_company_year_pk(
            df,
            table_name,
            failures,
        )

        # DQ-03
        if companies_df is not None:
            validate_fk_integrity(
                df,
                companies_df,
                table_name,
                failures,
            )

        # DQ-04
        validate_balance_sheet_balance(
            df,
            table_name,
            failures,
        )

        # DQ-05
        validate_opm_cross_check(
            df,
            table_name,
            failures,
        )

        # DQ-06
        validate_positive_sales(
            df,
            table_name,
            failures,
        )

        # DQ-07
        validate_year_format(
            df,
            table_name,
            failures,
        )

        # DQ-08
        validate_ticker_format(
            df,
            table_name,
            failures,
        )

        # DQ-09
        validate_net_cash(
            df,
            table_name,
            failures,
        )

        # DQ-10
        validate_fixed_assets(
            df,
            table_name,
            failures,
        )

        # DQ-11
        validate_tax_rate(
            df,
            table_name,
            failures,
        )

        # DQ-12
        validate_dividend_payout(
            df,
            table_name,
            failures,
        )

        # DQ-13
        validate_document_urls(
            df,
            table_name,
            failures,
        )

        # DQ-14
        validate_eps_sign(
            df,
            table_name,
            failures,
        )

    failures_df = pd.DataFrame(failures)

    output_file = OUTPUT_DIR / "validation_failures.csv"

    failures_df.to_csv(
        output_file,
        index=False,
    )

    print("\nRaw-data validation completed.")
    print(f"Failures found: {len(failures_df)}")
    print(f"Output: {output_file}")

    return failures_df


def load_processed_files():
    """Load cleaned datasets from data/processed."""

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
                f"WARNING: Missing processed file: {filepath}"
            )

            continue

        datasets[filename] = pd.read_csv(filepath)

    return datasets


def run_processed_validation():
    """Validate cleaned datasets produced by the ETL pipeline."""

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

        validate_balance_sheet_balance(
            df,
            table_name,
            failures,
        )

        validate_opm_cross_check(
            df,
            table_name,
            failures,
        )

        validate_positive_sales(
            df,
            table_name,
            failures,
        )

        validate_year_format(
            df,
            table_name,
            failures,
        )

        validate_ticker_format(
            df,
            table_name,
            failures,
        )

        validate_net_cash(
            df,
            table_name,
            failures,
        )

        validate_fixed_assets(
            df,
            table_name,
            failures,
        )

        validate_tax_rate(
            df,
            table_name,
            failures,
        )

        validate_dividend_payout(
            df,
            table_name,
            failures,
        )

        validate_eps_sign(
            df,
            table_name,
            failures,
        )

    failures_df = pd.DataFrame(failures)

    output_file = (
        OUTPUT_DIR / "processed_validation_failures.csv"
    )

    failures_df.to_csv(
        output_file,
        index=False,
    )

    print("\nProcessed-data validation completed.")
    print(f"Failures found: {len(failures_df)}")
    print(f"Output: {output_file}")

    if failures:
        print("\nProcessed-data failures:")
        print(failures_df.to_string(index=False))
    else:
        print(
            "All processed datasets passed validation. OK"
        )

    return failures_df


if __name__ == "__main__":
    run_validation()
    run_processed_validation()
