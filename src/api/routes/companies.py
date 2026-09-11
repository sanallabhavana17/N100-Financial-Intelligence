from fastapi import APIRouter, HTTPException
import sqlite3

router = APIRouter(prefix="/companies", tags=["Companies"])

DB_PATH = "data/nifty100.db"


def get_connection():
    """Create a connection to the N100 SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert a SQLite row to a normal dictionary."""
    return dict(row) if row is not None else None


@router.get("")
def get_companies():
    """Return all companies in the N100 universe."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                id AS company_id,
                company_name,
                website,
                face_value,
                book_value,
                roce_percentage,
                roe_percentage
            FROM companies
            ORDER BY id
            """
        ).fetchall()

        return {
            "count": len(rows),
            "companies": [row_to_dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.get("/{company_id}")
def get_company(company_id: str):
    """Return the profile information for one company."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                id AS company_id,
                company_name,
                company_logo,
                chart_link,
                about_company,
                website,
                nse_profile,
                bse_profile,
                face_value,
                book_value,
                roce_percentage,
                roe_percentage
            FROM companies
            WHERE id = ?
            """,
            (company_id.upper(),),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        return row_to_dict(row)
    finally:
        conn.close()


@router.get("/{company_id}/ratios")
def get_company_ratios(company_id: str):
    """Return the complete historical financial-ratio series for a company."""
    conn = get_connection()
    try:
        company = conn.execute(
            "SELECT id, company_name FROM companies WHERE id = ?",
            (company_id.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        rows = conn.execute(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id.upper(),),
        ).fetchall()

        return {
            "company_id": company["id"],
            "company_name": company["company_name"],
            "count": len(rows),
            "ratios": [row_to_dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.get("/{company_id}/latest")
def get_latest_company_data(company_id: str):
    """Return the latest available financial-ratio record for a company."""
    conn = get_connection()
    try:
        company = conn.execute(
            """
            SELECT
                id AS company_id,
                company_name,
                website,
                face_value,
                book_value,
                roce_percentage,
                roe_percentage
            FROM companies
            WHERE id = ?
            """,
            (company_id.upper(),),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        latest = conn.execute(
            """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
            ORDER BY year DESC
            LIMIT 1
            """,
            (company_id.upper(),),
        ).fetchone()

        return {
            "company": row_to_dict(company),
            "latest_ratio_year": latest["year"] if latest else None,
            "latest_ratios": row_to_dict(latest),
        }
    finally:
        conn.close()
