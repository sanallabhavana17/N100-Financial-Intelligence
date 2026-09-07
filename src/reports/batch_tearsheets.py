from pathlib import Path
import sqlite3
import csv
import sys

# Project root
ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "data" / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "tearsheets"
SKIPPED_PATH = ROOT / "output" / "skipped_tearsheets.csv"

# Import the working Day 33 generator
from src.reports.tearsheet import generate_tearsheet


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_all_companies():
    conn = get_connection()

    query = """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY id
    """

    rows = conn.execute(query).fetchall()
    conn.close()

    return rows


def get_year_count(company_id):
    conn = get_connection()

    query = """
        SELECT COUNT(DISTINCT year)
        FROM profitandloss
        WHERE company_id = ?
    """

    count = conn.execute(query, (company_id,)).fetchone()[0]
    conn.close()

    return count


def main():
    print("N100 COMPANY TEARSHEET BATCH GENERATOR")
    print("=" * 70)
    print(f"Database : {DB_PATH}")
    print(f"Output   : {OUTPUT_DIR}")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SKIPPED_PATH.parent.mkdir(parents=True, exist_ok=True)

    companies = get_all_companies()

    print(f"Companies found: {len(companies)}")
    print()

    generated = []
    skipped = []
    failed = []

    for index, (company_id, company_name) in enumerate(companies, start=1):

        year_count = get_year_count(company_id)

        print(
            f"[{index:02d}/{len(companies)}] "
            f"{company_id:<12} "
            f"{company_name[:30]:<30} "
            f"{year_count:>2} years",
            end=" "
        )

        # Sprint 5 Day 34 requirement:
        # Skip companies with fewer than 3 years of data.
        if year_count < 3:
            print("SKIPPED (<3 years)")
            skipped.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "year_count": year_count,
                    "reason": "Less than 3 years of profit/loss data",
                }
            )
            continue

        try:
            pdf_path = generate_tearsheet(company_id)

            pdf_path = Path(pdf_path)

            if pdf_path.exists():
                size_kb = pdf_path.stat().st_size / 1024

                print(f"OK  {pdf_path.name:<32} {size_kb:,.1f} KB")

                generated.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "pdf": pdf_path.name,
                    }
                )
            else:
                print("FAILED - PDF not created")

                failed.append(
                    {
                        "company_id": company_id,
                        "company_name": company_name,
                        "reason": "PDF was not created",
                    }
                )

        except Exception as exc:
            print(f"FAILED - {exc}")

            failed.append(
                {
                    "company_id": company_id,
                    "company_name": company_name,
                    "reason": str(exc),
                }
            )

    # ------------------------------------------------------------------
    # Save skipped_tearsheets.csv
    # ------------------------------------------------------------------

    with open(SKIPPED_PATH, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "company_id",
                "company_name",
                "year_count",
                "reason",
            ],
        )

        writer.writeheader()
        writer.writerows(skipped)

    print()
    print("=" * 70)
    print(f"Generated : {len(generated)}")
    print(f"Skipped   : {len(skipped)}")
    print(f"Failed    : {len(failed)}")
    print(f"Skipped log: {SKIPPED_PATH}")

    if failed:
        print()
        print("FAILED COMPANIES")
        print("-" * 70)

        for item in failed:
            print(
                f"{item['company_id']:<12} "
                f"{item['company_name']:<30} "
                f"{item['reason']}"
            )

    print()
    print("=" * 70)

    if not failed:
        print("Day 34 company tearsheet batch completed successfully.")
    else:
        print("Day 34 company tearsheet batch completed with failures.")


if __name__ == "__main__":
    main()