"""
N100 Financial Intelligence Platform
Sprint 6 - Day 36: KMeans Clustering

Creates:
    output/cluster_labels.csv
    reports/elbow_plot.png

Clustering features:
    1. return_on_equity_pct
    2. debt_to_equity
    3. revenue_cagr_5yr
    4. fcf_cagr_5yr
    5. operating_profit_margin_pct

Processing:
    1. Load the latest financial data for each company.
    2. Calculate 5-year FCF CAGR from historical free_cash_flow_cr.
    3. Impute missing values using broad-sector medians.
    4. Apply StandardScaler.
    5. Generate elbow plot for k=2 through k=10.
    6. Run KMeans with 5 clusters and random_state=42.
    7. Assign descriptive financial archetype names.
    8. Calculate distance from centroid.
    9. Save cluster labels.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ==============================================================
# PROJECT PATHS
# ==============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "data" / "nifty100.db"

OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"

CLUSTER_OUTPUT = OUTPUT_DIR / "cluster_labels.csv"
ELBOW_OUTPUT = REPORTS_DIR / "elbow_plot.png"


# ==============================================================
# CLUSTER CONFIGURATION
# ==============================================================

FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

N_CLUSTERS = 5
RANDOM_STATE = 42


# ==============================================================
# NUMERIC CLEANING
# ==============================================================


def to_numeric(series: pd.Series) -> pd.Series:
    """Convert financial values to numeric values safely."""

    return pd.to_numeric(
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("x", "", regex=False)
        .str.replace("X", "", regex=False)
        .str.strip()
        .replace(
            {
                "": np.nan,
                "None": np.nan,
                "none": np.nan,
                "nan": np.nan,
                "NaN": np.nan,
                "NULL": np.nan,
                "null": np.nan,
                "-": np.nan,
            }
        ),
        errors="coerce",
    )


# ==============================================================
# DATABASE LOADING
# ==============================================================


def load_latest_financial_data() -> pd.DataFrame:
    """Load latest ratios and calculate five-year FCF CAGR."""

    # ----------------------------------------------------------
    # Latest financial ratio row for each company
    # ----------------------------------------------------------

    latest_query = """
        WITH ranked_ratios AS (
            SELECT
                fr.company_id,
                fr.year,
                fr.return_on_equity_pct,
                fr.debt_to_equity,
                fr.revenue_cagr_5yr,
                fr.operating_profit_margin_pct,
                fr.free_cash_flow_cr,

                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY fr.year DESC
                ) AS rn

            FROM financial_ratios fr
        )

        SELECT
            rr.company_id,
            rr.year,
            rr.return_on_equity_pct,
            rr.debt_to_equity,
            rr.revenue_cagr_5yr,
            rr.operating_profit_margin_pct,
            rr.free_cash_flow_cr,
            s.broad_sector

        FROM ranked_ratios rr

        LEFT JOIN sectors s
            ON s.company_id = rr.company_id

        WHERE rr.rn = 1

        ORDER BY rr.company_id
    """

    # ----------------------------------------------------------
    # Historical FCF data
    # ----------------------------------------------------------

    fcf_query = """
        SELECT
            company_id,
            year,
            free_cash_flow_cr
        FROM financial_ratios
        ORDER BY company_id, year
    """

    with sqlite3.connect(DB_PATH) as conn:

        latest = pd.read_sql_query(
            latest_query,
            conn,
        )

        fcf_history = pd.read_sql_query(
            fcf_query,
            conn,
        )

    # ----------------------------------------------------------
    # Convert FCF to numeric
    # ----------------------------------------------------------

    fcf_history["free_cash_flow_cr"] = to_numeric(
        fcf_history["free_cash_flow_cr"]
    )

    # Remove rows where FCF is unavailable.
    fcf_history = fcf_history.dropna(
        subset=["free_cash_flow_cr"]
    )

    # ----------------------------------------------------------
    # Calculate 5-year FCF CAGR
    # ----------------------------------------------------------

    fcf_cagr_values: list[float] = []

    for company_id in latest["company_id"]:

        company_fcf = fcf_history[
            fcf_history["company_id"] == company_id
        ].sort_values("year")

        # Not enough data.
        if len(company_fcf) < 2:
            fcf_cagr_values.append(np.nan)
            continue

        latest_row = company_fcf.iloc[-1]

        latest_year = int(latest_row["year"])
        latest_fcf = float(
            latest_row["free_cash_flow_cr"]
        )

        target_year = latest_year - 5

        # Find the closest available historical year
        # at or before the five-year target.
        previous_candidates = company_fcf[
            company_fcf["year"] <= target_year
        ]

        if previous_candidates.empty:
            fcf_cagr_values.append(np.nan)
            continue

        previous_row = previous_candidates.iloc[-1]

        previous_year = int(previous_row["year"])
        previous_fcf = float(
            previous_row["free_cash_flow_cr"]
        )

        actual_years = latest_year - previous_year

        if actual_years <= 0:
            fcf_cagr_values.append(np.nan)
            continue

        # CAGR is mathematically undefined for
        # zero or negative starting/ending FCF.
        if previous_fcf <= 0 or latest_fcf <= 0:
            fcf_cagr_values.append(np.nan)
            continue

        fcf_cagr = (
            (latest_fcf / previous_fcf)
            ** (1.0 / actual_years)
            - 1.0
        ) * 100.0

        fcf_cagr_values.append(
            float(fcf_cagr)
        )

    latest["fcf_cagr_5yr"] = fcf_cagr_values

    return latest


# ==============================================================
# DATA CLEANING
# ==============================================================


def clean_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all clustering features into numeric values."""

    result = df.copy()

    for feature in FEATURES:

        result[feature] = to_numeric(
            result[feature]
        )

    return result


