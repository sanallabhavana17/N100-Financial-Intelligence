from pathlib import Path

import pandas as pd

from src.etl.normaliser import normalize_year


# ==========================================================
# DATA DIRECTORY
# ==========================================================

RAW_DATA_DIR = Path("data/raw")


# ==========================================================
# CORE FILES
# ==========================================================

CORE_FILES = {
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "analysis.xlsx",
    "documents.xlsx",
    "prosandcons.xlsx",
}


# ==========================================================
# LOAD ONE EXCEL FILE
# ==========================================================

def load_excel(file_path):
    """
    Load one Excel file and return a pandas DataFrame.

    Core files:
        Header is on Excel row 2 -> header=1

    Supplementary files:
        Header is on Excel row 1 -> header=0
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Excel file not found: {file_path}"
        )

    if file_path.name in CORE_FILES:
        df = pd.read_excel(
            file_path,
            header=1
        )
    else:
        df = pd.read_excel(
            file_path,
            header=0
        )

    df = df.dropna(
        axis=0,
        how="all"
    )

    df = df.dropna(
        axis=1,
        how="all"
    )

    return df


# ==========================================================
# NORMALIZE DATAFRAME
# ==========================================================

def normalize_dataframe(df):
    """
    Apply common normalization rules to a DataFrame.
    """

    df = df.copy()

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    if "year" in df.columns:
        df["year"] = df["year"].apply(
            normalize_year
        )

    return df


# ==========================================================
# LOAD ALL RAW EXCEL FILES
# ==========================================================

def load_all_files():
    """
    Load all Excel files from data/raw.

    Returns:
        Dictionary:
            filename -> DataFrame
    """

    if not RAW_DATA_DIR.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {RAW_DATA_DIR}"
        )

    datasets = {}

    for file_path in sorted(
        RAW_DATA_DIR.glob("*.xlsx")
    ):

        df = load_excel(file_path)

        df = normalize_dataframe(df)

        datasets[file_path.name] = df

    return datasets


# ==========================================================
# MAIN TEST
# ==========================================================

if __name__ == "__main__":

    datasets = load_all_files()

    print(
        "\nExcel files loaded successfully:\n"
    )

    for filename, df in datasets.items():

        print(
            f"{filename}: "
            f"{len(df)} rows × "
            f"{len(df.columns)} columns"
        )