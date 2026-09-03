"""
NIFTY100 FINANCIAL INTELLIGENCE
SPRINT 3 - DAY 19
RADAR CHART MODULE

Purpose:
    Generate radar-chart data and PNG charts for all 92 NIFTY100 companies.

Input:
    output/final_financial_ratios.csv

Optional input:
    output/peer_percentile_table.csv

Outputs:
    output/radar_chart_data.csv
    output/radar_charts/<company_id>_radar.png

Radar metrics:
    1. Profitability       - ROE
    2. Capital Efficiency  - ROCE
    3. Asset Returns       - ROA
    4. Net Margin          - NPM
    5. Operating Margin    - OPM
    6. Low Leverage        - D/E
    7. Interest Coverage   - ICR
    8. Revenue Growth      - Revenue CAGR 5Y
    9. PAT Growth          - PAT CAGR 5Y
   10. EPS Growth          - EPS CAGR 5Y
   11. Free Cash Flow      - FCF
   12. Asset Turnover      - Asset Turnover
   13. Quality Score       - Composite Quality Score

All 92 companies are included.
Percentiles are calculated across the latest available observation
for every company.
For D/E, lower leverage is better, so the percentile is inverted.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "output" / "final_financial_ratios.csv"
PEER_FILE = BASE_DIR / "output" / "peer_percentile_table.csv"

RADAR_DATA_FILE = BASE_DIR / "output" / "radar_chart_data.csv"
RADAR_DIR = BASE_DIR / "output" / "radar_charts"


# ============================================================
# CONFIGURATION
# ============================================================

EXPECTED_COMPANIES = 92

RADAR_METRICS = {
    "Profitability": "return_on_equity_pct",
    "Capital Efficiency": "return_on_capital_employed_pct",
    "Asset Returns": "return_on_assets_pct",
    "Net Margin": "net_profit_margin_pct",
    "Operating Margin": "operating_profit_margin_pct",
    "Low Leverage": "debt_to_equity",
    "Interest Coverage": "interest_coverage",
    "Revenue Growth": "revenue_cagr_5yr",
    "PAT Growth": "pat_cagr_5yr",
    "EPS Growth": "eps_cagr_5yr",
    "Free Cash Flow": "free_cash_flow_cr",
    "Asset Turnover": "asset_turnover",
    "Quality Score": "composite_quality_score",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_numeric(series):
    """
    Convert a pandas series to numeric safely.
    Invalid values become NaN.
    """
    return pd.to_numeric(series, errors="coerce")


def percentile_rank(series):
    """
    Calculate percentile rank from 0 to 100.

    Higher raw values receive higher percentile values.
    NaN values remain NaN.
    """
    numeric = clean_numeric(series)

    valid = numeric.notna()

    result = pd.Series(np.nan, index=series.index, dtype=float)

    if valid.sum() == 0:
        return result

    if valid.sum() == 1:
        result.loc[valid] = 100.0
        return result

    result.loc[valid] = numeric.loc[valid].rank(
        method="average",
        pct=True
    ) * 100.0

    return result


def safe_filename(value):
    """
    Make a company ID safe for use as a filename.
    """
    value = str(value)

    invalid_chars = '<>:"/\\|?*'

    for char in invalid_chars:
        value = value.replace(char, "_")

    return value.strip()


# ============================================================
# LOAD DATA
# ============================================================

def load_financial_data():
    """
    Load the final financial-ratio dataset.

    This is intentionally used instead of peer_percentile_table.csv
    because the peer table contains only 56 peer-group companies,
    whereas D19 requires radar charts for all 92 companies.
    """

    print("Loading final financial ratio data...")
    print(f"Input: {INPUT_FILE}")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Required input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(f"Input rows: {len(df):,}")
    print(f"Companies: {df['company_id'].nunique():,}")

    return df


# ============================================================
# VALIDATE REQUIRED COLUMNS
# ============================================================

def validate_columns(df):
    """
    Validate that all required radar columns exist.
    """

    required_columns = {
        "company_id",
        "year",
        *RADAR_METRICS.values(),
    }

    missing = sorted(required_columns - set(df.columns))

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(f"  - {column}" for column in missing)
        )

    print("Required radar columns: PASSED")


# ============================================================
# SELECT LATEST COMPANY OBSERVATION
# ============================================================

def select_latest_company_data(df):
    """
    Select the latest available financial year for each company.

    This guarantees one radar profile per company.
    """

    print()
    print("Selecting latest available company observations...")

    data = df.copy()

    data["year"] = pd.to_numeric(data["year"], errors="coerce")

    data = data.dropna(subset=["company_id", "year"])

    data = data.sort_values(
        ["company_id", "year"]
    )

    latest = (
        data
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    latest = latest.sort_values("company_id").reset_index(drop=True)

    print(f"Latest company observations: {len(latest):,}")
    print(
        f"Unique companies: "
        f"{latest['company_id'].nunique():,}"
    )

    return latest


# ============================================================
# ADD OPTIONAL PEER INFORMATION
# ============================================================

def add_peer_information(radar_df):
    """
    Add peer-group information where available.

    Peer membership is optional because only 56 companies
    currently have peer-group assignments.

    Radar charts remain available for all 92 companies.
    """

    if not PEER_FILE.exists():
        print()
        print("Peer percentile file not found.")
        print("Continuing without peer-group information.")
        radar_df["peer_group_name"] = np.nan
        radar_df["peer_rank"] = np.nan
        radar_df["peer_group_size"] = np.nan
        return radar_df

    print()
    print("Loading optional peer-group information...")

    peer_df = pd.read_csv(PEER_FILE)

    if "company_id" not in peer_df.columns:
        print("WARNING: peer file has no company_id column.")
        radar_df["peer_group_name"] = np.nan
        radar_df["peer_rank"] = np.nan
        radar_df["peer_group_size"] = np.nan
        return radar_df

    # Select latest peer record for each company.
    peer_df["year"] = pd.to_numeric(
        peer_df["year"],
        errors="coerce"
    )

    peer_latest = (
        peer_df
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    optional_columns = [
        "company_id",
        "peer_group_name",
        "peer_rank",
        "peer_group_size",
    ]

    available_columns = [
        column
        for column in optional_columns
        if column in peer_latest.columns
    ]

    peer_latest = peer_latest[available_columns]

    # Avoid accidental duplicate company IDs.
    peer_latest = (
        peer_latest
        .drop_duplicates("company_id")
    )

    radar_df = radar_df.merge(
        peer_latest,
        on="company_id",
        how="left"
    )

    matched = radar_df["peer_group_name"].notna().sum()

    print(
        f"Companies with peer-group information: "
        f"{matched:,}/{len(radar_df):,}"
    )

    return radar_df


# ============================================================
# CREATE RADAR PERCENTILES
# ============================================================

def create_radar_data(latest_df):
    """
    Convert the 13 raw KPI metrics into 0-100 percentile scores.

    D/E is inverted because lower leverage is preferable.
    """

    print()
    print("Creating radar-chart percentile data...")

    radar = latest_df[
        ["company_id", "year"]
    ].copy()

    for label, source_column in RADAR_METRICS.items():

        percentile_column = (
            label.lower()
            .replace(" ", "_")
            + "_percentile"
        )

        raw_values = clean_numeric(
            latest_df[source_column]
        )

        percentile_values = percentile_rank(raw_values)

        # Lower debt-to-equity is better.
        if label == "Low Leverage":
            percentile_values = (
                100.0 - percentile_values
            )

        radar[percentile_column] = (
            percentile_values.round(4)
        )

    # Keep useful raw KPI values alongside percentile scores.
    for label, source_column in RADAR_METRICS.items():
        radar[source_column] = clean_numeric(
            latest_df[source_column]
        )

    return radar


# ============================================================
# VALIDATE RADAR DATA
# ============================================================

def validate_radar_data(radar_df):
    """
    Run D19 data-quality checks.
    """

    print()
    print("RADAR DATA VALIDATION")
    print("-" * 60)

    duplicate_count = (
        radar_df
        .duplicated(["company_id", "year"])
        .sum()
    )

    print(
        f"Duplicate company/year records: "
        f"{duplicate_count}"
    )

    percentile_columns = [
        column
        for column in radar_df.columns
        if column.endswith("_percentile")
    ]

    invalid_count = 0

    for column in percentile_columns:
        values = clean_numeric(radar_df[column])

        invalid = (
            values.notna()
            & ((values < 0) | (values > 100))
        )

        invalid_count += int(invalid.sum())

    print(
        f"Invalid radar percentile values: "
        f"{invalid_count}"
    )

    company_count = radar_df["company_id"].nunique()

    print(
        f"Unique companies: {company_count}"
    )

    print(
        f"Expected companies: {EXPECTED_COMPANIES}"
    )

    if duplicate_count != 0:
        raise ValueError(
            "Duplicate company/year records detected."
        )

    if invalid_count != 0:
        raise ValueError(
            "Invalid radar percentile values detected."
        )

    if company_count != EXPECTED_COMPANIES:
        raise ValueError(
            f"Expected {EXPECTED_COMPANIES} companies, "
            f"but found {company_count}."
        )

    if radar_df.empty:
        raise ValueError(
            "Radar dataset is empty."
        )

    print("Validation: PASSED")


# ============================================================
# SAVE RADAR DATA
# ============================================================

def save_radar_data(radar_df):
    """
    Save radar chart data as CSV.
    """

    RADAR_DATA_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    radar_df.to_csv(
        RADAR_DATA_FILE,
        index=False
    )

    print()
    print(
        f"Radar data saved: {RADAR_DATA_FILE}"
    )


# ============================================================
# GENERATE RADAR CHART
# ============================================================

def generate_single_radar(row):
    """
    Generate one radar chart for a company.
    """

    labels = list(RADAR_METRICS.keys())

    values = []

    for label in labels:

        percentile_column = (
            label.lower()
            .replace(" ", "_")
            + "_percentile"
        )

        value = row.get(
            percentile_column,
            np.nan
        )

        if pd.isna(value):
            value = 0.0

        values.append(float(value))

    # Close the radar polygon.
    values += values[:1]

    angles = np.linspace(
        0,
        2 * np.pi,
        len(labels),
        endpoint=False
    ).tolist()

    angles += angles[:1]

    fig, ax = plt.subplots(
        figsize=(9, 9),
        subplot_kw={"polar": True}
    )

    ax.set_theta_offset(
        np.pi / 2
    )

    ax.set_theta_direction(
        -1
    )

    ax.set_xticks(
        angles[:-1]
    )

    ax.set_xticklabels(
        labels,
        fontsize=8
    )

    ax.set_ylim(
        0,
        100
    )

    ax.set_yticks(
        [20, 40, 60, 80, 100]
    )

    ax.set_yticklabels(
        ["20", "40", "60", "80", "100"],
        fontsize=7
    )

    ax.plot(
        angles,
        values,
        linewidth=2
    )

    ax.fill(
        angles,
        values,
        alpha=0.20
    )

    company_id = str(row["company_id"])

    try:
        year = int(row["year"])
    except (ValueError, TypeError):
        year = row["year"]

    title = (
        f"{company_id} Financial Radar\n"
        f"Latest Year: {year}"
    )

    peer_group = row.get(
        "peer_group_name",
        np.nan
    )

    if pd.notna(peer_group):
        title += f"\nPeer Group: {peer_group}"

    ax.set_title(
        title,
        pad=25,
        fontsize=13,
        fontweight="bold"
    )

    output_name = (
        f"{safe_filename(company_id)}_radar.png"
    )

    output_path = RADAR_DIR / output_name

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close(fig)

    return output_path


# ============================================================
# GENERATE ALL RADAR CHARTS
# ============================================================

def generate_charts(radar_df):
    """
    Generate exactly one PNG chart per company.
    """

    print()
    print("Generating radar charts...")
    print(
        f"Output directory: {RADAR_DIR}"
    )

    RADAR_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Remove old radar PNG files so stale files
    # cannot inflate the final count.
    old_files = list(
        RADAR_DIR.glob("*.png")
    )

    for old_file in old_files:
        old_file.unlink()

    generated = 0

    for _, row in radar_df.iterrows():

        generate_single_radar(row)

        generated += 1

        if generated % 10 == 0:
            print(
                f"  Generated: "
                f"{generated}/{len(radar_df)}"
            )

    return generated


# ============================================================
# FINAL VALIDATION
# ============================================================

def final_validation(radar_df, generated_count):
    """
    Validate final D19 outputs.
    """

    print()
    print("FINAL VALIDATION")
    print("-" * 60)

    unique_companies = (
        radar_df["company_id"].nunique()
    )

    png_files = list(
        RADAR_DIR.glob("*.png")
    )

    png_count = len(png_files)

    duplicate_companies = (
        radar_df["company_id"]
        .duplicated()
        .sum()
    )

    print(
        f"Unique companies in radar data: "
        f"{unique_companies}"
    )

    print(
        f"PNG files generated: "
        f"{png_count}"
    )

    print(
        f"Expected companies: "
        f"{EXPECTED_COMPANIES}"
    )

    print(
        f"Duplicate company records: "
        f"{duplicate_companies}"
    )

    if unique_companies != EXPECTED_COMPANIES:
        raise ValueError(
            f"Radar data contains {unique_companies} "
            f"companies instead of {EXPECTED_COMPANIES}."
        )

    if generated_count != EXPECTED_COMPANIES:
        raise ValueError(
            f"Generated {generated_count} charts instead "
            f"of {EXPECTED_COMPANIES}."
        )

    if png_count != EXPECTED_COMPANIES:
        raise ValueError(
            f"Found {png_count} PNG files instead "
            f"of {EXPECTED_COMPANIES}."
        )

    if duplicate_companies != 0:
        raise ValueError(
            "Duplicate companies found in radar data."
        )

    print()
    print("D19 FINAL VALIDATION: PASSED")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("NIFTY100 RADAR CHART MODULE")
    print("SPRINT 3 - DAY 19")
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Load final financial data
    # --------------------------------------------------------

    df = load_financial_data()

    # --------------------------------------------------------
    # 2. Validate required columns
    # --------------------------------------------------------

    validate_columns(df)

    # --------------------------------------------------------
    # 3. Select latest observation for each company
    # --------------------------------------------------------

    latest_df = select_latest_company_data(df)

    # --------------------------------------------------------
    # 4. Add peer information where available
    # --------------------------------------------------------

    latest_df = add_peer_information(
        latest_df
    )

    # --------------------------------------------------------
    # 5. Create percentile-based radar data
    # --------------------------------------------------------

    radar_df = create_radar_data(
        latest_df
    )

    # --------------------------------------------------------
    # 6. Preserve peer information in output
    # --------------------------------------------------------

    metadata_columns = [
        column
        for column in [
            "peer_group_name",
            "peer_rank",
            "peer_group_size",
        ]
        if column in latest_df.columns
    ]

    for column in metadata_columns:
        radar_df[column] = latest_df[
            column
        ].values

    # --------------------------------------------------------
    # 7. Reorder columns
    # --------------------------------------------------------

    percentile_columns = [
        label.lower()
        .replace(" ", "_")
        + "_percentile"
        for label in RADAR_METRICS.keys()
    ]

    raw_columns = list(
        RADAR_METRICS.values()
    )

    ordered_columns = [
        "company_id",
        "year",
    ]

    ordered_columns += metadata_columns
    ordered_columns += percentile_columns
    ordered_columns += raw_columns

    ordered_columns = [
        column
        for column in ordered_columns
        if column in radar_df.columns
    ]

    radar_df = radar_df[
        ordered_columns
    ].copy()

    # --------------------------------------------------------
    # 8. Validate radar data
    # --------------------------------------------------------

    validate_radar_data(
        radar_df
    )

    # --------------------------------------------------------
    # 9. Save CSV
    # --------------------------------------------------------

    save_radar_data(
        radar_df
    )

    # --------------------------------------------------------
    # 10. Generate 92 PNG charts
    # --------------------------------------------------------

    generated_count = generate_charts(
        radar_df
    )

    print(
        f"Radar charts generated: "
        f"{generated_count}"
    )

    # --------------------------------------------------------
    # 11. Final validation
    # --------------------------------------------------------

    final_validation(
        radar_df,
        generated_count
    )

    # --------------------------------------------------------
    # 12. Completion message
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("D19 RADAR CHART MODULE COMPLETE")
    print("=" * 60)

    print(
        f"Radar data: {RADAR_DATA_FILE}"
    )

    print(
        f"Radar charts: {RADAR_DIR}"
    )

    print(
        f"Companies: "
        f"{radar_df['company_id'].nunique()}"
    )

    print(
        f"PNG charts: "
        f"{generated_count}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()