# ==============================================================
# SECTOR MEDIAN IMPUTATION
# ==============================================================


def impute_sector_medians(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Impute missing feature values using broad-sector medians."""

    result = df.copy()

    global_medians: dict[str, float] = {}

    for feature in FEATURES:

        # Calculate overall median as fallback.
        global_median = result[feature].median()

        if pd.isna(global_median):

            raise ValueError(
                f"No usable values found for feature: {feature}"
            )

        global_medians[feature] = float(
            global_median
        )

        # Calculate median within each sector.
        sector_medians = (
            result.groupby(
                "broad_sector"
            )[feature]
            .transform("median")
        )

        # First use sector median.
        result[feature] = result[feature].fillna(
            sector_medians
        )

        # If sector median itself is unavailable,
        # use the overall median.
        result[feature] = result[feature].fillna(
            global_median
        )

    return result, global_medians


# ==============================================================
# STANDARD SCALING
# ==============================================================


def scale_features(
    df: pd.DataFrame,
) -> tuple[StandardScaler, np.ndarray]:
    """Standardize clustering features using StandardScaler."""

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(
        df[FEATURES]
    )

    return scaler, X_scaled


# ==============================================================
# ELBOW ANALYSIS
# ==============================================================


def calculate_elbow(
    X_scaled: np.ndarray,
) -> tuple[list[int], list[float]]:
    """Calculate KMeans inertia for k values 2 through 10."""

    k_values = list(range(2, 11))

    inertias: list[float] = []

    for k in k_values:

        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=10,
        )

        model.fit(X_scaled)

        inertias.append(
            float(model.inertia_)
        )

    return k_values, inertias


def save_elbow_plot(
    k_values: list[int],
    inertias: list[float],
) -> None:
    """Save the KMeans elbow plot."""

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.figure(
        figsize=(9, 6)
    )

    plt.plot(
        k_values,
        inertias,
        marker="o",
    )

    plt.xlabel(
        "Number of clusters (k)"
    )

    plt.ylabel(
        "Inertia"
    )

    plt.title(
        "N100 Financial Intelligence - KMeans Elbow Plot"
    )

    plt.xticks(
        k_values
    )

    plt.grid(
        True,
        alpha=0.3,
    )

    plt.tight_layout()

    plt.savefig(
        ELBOW_OUTPUT,
        dpi=160,
    )

    plt.close()


# ==============================================================
# CLUSTER PROFILE
# ==============================================================


def calculate_cluster_profile(
    df: pd.DataFrame,
    labels: np.ndarray,
) -> pd.DataFrame:
    """Calculate mean feature values for every cluster."""

    profile = df.copy()

    profile["cluster_id"] = labels

    return (
        profile.groupby(
            "cluster_id"
        )[FEATURES]
        .mean()
        .sort_index()
    )


def calculate_cluster_medians(
    df: pd.DataFrame,
    labels: np.ndarray,
) -> pd.DataFrame:
    """Calculate median feature values for every cluster."""

    profile = df.copy()

    profile["cluster_id"] = labels

    return (
        profile.groupby(
            "cluster_id"
        )[FEATURES]
        .median()
        .sort_index()
    )


# ==============================================================
# CLUSTER NAMING
# ==============================================================


def assign_cluster_names(
    profile: pd.DataFrame,
) -> dict[int, str]:
    """
    Assign descriptive financial archetype names to clusters.

    Names are assigned relative to the observed financial profile.
    """

    scoring = profile.copy()

    # ----------------------------------------------------------
    # Safe standardisation of profile characteristics.
    # ----------------------------------------------------------

    def safe_zscore(
        series: pd.Series,
    ) -> pd.Series:

        std = series.std(
            ddof=0
        )

        if std == 0 or pd.isna(std):

            return pd.Series(
                0.0,
                index=series.index,
            )

        return (
            series - series.mean()
        ) / std

    scoring[
        "roe_score"
    ] = safe_zscore(
        scoring[
            "return_on_equity_pct"
        ]
    )

    scoring[
        "debt_score"
    ] = safe_zscore(
        scoring[
            "debt_to_equity"
        ]
    )

    scoring[
        "revenue_growth_score"
    ] = safe_zscore(
        scoring[
            "revenue_cagr_5yr"
        ]
    )

    scoring[
        "fcf_growth_score"
    ] = safe_zscore(
        scoring[
            "fcf_cagr_5yr"
        ]
    )

    scoring[
        "margin_score"
    ] = safe_zscore(
        scoring[
            "operating_profit_margin_pct"
        ]
    )

    # ----------------------------------------------------------
    # Composite scores.
    # ----------------------------------------------------------

    scoring[
        "quality_score"
    ] = (
        scoring["roe_score"]
        + scoring["margin_score"]
        + scoring["fcf_growth_score"]
        + scoring["revenue_growth_score"]
        - scoring["debt_score"]
    )

    scoring[
        "growth_score"
    ] = (
        scoring["revenue_growth_score"]
        + scoring["fcf_growth_score"]
        + scoring["margin_score"]
    )

    scoring[
        "defensive_score"
    ] = (
        scoring["roe_score"]
        + scoring["margin_score"]
        - scoring["debt_score"]
    )

    scoring[
        "distress_score"
    ] = (
        scoring["debt_score"]
        - scoring["roe_score"]
        - scoring["margin_score"]
        - scoring["revenue_growth_score"]
    )

    # ----------------------------------------------------------
    # Assign five unique archetype names.
    # ----------------------------------------------------------

    remaining = set(
        int(x)
        for x in scoring.index
    )

    names: dict[int, str] = {}

    # 1. Highest overall quality.
    if remaining:

        cluster = int(
            scoring.loc[
                list(remaining),
                "quality_score",
            ].idxmax()
        )

        names[
            cluster
        ] = "High-Quality Compounders"

        remaining.remove(
            cluster
        )

    # 2. Highest growth.
    if remaining:

        cluster = int(
            scoring.loc[
                list(remaining),
                "growth_score",
            ].idxmax()
        )

        names[
            cluster
        ] = "Emerging Growth"

        remaining.remove(
            cluster
        )

    # 3. Strong defensive characteristics.
    if remaining:

        cluster = int(
            scoring.loc[
                list(remaining),
                "defensive_score",
            ].idxmax()
        )

        names[
            cluster
        ] = "Defensive Dividend Payers"

        remaining.remove(
            cluster
        )

    # 4. Weakest / highest financial stress.
    if remaining:

        cluster = int(
            scoring.loc[
                list(remaining),
                "distress_score",
            ].idxmax()
        )

        names[
            cluster
        ] = "Distressed or Turnaround"

        remaining.remove(
            cluster
        )

    # 5. Remaining profile.
    for cluster in remaining:

        names[
            int(cluster)
        ] = "Value Cyclicals"

    return names


# ==============================================================
# DISTANCE FROM CENTROID
# ==============================================================


def calculate_centroid_distances(
    X_scaled: np.ndarray,
    labels: np.ndarray,
    centroids: np.ndarray,
) -> np.ndarray:
    """Calculate Euclidean distance of every company from its centroid."""

    distances = np.zeros(
        len(X_scaled),
        dtype=float,
    )

    for index in range(
        len(X_scaled)
    ):

        cluster_id = int(
            labels[index]
        )

        distances[index] = np.linalg.norm(
            X_scaled[index]
            - centroids[cluster_id]
        )

    return distances


# ==============================================================
# MAIN
# ==============================================================


def main() -> None:
    """Run the complete Day 36 KMeans clustering pipeline."""

    print(
        "N100 KMEANS CLUSTERING"
    )

    print(
        "=" * 70
    )

    # ----------------------------------------------------------
    # Check database.
    # ----------------------------------------------------------

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Database : {DB_PATH}"
    )

    print(
        f"Output   : {CLUSTER_OUTPUT}"
    )

    print(
        f"Elbow    : {ELBOW_OUTPUT}"
    )

    print()

    # ----------------------------------------------------------
    # Load latest financial data.
    # ----------------------------------------------------------

    df = load_latest_financial_data()

    print(
        f"Companies loaded: {len(df)}"
    )

    # Sprint 6 requires all 92 companies.
    if len(df) != 92:

        raise ValueError(
            "Expected 92 companies, "
            f"but loaded {len(df)}."
        )

    if df["company_id"].nunique() != 92:

        raise ValueError(
            "Expected 92 unique company IDs."
        )

    # ----------------------------------------------------------
    # Clean feature values.
    # ----------------------------------------------------------

    df = clean_features(
        df
    )

    print()

    print(
        "Missing values BEFORE "
        "sector-median imputation:"
    )

    print(
        df[FEATURES]
        .isna()
        .sum()
        .to_string()
    )

    # ----------------------------------------------------------
    # Sector median imputation.
    # ----------------------------------------------------------

    df, global_medians = (
        impute_sector_medians(
            df
        )
    )

    print()

    print(
        "Missing values AFTER "
        "sector-median imputation:"
    )

    print(
        df[FEATURES]
        .isna()
        .sum()
        .to_string()
    )

    if (
        df[FEATURES]
        .isna()
        .any()
        .any()
    ):

        raise ValueError(
            "Missing values remain "
            "after imputation."
        )

    # ----------------------------------------------------------
    # StandardScaler.
    # ----------------------------------------------------------

    scaler, X_scaled = (
        scale_features(
            df
        )
    )

    print()

    print(
        "StandardScaler applied."
    )

    print(
        "Scaled means:",
        np.round(
            X_scaled.mean(
                axis=0
            ),
            6,
        ),
    )

    print(
        "Scaled standard deviations:",
        np.round(
            X_scaled.std(
                axis=0
            ),
            6,
        ),
    )

    # ----------------------------------------------------------
    # Elbow analysis.
    # ----------------------------------------------------------

    k_values, inertias = (
        calculate_elbow(
            X_scaled
        )
    )

    save_elbow_plot(
        k_values,
        inertias,
    )

    print()

    print(
        "Elbow analysis:"
    )

    for k, inertia in zip(
        k_values,
        inertias,
    ):

        print(
            f"  k={k}: "
            f"inertia={inertia:.4f}"
        )

    # ----------------------------------------------------------
    # KMeans with exactly 5 clusters.
    # ----------------------------------------------------------

    model = KMeans(
        n_clusters=N_CLUSTERS,
        random_state=RANDOM_STATE,
        n_init=10,
    )

    labels = model.fit_predict(
        X_scaled
    )

    # ----------------------------------------------------------
    # Distance from centroid.
    # ----------------------------------------------------------

    distances = (
        calculate_centroid_distances(
            X_scaled,
            labels,
            model.cluster_centers_,
        )
    )

    # ----------------------------------------------------------
    # Cluster profiles.
    # ----------------------------------------------------------

    mean_profile = (
        calculate_cluster_profile(
            df,
            labels,
        )
    )

    median_profile = (
        calculate_cluster_medians(
            df,
            labels,
        )
    )

    # ----------------------------------------------------------
    # Cluster names.
    # ----------------------------------------------------------

    cluster_names = (
        assign_cluster_names(
            mean_profile
        )
    )

    # ----------------------------------------------------------
    # Build output.
    # ----------------------------------------------------------

    output = pd.DataFrame(
        {
            "company_id": df[
                "company_id"
            ],
            "cluster_id": labels.astype(
                int
            ),
            "cluster_name": [
                cluster_names[
                    int(label)
                ]
                for label in labels
            ],
            "distance_from_centroid": distances,
        }
    )

    output = (
        output.sort_values(
            "company_id"
        )
        .reset_index(
            drop=True
        )
    )

    # ----------------------------------------------------------
    # Save cluster labels.
    # ----------------------------------------------------------

    output.to_csv(
        CLUSTER_OUTPUT,
        index=False,
    )

    # ----------------------------------------------------------
    # Cluster counts.
    # ----------------------------------------------------------

    counts = (
        output.groupby(
            [
                "cluster_id",
                "cluster_name",
            ]
        )
        .size()
        .reset_index(
            name="company_count"
        )
        .sort_values(
            "cluster_id"
        )
    )

    # ----------------------------------------------------------
    # Console output.
    # ----------------------------------------------------------

    print()

    print(
        "=" * 70
    )

    print(
        "CLUSTER SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        counts.to_string(
            index=False
        )
    )

    print()

    print(
        "CLUSTER PROFILES - MEAN"
    )

    print(
        "=" * 70
    )

    mean_display = (
        mean_profile.copy()
    )

    mean_display[
        "cluster_name"
    ] = [
        cluster_names[
            int(cluster)
        ]
        for cluster in mean_display.index
    ]

    mean_display = mean_display[
        [
            "cluster_name",
            *FEATURES,
        ]
    ]

    print(
        mean_display.round(
            2
        ).to_string()
    )

    print()

    print(
        "CLUSTER PROFILES - MEDIAN"
    )

    print(
        "=" * 70
    )

    median_display = (
        median_profile.copy()
    )

    median_display[
        "cluster_name"
    ] = [
        cluster_names[
            int(cluster)
        ]
        for cluster in median_display.index
    ]

    median_display = median_display[
        [
            "cluster_name",
            *FEATURES,
        ]
    ]

    print(
        median_display.round(
            2
        ).to_string()
    )

    print()

    # ----------------------------------------------------------
    # Final validation.
    # ----------------------------------------------------------

    print(
        "=" * 70
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 70
    )

    print(
        f"Output rows      : {len(output)}"
    )

    print(
        "Unique companies : "
        f"{output['company_id'].nunique()}"
    )

    print(
        "Unique clusters  : "
        f"{output['cluster_id'].nunique()}"
    )

    print(
        "Cluster IDs      : "
        f"{sorted(output['cluster_id'].unique())}"
    )

    print(
        f"Cluster output   : {CLUSTER_OUTPUT}"
    )

    print(
        f"Elbow plot       : {ELBOW_OUTPUT}"
    )

    # ----------------------------------------------------------
    # Hard validation checks.
    # ----------------------------------------------------------

    if len(output) != 92:

        raise ValueError(
            "Cluster output does not contain 92 rows."
        )

    if (
        output["company_id"]
        .nunique()
        != 92
    ):

        raise ValueError(
            "Cluster output does not contain "
            "92 unique companies."
        )

    expected_clusters = {
        0,
        1,
        2,
        3,
        4,
    }

    actual_clusters = set(
        output[
            "cluster_id"
        ].unique()
    )

    if actual_clusters != expected_clusters:

        raise ValueError(
            "Cluster IDs are not exactly "
            "0, 1, 2, 3, 4."
        )

    if (
        output[
            "cluster_name"
        ].isna()
        .any()
    ):

        raise ValueError(
            "Missing cluster names detected."
        )

    if (
        output[
            "distance_from_centroid"
        ]
        .isna()
        .any()
    ):

        raise ValueError(
            "Missing centroid distances detected."
        )

    if not CLUSTER_OUTPUT.exists():

        raise FileNotFoundError(
            "cluster_labels.csv "
            "was not created."
        )

    if not ELBOW_OUTPUT.exists():

        raise FileNotFoundError(
            "elbow_plot.png "
            "was not created."
        )

    print()

    print(
        "=" * 70
    )

    print(
        "Day 36 clustering completed successfully."
    )

    print(
        "=" * 70
    )


# ==============================================================
# ENTRY POINT
# ==============================================================


if __name__ == "__main__":
    main()