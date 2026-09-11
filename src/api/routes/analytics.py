from fastapi import APIRouter, HTTPException, Query
import sqlite3
from pathlib import Path
import pandas as pd

router = APIRouter(
    prefix="/api/v1",
    tags=["Analytics"],
)

DB_PATH = Path("data/nifty100.db")


def get_connection():
    """Create a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dict(rows):
    """Convert SQLite rows to dictionaries."""
    return [dict(row) for row in rows]


@router.get("/screener")
def screener(
    min_roe: float | None = Query(None),
    max_de: float | None = Query(None),
    min_fcf: float | None = Query(None),
    sector: str | None = Query(None),
    min_rev_cagr_5yr: float | None = Query(None),
    min_pat_cagr_5yr: float | None = Query(None),
    max_pe: float | None = Query(None),
):
    """Screen N100 companies using optional financial filters."""

    if min_roe is not None and min_roe < 0:
        raise HTTPException(400, "min_roe must be >= 0")

    if max_de is not None and max_de < 0:
        raise HTTPException(400, "max_de must be >= 0")

    if min_fcf is not None and min_fcf < 0:
        raise HTTPException(400, "min_fcf must be >= 0")

    if min_rev_cagr_5yr is not None and min_rev_cagr_5yr < 0:
        raise HTTPException(400, "min_rev_cagr_5yr must be >= 0")

    if min_pat_cagr_5yr is not None and min_pat_cagr_5yr < 0:
        raise HTTPException(400, "min_pat_cagr_5yr must be >= 0")

    if max_pe is not None and max_pe <= 0:
        raise HTTPException(400, "max_pe must be > 0")

    conn = get_connection()

    try:
        query = """
            SELECT
                fr.company_id,
                c.company_name,
                s.broad_sector AS sector,
                fr.year,
                CAST(fr.return_on_equity_pct AS REAL) AS roe,
                CAST(fr.debt_to_equity AS REAL) AS debt_to_equity,
                CAST(fr.free_cash_flow_cr AS REAL) AS free_cash_flow,
                fr.revenue_cagr_5yr,
                fr.pat_cagr_5yr,
                mc.pe_ratio
            FROM financial_ratios fr
            JOIN companies c
                ON c.id = fr.company_id
            LEFT JOIN sectors s
                ON s.company_id = fr.company_id
            LEFT JOIN market_cap mc
                ON mc.company_id = fr.company_id
                AND mc.year = fr.year
            WHERE fr.year = (
                SELECT MAX(fr2.year)
                FROM financial_ratios fr2
                WHERE fr2.company_id = fr.company_id
            )
        """

        conditions = []
        params = []

        if min_roe is not None:
            conditions.append(
                "CAST(fr.return_on_equity_pct AS REAL) >= ?"
            )
            params.append(min_roe)

        if max_de is not None:
            conditions.append(
                "CAST(fr.debt_to_equity AS REAL) <= ?"
            )
            params.append(max_de)

        if min_fcf is not None:
            conditions.append(
                "CAST(fr.free_cash_flow_cr AS REAL) >= ?"
            )
            params.append(min_fcf)

        if sector:
            conditions.append(
                "LOWER(s.broad_sector) = LOWER(?)"
            )
            params.append(sector)

        if min_rev_cagr_5yr is not None:
            conditions.append(
                "fr.revenue_cagr_5yr >= ?"
            )
            params.append(min_rev_cagr_5yr)

        if min_pat_cagr_5yr is not None:
            conditions.append(
                "fr.pat_cagr_5yr >= ?"
            )
            params.append(min_pat_cagr_5yr)

        if max_pe is not None:
            conditions.append(
                "mc.pe_ratio <= ?"
            )
            params.append(max_pe)

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += """
            ORDER BY
                COALESCE(fr.composite_quality_score, 0) DESC,
                fr.company_id
        """

        rows = conn.execute(query, params).fetchall()

        return {
            "count": len(rows),
            "results": rows_to_dict(rows),
        }

    finally:
        conn.close()


@router.get("/sectors")
def get_sectors():
    """Return all broad sectors and company counts."""
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                broad_sector,
                COUNT(DISTINCT company_id) AS company_count,
                ROUND(SUM(index_weight_pct), 4)
                    AS total_index_weight_pct
            FROM sectors
            GROUP BY broad_sector
            ORDER BY broad_sector
            """
        ).fetchall()

        return {
            "count": len(rows),
            "sectors": rows_to_dict(rows),
        }

    finally:
        conn.close()


