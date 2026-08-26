from pathlib import Path

import pandas as pd

from src.analytics.cashflow_kpis import capital_allocation_pattern


INPUT_FILE = Path("data/processed/cashflow_cleaned.csv")
OUTPUT_FILE = Path("output/capital_allocation.csv")


def sign(value):
    """Return the required sign representation."""
    if value > 0:
        return "+"
    elif value < 0:
        return "-"
    return "0"


def generate_capital_allocation():
    """
    Generate capital allocation classification for every
    company-year record.

    Output columns:
        company_id
        year
        cfo_sign
        cfi_sign
        cff_sign
        pattern_label
    """

    df = pd.read_csv(INPUT_FILE)

    required_columns = {
        "company_id",
        "year",
        "operating_activity",
        "investing_activity",
        "financing_activity",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    records = []

    for _, row in df.iterrows():

        cfo = row["operating_activity"]
        cfi = row["investing_activity"]
        cff = row["financing_activity"]

        pattern_label = capital_allocation_pattern(
            cfo,
            cfi,
            cff,
        )

        records.append(
            {
                "company_id": row["company_id"],
                "year": row["year"],
                "cfo_sign": sign(cfo),
                "cfi_sign": sign(cfi),
                "cff_sign": sign(cff),
                "pattern_label": pattern_label,
            }
        )

    result = pd.DataFrame(records)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"Capital allocation file created: "
        f"{OUTPUT_FILE}"
    )
    print(f"Rows: {len(result)}")
    print(f"Companies: {result['company_id'].nunique()}")
    print(
        f"Company-year duplicates: "
        f"{result.duplicated(['company_id', 'year']).sum()}"
    )

    print("\nPattern distribution:")
    print(result["pattern_label"].value_counts())

    return result


if __name__ == "__main__":
    generate_capital_allocation()