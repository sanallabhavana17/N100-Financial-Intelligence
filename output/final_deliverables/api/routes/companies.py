import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

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
    return conn.execute(
        "SELECT id, company_name FROM companies WHERE id = ?",
        (company_id.upper(),),
    ).fetchone()


@router.get("")
def get_companies(
    sector: str | None = Query(default=None),
    market_cap_category: str | None = Query(default=None),
    search: str | None = Query(default=None),
):
    """Return all companies with optional sector, market-cap, and search filters."""
    conn = get_connection()

    try:
        query = """
            SELECT
                c.id AS company_id,
                c.company_name,
                s.broad_sector,
                s.sub_sector,
                c.roe_percentage AS roe_pct,
                c.roce_percentage AS roce_pct,
                s.market_cap_category
            FROM companies c
            LEFT JOIN sectors s
                ON c.id = s.company_id
            WHERE 1 = 1
        """

        params = []

        if sector:
            query += """
                AND LOWER(s.broad_sector) = LOWER(?)
            """
            params.append(sector.strip())

        if market_cap_category:
            query += """
                AND LOWER(s.market_cap_category) = LOWER(?)
            """
            params.append(market_cap_category.strip())

        if search:
            query += """
                AND (
                    LOWER(c.id) LIKE LOWER(?)
                    OR LOWER(c.company_name) LIKE LOWER(?)
                )
            """
            search_pattern = f"%{search.strip()}%"
            params.extend([search_pattern, search_pattern])

        query += " ORDER BY c.id"

        rows = conn.execute(query, params).fetchall()

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
                c.id AS company_id,
                c.company_name,
                c.company_logo,
                c.chart_link,
                c.about_company,
                c.website,
                c.nse_profile,
                c.bse_profile,
                c.face_value,
                c.book_value,
                c.roce_percentage,
                c.roe_percentage,
                s.broad_sector,
                s.sub_sector
            FROM companies c
            LEFT JOIN sectors s
                ON c.id = s.company_id
            WHERE c.id = ?
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
def get_profit_and_loss(
    company_id: str,
    from_year: str | None = Query(default=None),
    to_year: str | None = Query(default=None),
):
    """Return historical profit-and-loss data with optional year filtering."""
    conn = get_connection()

    try:
        company_id = company_id.upper()
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        query = """
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
        """

        params = [company_id]

        if from_year:
            from_year_int = int(from_year[:4])
            query += " AND year >= ?"
            params.append(from_year_int)

        if to_year:
            to_year_int = int(to_year[:4])
            query += " AND year <= ?"
            params.append(to_year_int)

        query += " ORDER BY year"

        rows = conn.execute(query, params).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "count": len(rows),
            "profit_and_loss": [row_to_dict(row) for row in rows],
        }

    finally:
        conn.close()


@router.get("/{company_id}/bs")
def get_balance_sheet(
    company_id: str,
    from_year: str | None = Query(default=None),
    to_year: str | None = Query(default=None),
):
    """Return historical balance-sheet data with optional year filtering."""
    conn = get_connection()

    try:
        company_id = company_id.upper()
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        query = """
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
        """

        params = [company_id]

        if from_year:
            from_year_int = int(from_year[:4])
            query += " AND year >= ?"
            params.append(from_year_int)

        if to_year:
            to_year_int = int(to_year[:4])
            query += " AND year <= ?"
            params.append(to_year_int)

        query += " ORDER BY year"

        rows = conn.execute(query, params).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "count": len(rows),
            "balance_sheet": [row_to_dict(row) for row in rows],
        }

    finally:
        conn.close()


@router.get("/{company_id}/cashflow")
def get_cashflow(
    company_id: str,
    from_year: str | None = Query(default=None),
    to_year: str | None = Query(default=None),
):
    """Return historical cash-flow data with optional year filtering."""
    conn = get_connection()

    try:
        company_id = company_id.upper()
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        query = """
            SELECT
                year,
                operating_activity,
                investing_activity,
                financing_activity,
                net_cash_flow
            FROM cashflow
            WHERE company_id = ?
        """

        params = [company_id]

        if from_year:
            from_year_int = int(from_year[:4])
            query += " AND year >= ?"
            params.append(from_year_int)
        if to_year:
            to_year_int = int(to_year[:4])
            query += " AND year <= ?"
            params.append(to_year_int)

        rows = conn.execute(query, params).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "count": len(rows),
            "cashflow": [row_to_dict(row) for row in rows],
        }

    finally:
        conn.close()


@router.get("/{company_id}/ratios")
def get_company_ratios(
    company_id: str,
    year: str | None = Query(default=None),
):
    """Return company financial ratios with an optional year filter."""
    conn = get_connection()

    try:
        company_id = company_id.upper()
        company = company_exists(conn, company_id)

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        query = """
            SELECT *
            FROM financial_ratios
            WHERE company_id = ?
        """

        params = [company_id]

        if year:
            query += " AND year = ?"
            params.append(year)

        query += " ORDER BY year"

        rows = conn.execute(query, params).fetchall()

        return {
            "company_id": company_id,
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