@router.get("/sectors/{sector}/companies")
def get_sector_companies(sector: str):
    """Return companies belonging to a broad sector."""
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT
                s.company_id,
                c.company_name,
                s.broad_sector,
                s.sub_sector,
                s.index_weight_pct,
                s.market_cap_category
            FROM sectors s
            JOIN companies c
                ON c.id = s.company_id
            WHERE LOWER(s.broad_sector) = LOWER(?)
            ORDER BY s.index_weight_pct DESC,
                     s.company_id
            """,
            (sector,),
        ).fetchall()

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"Sector '{sector}' not found",
            )

        return {
            "sector": sector,
            "count": len(rows),
            "companies": rows_to_dict(rows),
        }

    finally:
        conn.close()


@router.get("/peers/{group_name}")
def get_peers(group_name: str):
    """Return companies and percentile metrics for a peer group."""
    conn = get_connection()

    try:
        members = conn.execute(
            """
            SELECT
                pg.company_id,
                c.company_name,
                pg.is_benchmark
            FROM peer_groups pg
            JOIN companies c
                ON c.id = pg.company_id
            WHERE LOWER(pg.peer_group_name) = LOWER(?)
            ORDER BY pg.is_benchmark DESC,
                     pg.company_id
            """,
            (group_name,),
        ).fetchall()

        if not members:
            raise HTTPException(
                status_code=404,
                detail=f"Peer group '{group_name}' not found",
            )

        result = []

        for member in members:
            metrics = conn.execute(
                """
                SELECT
                    metric,
                    value,
                    percentile_rank,
                    year
                FROM peer_percentiles
                WHERE company_id = ?
                  AND LOWER(peer_group_name) = LOWER(?)
                ORDER BY metric
                """,
                (member["company_id"], group_name),
            ).fetchall()

            item = dict(member)
            item["metrics"] = rows_to_dict(metrics)
            result.append(item)

        return {
            "peer_group": group_name,
            "count": len(result),
            "companies": result,
        }

    finally:
        conn.close()


@router.get("/companies/{company_id}/peers/compare")
def compare_peers(company_id: str):
    """Return radar-style KPI data for a company's peer group."""
    company_id = company_id.upper()
    conn = get_connection()

    try:
        company = conn.execute(
            """
            SELECT id, company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        peer = conn.execute(
            """
            SELECT peer_group_name
            FROM peer_groups
            WHERE company_id = ?
            LIMIT 1
            """,
            (company_id,),
        ).fetchone()

        if peer is None:
            raise HTTPException(
                status_code=404,
                detail=f"No peer group found for '{company_id}'",
            )

        rows = conn.execute(
            """
            SELECT
                pp.company_id,
                c.company_name,
                pp.metric,
                pp.percentile_rank,
                pp.value,
                pp.year
            FROM peer_percentiles pp
            JOIN companies c
                ON c.id = pp.company_id
            WHERE LOWER(pp.peer_group_name) = LOWER(?)
            ORDER BY pp.company_id, pp.metric
            """,
            (peer["peer_group_name"],),
        ).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "peer_group": peer["peer_group_name"],
            "radar_data": rows_to_dict(rows),
        }

    finally:
        conn.close()


@router.get("/market-cap/{company_id}")
def get_market_cap(company_id: str):
    """Return historical market-cap and valuation data."""
    company_id = company_id.upper()
    conn = get_connection()

    try:
        company = conn.execute(
            """
            SELECT id, company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        rows = conn.execute(
            """
            SELECT
                year,
                market_cap_crore,
                enterprise_value_crore,
                pe_ratio,
                pb_ratio,
                ev_ebitda,
                dividend_yield_pct
            FROM market_cap
            WHERE company_id = ?
            ORDER BY year
            """,
            (company_id,),
        ).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "count": len(rows),
            "market_cap": rows_to_dict(rows),
        }

    finally:
        conn.close()


@router.get("/portfolio/stats")
def get_portfolio_stats():
    """Return portfolio-level statistics generated by Day 37."""
    path = Path("output/portfolio_statistics.csv")

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Portfolio statistics output not found",
        )

    df = pd.read_csv(path)

    return {
        "count": len(df),
        "statistics": df.to_dict(orient="records"),
    }


@router.get("/companies/{company_id}/documents")
def get_documents(company_id: str):
    """Return available annual-report documents."""
    company_id = company_id.upper()
    conn = get_connection()

    try:
        company = conn.execute(
            """
            SELECT id, company_name
            FROM companies
            WHERE id = ?
            """,
            (company_id,),
        ).fetchone()

        if company is None:
            raise HTTPException(
                status_code=404,
                detail=f"Company '{company_id}' not found",
            )

        rows = conn.execute(
            """
            SELECT
                year,
                annual_report
            FROM documents
            WHERE company_id = ?
            ORDER BY year DESC
            """,
            (company_id,),
        ).fetchall()

        return {
            "company_id": company_id,
            "company_name": company["company_name"],
            "count": len(rows),
            "documents": rows_to_dict(rows),
        }

    finally:
        conn.close()
