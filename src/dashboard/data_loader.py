from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "nifty100.db"


def load_db(
    query: str,
    params: tuple[Any, ...] = (),
) -> pd.DataFrame:
    """Run a SQL query against the NIFTY 100 SQLite database."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(
            query,
            connection,
            params=params,
        )


def get_table_names() -> list[str]:
    """Return all SQLite table names."""

    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """

    return load_db(query)["name"].tolist()


def get_companies() -> pd.DataFrame:
    """Return all companies from the database."""

    return load_db(
        """
        SELECT
            id,
            company_name,
            company_logo,
            website,
            nse_profile,
            bse_profile,
            face_value,
            book_value,
            roce_percentage,
            roe_percentage
        FROM companies
        ORDER BY company_name
        """
    )
