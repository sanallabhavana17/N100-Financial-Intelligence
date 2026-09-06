from pathlib import Path

import numpy as np
import pandas as pd

from src.dashboard.data_loader import load_db


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HELPERS
# ============================================================

def safe_numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# BUILD VALUATION SUMMARY
# ============================================================

def build_valuation_summary():

    query = """
    SELECT
        m.company_id,
        c.company_name,
        s.broad_sector AS sector,
        m.year,
        m.market_cap_crore,
        m.pe_ratio,
        m.pb_ratio,
        m.ev_ebitda,
        r.free_cash_flow_cr
    FROM market_cap m

    LEFT JOIN companies c
        ON m.company_id = c.id

    LEFT JOIN sectors s
        ON m.company_id = s.company_id

    LEFT JOIN financial_ratios r
        ON m.company_id = r.company_id
        AND m.year = r.year

    ORDER BY
        m.company_id,
        m.year
    """

    df = load_db(query)

    if df.empty:
        raise ValueError(
            "No valuation data found in the database."
        )


    # ========================================================
    # NUMERIC CONVERSION
    # ========================================================

    numeric_columns = [
        "year",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "free_cash_flow_cr",
    ]

    for column in numeric_columns:

        df[column] = safe_numeric(
            df[column]
        )


    # ========================================================
    # INVALID VALUATION MULTIPLES
    # ========================================================

    for column in [
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
    ]:

        df.loc[
            df[column] <= 0,
            column,
        ] = np.nan


    # ========================================================
    # LATEST VALUATION YEAR FOR EACH COMPANY
    # ========================================================

    current = (
        df
        .sort_values(
            [
                "company_id",
                "year",
            ]
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )


    current = current[
        [
            "company_id",
            "company_name",
            "sector",
            "year",
            "market_cap_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "free_cash_flow_cr",
        ]
    ]


    # ========================================================
    # FIVE-YEAR MEDIAN P/E
    # ========================================================

    five_year_medians = []

    for company_id, company_df in df.groupby(
        "company_id"
    ):

        company_df = (
            company_df
            .sort_values("year")
            .tail(5)
        )

        five_year_medians.append(
            {
                "company_id": company_id,
                "5yr_median_PE":
                    company_df[
                        "pe_ratio"
                    ].median(),
            }
        )


    historical = pd.DataFrame(
        five_year_medians
    )


    # ========================================================
    # MERGE FIVE-YEAR MEDIAN
    # ========================================================

    result = current.merge(
        historical,
        on="company_id",
        how="left",
    )


    # ========================================================
    # SECTOR MEDIAN P/E
    #
    # Latest P/E observation of each company
    # is used to calculate the sector median.
    # ========================================================

    sector_medians = (
        current
        .groupby(
            "sector",
            dropna=False,
        )
        .agg(
            sector_median_PE=(
                "pe_ratio",
                "median",
            )
        )
        .reset_index()
    )


    result = result.merge(
        sector_medians,
        on="sector",
        how="left",
    )


    # ========================================================
    # FCF YIELD
    #
    # FCF Yield =
    # FCF / Market Cap * 100
    # ========================================================

    result["FCF_yield_pct"] = np.where(

        (
            result[
                "market_cap_crore"
            ] > 0
        )
        &
        result[
            "free_cash_flow_cr"
        ].notna(),

        (
            result[
                "free_cash_flow_cr"
            ]
            /
            result[
                "market_cap_crore"
            ]
        ) * 100,

        np.nan,
    )


    # ========================================================
    # P/E VS SECTOR MEDIAN
    #
    # PE_vs_sector_median_pct =
    # ((Company PE / Sector Median PE) - 1) * 100
    # ========================================================

    result[
        "PE_vs_sector_median_pct"
    ] = np.where(

        result[
            "pe_ratio"
        ].notna()
        &
        result[
            "sector_median_PE"
        ].notna()
        &
        (
            result[
                "sector_median_PE"
            ] > 0
        ),

        (
            (
                result[
                    "pe_ratio"
                ]
                /
                result[
                    "sector_median_PE"
                ]
            )
            - 1
        ) * 100,

        np.nan,
    )


    # ========================================================
    # VALUATION FLAG
    #
    # > 150% of sector median = Caution
    # < 70% of sector median = Discount
    # Otherwise = Fair
    # ========================================================

    result["flag"] = "Fair"


    caution_mask = (
        result[
            "pe_ratio"
        ].notna()
        &
        result[
            "sector_median_PE"
        ].notna()
        &
        (
            result[
                "pe_ratio"
            ]
            >
            result[
                "sector_median_PE"
            ] * 1.5
        )
    )


    discount_mask = (
        result[
            "pe_ratio"
        ].notna()
        &
        result[
            "sector_median_PE"
        ].notna()
        &
        (
            result[
                "pe_ratio"
            ]
            <
            result[
                "sector_median_PE"
            ] * 0.7
        )
    )


    result.loc[
        caution_mask,
        "flag",
    ] = "Caution"


    result.loc[
        discount_mask,
        "flag",
    ] = "Discount"


    # ========================================================
    # FINAL REQUIRED COLUMNS
    # ========================================================

    result = result.rename(
        columns={
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
        }
    )


    required_columns = [
        "company_id",
        "company_name",
        "sector",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
        "flag",
    ]


    result = result[
        required_columns
    ].copy()


    # ========================================================
    # SORT
    # ========================================================

    result = (
        result
        .sort_values(
            [
                "flag",
                "company_name",
            ]
        )
        .reset_index(drop=True)
    )


    return result


# ============================================================
# WRITE OUTPUT FILES
# ============================================================

def main():

    result = build_valuation_summary()


    # ========================================================
    # VALIDATE 92-COMPANY REQUIREMENT
    # ========================================================

    company_count = (
        result[
            "company_id"
        ]
        .nunique()
    )


    if company_count != 92:

        raise ValueError(
            "Valuation summary must contain "
            f"92 companies, but found "
            f"{company_count}."
        )


    # ========================================================
    # VALIDATE REQUIRED COLUMNS
    # ========================================================

    required_columns = [
        "company_id",
        "company_name",
        "sector",
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
        "flag",
    ]


    missing_columns = [
        column
        for column in required_columns
        if column not in result.columns
    ]


    if missing_columns:

        raise ValueError(
            "Missing required columns: "
            + ", ".join(
                missing_columns
            )
        )


    # ========================================================
    # VALIDATE FLAGS
    # ========================================================

    valid_flags = {
        "Caution",
        "Discount",
        "Fair",
    }


    invalid_flags = set(
        result[
            "flag"
        ]
        .dropna()
        .unique()
    ) - valid_flags


    if invalid_flags:

        raise ValueError(
            "Invalid valuation flags: "
            + ", ".join(
                sorted(
                    invalid_flags
                )
            )
        )


    # ========================================================
    # VALUATION SUMMARY EXCEL
    # ========================================================

    summary_path = (
        OUTPUT_DIR
        / "valuation_summary.xlsx"
    )


    result.to_excel(
        summary_path,
        index=False,
    )


    # ========================================================
    # FLAGGED COMPANIES ONLY
    # ========================================================

    flags = result[
        result[
            "flag"
        ].isin(
            [
                "Caution",
                "Discount",
            ]
        )
    ].copy()


    flags_path = (
        OUTPUT_DIR
        / "valuation_flags.csv"
    )


    flags.to_csv(
        flags_path,
        index=False,
    )


    # ========================================================
    # CONSOLE OUTPUT
    # ========================================================

    print()
    print(
        "N100 VALUATION ENGINE"
    )
    print(
        "=" * 60
    )

    print(
        f"Companies: {company_count}"
    )

    print(
        f"Summary file: {summary_path}"
    )

    print(
        f"Flags file:   {flags_path}"
    )

    print()

    print(
        "Required columns:"
    )

    print(
        result.columns.tolist()
    )

    print()

    print(
        "Valuation flags:"
    )

    print(
        result[
            "flag"
        ]
        .value_counts()
        .to_string()
    )

    print()

    print(
        "Flagged companies:"
    )

    print(
        flags[
            [
                "company_id",
                "company_name",
                "sector",
                "P/E",
                "FCF_yield_pct",
                "PE_vs_sector_median_pct",
                "flag",
            ]
        ].to_string(
            index=False
        )
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()