"""
N100 Financial Intelligence
Sprint 5 - Day 32
Capital Allocation Pattern Analysis

Uses the existing output/capital_allocation.csv.

Outputs:
    output/pattern_changes.csv

Also updates:
    output/cashflow_intelligence.xlsx

The analysis:
    1. Verifies company/year coverage.
    2. Produces latest-year pattern distribution.
    3. Tracks year-over-year pattern changes.
    4. Adds capital allocation information to the
       cash-flow intelligence workbook.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CAPITAL_ALLOCATION_FILE = (
    PROJECT_ROOT / "output" / "capital_allocation.csv"
)

CASHFLOW_FILE = (
    PROJECT_ROOT / "output" / "cashflow_intelligence.xlsx"
)

PATTERN_CHANGES_FILE = (
    PROJECT_ROOT / "output" / "pattern_changes.csv"
)


EXPECTED_PATTERNS = [
    "Reinvestor",
    "Shareholder Returns",
    "Liquidating Assets",
    "Distress Signal",
    "Growth Funded by Debt",
    "Cash Accumulator",
    "Pre-Revenue",
    "Mixed",
]


REQUIRED_COLUMNS = [
    "company_id",
    "year",
    "cfo_sign",
    "cfi_sign",
    "cff_sign",
    "pattern_label",
]


def load_capital_allocation():
    if not CAPITAL_ALLOCATION_FILE.exists():
        raise FileNotFoundError(
            f"Missing file: {CAPITAL_ALLOCATION_FILE}"
        )

    df = pd.read_csv(CAPITAL_ALLOCATION_FILE)

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Missing required columns: {missing}"
        )

    df["company_id"] = df["company_id"].astype(str)
    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    return df


def verify_coverage(df):
    print()
    print("COVERAGE VALIDATION")
    print("-" * 70)

    company_count = df["company_id"].nunique()

    print(f"Companies: {company_count}")
    print(f"Rows:      {len(df):,}")
    print(
        f"Years:     {int(df['year'].min())} - "
        f"{int(df['year'].max())}"
    )

    if company_count != 92:
        raise RuntimeError(
            f"Expected 92 companies, found {company_count}."
        )

    # Check duplicate company/year combinations.
    duplicates = df.duplicated(
        subset=["company_id", "year"]
    ).sum()

    print(f"Duplicate company/year rows: {duplicates}")

    if duplicates:
        raise RuntimeError(
            "Duplicate company/year records found."
        )

    # Check missing patterns.
    missing_patterns = df["pattern_label"].isna().sum()

    print(f"Missing pattern labels:       {missing_patterns}")

    if missing_patterns:
        raise RuntimeError(
            "Missing capital allocation pattern labels found."
        )

    counts = (
        df.groupby("company_id")
        .size()
    )

    print(
        f"Minimum years/company:       {counts.min()}"
    )

    print(
        f"Maximum years/company:       {counts.max()}"
    )

    short_history = counts[counts < 3]

    if not short_history.empty:
        print()
        print("Companies with <3 years:")
        print(short_history.to_string())


def latest_year_distribution(df):
    latest_year = int(df["year"].max())

    latest = df[
        df["year"] == latest_year
    ].copy()

    if latest["company_id"].nunique() != 92:
        raise RuntimeError(
            "Latest year does not contain all 92 companies."
        )

    distribution = (
        latest["pattern_label"]
        .value_counts()
        .reindex(
            EXPECTED_PATTERNS,
            fill_value=0,
        )
        .rename_axis("pattern_label")
        .reset_index(name="company_count")
    )

    distribution["percentage"] = (
        distribution["company_count"]
        / len(latest)
        * 100
    )

    return latest_year, latest, distribution


def calculate_pattern_changes(df):
    """
    Compare each company's pattern with its previous
    available year.

    This uses the previous available observation rather
    than assuming every company has every calendar year.
    """

    ordered = df.sort_values(
        ["company_id", "year"]
    ).copy()

    ordered["previous_year"] = (
        ordered.groupby("company_id")["year"]
        .shift(1)
    )

    ordered["previous_pattern"] = (
        ordered.groupby("company_id")["pattern_label"]
        .shift(1)
    )

    changes = ordered[
        ordered["previous_pattern"].notna()
    ].copy()

    changes["changed"] = (
        changes["pattern_label"]
        != changes["previous_pattern"]
    )

    changes = changes.rename(
        columns={
            "year": "year",
            "pattern_label": "current_pattern",
        }
    )

    changes["company_id"] = (
        changes["company_id"].astype(str)
    )

    changes["previous_year"] = pd.to_numeric(
        changes["previous_year"],
        errors="coerce",
    ).astype("Int64")

    changes["year"] = pd.to_numeric(
        changes["year"],
        errors="coerce",
    ).astype("Int64")

    output = changes[
        [
            "company_id",
            "previous_year",
            "year",
            "previous_pattern",
            "current_pattern",
            "changed",
        ]
    ].copy()

    return output


def transition_summary(pattern_changes):
    changed = pattern_changes[
        pattern_changes["changed"] == True
    ].copy()

    if changed.empty:
        return pd.DataFrame(
            columns=[
                "previous_pattern",
                "current_pattern",
                "company_count",
            ]
        )

    summary = (
        changed.groupby(
            [
                "previous_pattern",
                "current_pattern",
            ]
        )
        .size()
        .reset_index(
            name="company_count"
        )
        .sort_values(
            "company_count",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return summary


def update_cashflow_workbook(
    cashflow_file,
    latest,
    distribution,
    transition,
):
    """
    Add Day 32 sheets to the existing Day 31 workbook.

    Existing Day 31 sheets are preserved.
    """

    if not cashflow_file.exists():
        raise FileNotFoundError(
            f"Missing workbook: {cashflow_file}"
        )

    # Read the existing main intelligence sheet.
    intelligence = pd.read_excel(
        cashflow_file,
        sheet_name="cashflow_intelligence",
    )

    # Latest capital allocation for each company.
    allocation_latest = latest[
        [
            "company_id",
            "pattern_label",
            "year",
        ]
    ].copy()

    allocation_latest = allocation_latest.rename(
        columns={
            "pattern_label":
                "latest_capital_allocation",
            "year":
                "capital_allocation_year",
        }
    )

    # Add the latest pattern to the intelligence table.
    intelligence["company_id"] = (
        intelligence["company_id"]
        .astype(str)
    )

    allocation_latest["company_id"] = (
        allocation_latest["company_id"]
        .astype(str)
    )

    intelligence = intelligence.drop(
        columns=[
            "latest_capital_allocation",
            "capital_allocation_year",
        ],
        errors="ignore",
    )

    intelligence = intelligence.merge(
        allocation_latest,
        on="company_id",
        how="left",
    )

    # Rewrite workbook while preserving the existing Day 31 data.
    with pd.ExcelWriter(
        cashflow_file,
        engine="openpyxl",
        mode="w",
    ) as writer:

        intelligence.to_excel(
            writer,
            sheet_name="cashflow_intelligence",
            index=False,
        )

        # Recreate Day 31 summary.
        summary = pd.DataFrame(
            {
                "Metric": [
                    "Companies",
                    "High Quality CFO",
                    "Moderate CFO",
                    "Accrual Risk CFO",
                    "Asset Light",
                    "Moderate CapEx",
                    "Capital Intensive",
                    "Distress Flags",
                    "Deleveraging Flags",
                ],
                "Count": [
                    intelligence["company_id"]
                    .nunique(),
                    (
                        intelligence[
                            "cfo_quality_label"
                        ] == "High Quality"
                    ).sum(),
                    (
                        intelligence[
                            "cfo_quality_label"
                        ] == "Moderate"
                    ).sum(),
                    (
                        intelligence[
                            "cfo_quality_label"
                        ] == "Accrual Risk"
                    ).sum(),
                    (
                        intelligence[
                            "capex_label"
                        ] == "Asset Light"
                    ).sum(),
                    (
                        intelligence[
                            "capex_label"
                        ] == "Moderate"
                    ).sum(),
                    (
                        intelligence[
                            "capex_label"
                        ] == "Capital Intensive"
                    ).sum(),
                    intelligence[
                        "distress_flag"
                    ].sum(),
                    intelligence[
                        "deleveraging_flag"
                    ].sum(),
                ],
            }
        )

        summary.to_excel(
            writer,
            sheet_name="summary",
            index=False,
        )

        distribution.to_excel(
            writer,
            sheet_name="allocation_distribution",
            index=False,
        )

        transition.to_excel(
            writer,
            sheet_name="allocation_changes",
            index=False,
        )

    # Validate workbook after writing.
    workbook = load_workbook(
        cashflow_file,
        read_only=True,
    )

    required_sheets = {
        "cashflow_intelligence",
        "summary",
        "allocation_distribution",
        "allocation_changes",
    }

    missing_sheets = (
        required_sheets
        - set(workbook.sheetnames)
    )

    workbook.close()

    if missing_sheets:
        raise RuntimeError(
            f"Missing workbook sheets: {missing_sheets}"
        )


def main():
    print("N100 CAPITAL ALLOCATION ANALYSIS")
    print("=" * 70)

    df = load_capital_allocation()

    print(
        f"Capital allocation rows loaded: "
        f"{len(df):,}"
    )

    verify_coverage(df)

    # -----------------------------------------------------------------------
    # Latest-year distribution
    # -----------------------------------------------------------------------

    latest_year, latest, distribution = (
        latest_year_distribution(df)
    )

    print()
    print("LATEST-YEAR DISTRIBUTION")
    print("-" * 70)
    print(f"Latest year: {latest_year}")
    print(f"Companies:   {latest['company_id'].nunique()}")

    print()
    print(
        distribution.to_string(index=False)
    )

    # -----------------------------------------------------------------------
    # Pattern changes
    # -----------------------------------------------------------------------

    changes = calculate_pattern_changes(df)

    transition = transition_summary(changes)

    changes.to_csv(
        PATTERN_CHANGES_FILE,
        index=False,
        encoding="utf-8",
    )

    print()
    print("PATTERN CHANGE ANALYSIS")
    print("-" * 70)
    print(
        f"Year-over-year observations: "
        f"{len(changes):,}"
    )

    print(
        f"Pattern changes: "
        f"{changes['changed'].sum():,}"
    )

    print(
        f"Unchanged observations: "
        f"{(~changes['changed']).sum():,}"
    )

    print()
    print("Top pattern transitions:")

    if transition.empty:
        print("No pattern changes detected.")
    else:
        print(
            transition
            .head(15)
            .to_string(index=False)
        )

    # -----------------------------------------------------------------------
    # Update Day 31 workbook
    # -----------------------------------------------------------------------

    update_cashflow_workbook(
        CASHFLOW_FILE,
        latest,
        distribution,
        transition,
    )

    # -----------------------------------------------------------------------
    # Final validation
    # -----------------------------------------------------------------------

    print()
    print("FINAL VALIDATION")
    print("-" * 70)

    print(
        f"Latest-year companies: "
        f"{latest['company_id'].nunique()}"
    )

    print(
        f"Expected patterns represented: "
        f"{len(EXPECTED_PATTERNS)}"
    )

    print(
        f"Distribution total: "
        f"{distribution['company_count'].sum()}"
    )

    print(
        f"Pattern-change rows: "
        f"{len(changes):,}"
    )

    print(
        f"Changed rows: "
        f"{changes['changed'].sum():,}"
    )

    print()
    print(f"Saved: {PATTERN_CHANGES_FILE}")
    print(f"Updated: {CASHFLOW_FILE}")
    print()
    print(
        "Day 32 Capital Allocation Analysis "
        "completed successfully."
    )


if __name__ == "__main__":
    main()