from pathlib import Path
import sqlite3
import time

from fastapi import APIRouter


router = APIRouter(
    prefix="/api/v1",
    tags=["Health"],
)

DB_PATH = Path("data/nifty100.db")
START_TIME = time.time()


def get_db_row_counts():
    """Return row counts for the ten core API database tables."""

    tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
        "market_cap",
        "documents",
        "peer_groups",
        "peer_percentiles",
        "sectors",
    ]

    conn = sqlite3.connect(DB_PATH)

    try:
        counts = {}

        for table in tables:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()

            counts[table] = row[0]

        return counts

    finally:
        conn.close()


@router.get("/health")
def health_check():
    """Return API health, database row counts, uptime, and version."""

    return {
        "status": "ok",
        "db_row_counts": get_db_row_counts(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "version": "1.0.0",
    }
