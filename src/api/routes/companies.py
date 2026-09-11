from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import sqlite3
from pathlib import Path

router = APIRouter(
    prefix="/api/v1/companies",
    tags=["Companies"],
)

DB_PATH = Path("data/nifty100.db")


def get_connection():
    """Create a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    """Convert a SQLite row to a dictionary."""
    return dict(row) if row is not None else None


def company_exists(conn, company_id):
    """Check whether a company exists."""
    row = conn.execute(
        "SELECT id, company_name FROM companies WHERE id = ?",
        (company_id.upper(),),
    ).fetchone()
    return row


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


@router.get("/{company_id}/pl")
def get_profit_and_loss(company_id: str):
    """Return historical profit and loss data."""
    conn = get_connection()
    try:
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        rows = conn.execute(
            """
            SELECT
                year,
                sales,
                expenses,
                operating_profit,
                opm_percentage,
                other_income,
                interest,
                depreciation,
                profit_before_tax,
                tax_percentage,
                net_profit,
                eps,
                dividend_payout
            FROM profitandloss
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id.upper(),),
        ).fetchall()

        return {
            "company_id": company_id.upper(),
            "company_name": company["company_name"],
            "count": len(rows),
            "profit_and_loss": [row_to_dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.get("/{company_id}/bs")
def get_balance_sheet(company_id: str):
    """Return historical balance sheet data."""
    conn = get_connection()
    try:
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        rows = conn.execute(
            """
            SELECT
                year,
                equity_capital,
                reserves,
                borrowings,
                other_liabilities,
                total_liabilities,
                fixed_assets,
                cwip,
                investments,
                other_asset,
                total_assets
            FROM balancesheet
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id.upper(),),
        ).fetchall()

        return {
            "company_id": company_id.upper(),
            "company_name": company["company_name"],
            "count": len(rows),
            "balance_sheet": [row_to_dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.get("/{company_id}/cashflow")
def get_cashflow(company_id: str):
    """Return historical cash flow data."""
    conn = get_connection()
    try:
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        rows = conn.execute(
            """
            SELECT
                year,
                operating_activity,
                investing_activity,
                financing_activity,
                net_cash_flow
            FROM cashflow
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id.upper(),),
        ).fetchall()

        return {
            "company_id": company_id.upper(),
            "company_name": company["company_name"],
            "count": len(rows),
            "cashflow": [row_to_dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.get("/{company_id}/ratios")
def get_company_ratios(company_id: str):
    """Return the complete historical financial-ratio series."""
    conn = get_connection()
    try:
        company = company_exists(conn, company_id)

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
            "company_id": company_id.upper(),
            "company_name": company["company_name"],
            "count": len(rows),
            "ratios": [row_to_dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.get("/{company_id}/tearsheet")
def get_tearsheet(company_id: str):
    """Return the pre-generated company tearsheet PDF."""
    company_id = company_id.upper()

    conn = get_connection()
    try:
        company = company_exists(conn, company_id)
    finally:
        conn.close()

    if company is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{company_id}' not found",
        )

    pdf_path = Path("reports/tearsheets") / f"{company_id}_tearsheet.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet for '{company_id}' is not available",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )
