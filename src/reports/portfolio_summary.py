from pathlib import Path
import sqlite3

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# ==============================================================
# PATHS
# ==============================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "data" / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "portfolio"
OUTPUT_PATH = OUTPUT_DIR / "portfolio_summary.pdf"


# ==============================================================
# DATABASE
# ==============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def load_companies():
    conn = get_connection()

    query = """
        SELECT
            id AS company_id,
            company_name
        FROM companies
        ORDER BY id
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


def load_sectors():
    conn = get_connection()

    query = """
        SELECT
            company_id,
            broad_sector,
            sub_sector,
            index_weight_pct
        FROM sectors
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


def load_latest_ratios(company_ids):
    if not company_ids:
        return pd.DataFrame()

    conn = get_connection()

    placeholders = ",".join(["?"] * len(company_ids))

    query = f"""
        SELECT
            company_id,
            year,

            revenue_cagr_5yr,
            pat_cagr_5yr,

            return_on_equity_pct,
            return_on_capital_employed_pct,

            cfo_quality_ratio,
            cfo_quality_label,

            capex_intensity_pct,
            capex_intensity_label,

            fcf_conversion_pct,

            capital_allocation_pattern,

            debt_to_equity,
            interest_coverage,

            earnings_per_share,
            book_value_per_share,

            dividend_payout_ratio_pct,

            composite_quality_score

        FROM financial_ratios

        WHERE company_id IN ({placeholders})

        ORDER BY company_id, year
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=company_ids,
    )

    conn.close()

    if df.empty:
        return df

    latest = (
        df.sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
        .copy()
    )

    return latest


def load_historical_ratios(company_ids):
    if not company_ids:
        return pd.DataFrame()

    conn = get_connection()

    placeholders = ",".join(["?"] * len(company_ids))

    query = f"""
        SELECT
            company_id,
            year,

            revenue_cagr_5yr,
            pat_cagr_5yr,

            return_on_equity_pct,
            return_on_capital_employed_pct,

            cfo_quality_ratio,
            fcf_conversion_pct,

            composite_quality_score

        FROM financial_ratios

        WHERE company_id IN ({placeholders})

        ORDER BY company_id, year
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=company_ids,
    )

    conn.close()

    return df


# ==============================================================
# FORMATTING HELPERS
# ==============================================================

def fmt(value, decimals=1):
    if value is None or pd.isna(value):
        return "—"

    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def fmt_pct(value, decimals=1):
    if value is None or pd.isna(value):
        return "—"

    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def numeric(value):
    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def trend_arrow(current, previous):
    """
    Compare latest value against previous available year.

    ↑ = improved
    ↓ = declined
    → = unchanged / unavailable
    """

    current = numeric(current)
    previous = numeric(previous)

    if current is None or previous is None:
        return "→"

    if current > previous:
        return "↑"

    if current < previous:
        return "↓"

    return "→"


# ==============================================================
# REPORT STYLES
# ==============================================================

def build_styles():
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "PortfolioTitle",
            parent=styles["Title"],
            fontSize=21,
            leading=25,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0B1F3A"),
            spaceAfter=3 * mm,
        ),

        "company": ParagraphStyle(
            "PortfolioCompany",
            parent=styles["Heading2"],
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=2 * mm,
        ),

        "subtitle": ParagraphStyle(
            "PortfolioSubtitle",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
            spaceAfter=7 * mm,
        ),

        "heading": ParagraphStyle(
            "PortfolioHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0B1F3A"),
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
        ),

        "body": ParagraphStyle(
            "PortfolioBody",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
        ),

        "small": ParagraphStyle(
            "PortfolioSmall",
            parent=styles["BodyText"],
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#666666"),
        ),
    }


# ==============================================================
# HEADER / FOOTER
# ==============================================================

def draw_header_footer(canvas, doc):
    canvas.saveState()

    width, height = A4

    # Header
    canvas.setFillColor(colors.HexColor("#0B1F3A"))

    canvas.rect(
        0,
        height - 13 * mm,
        width,
        13 * mm,
        fill=1,
        stroke=0,
    )

    canvas.setFillColor(colors.white)

    canvas.setFont(
        "Helvetica-Bold",
        8,
    )

    canvas.drawString(
        15 * mm,
        height - 8.5 * mm,
        "N100 FINANCIAL INTELLIGENCE",
    )

    # Footer
    canvas.setFillColor(
        colors.HexColor("#555555")
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.drawString(
        15 * mm,
        7 * mm,
        "Sprint 5 — Portfolio Summary",
    )

    canvas.drawRightString(
        width - 15 * mm,
        7 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ==============================================================
# KPI TABLE
# ==============================================================

def make_kpi_table(row, previous):
    """
    Creates exactly six KPI tiles in a 2 x 3 grid.
    """

    kpis = [
        (
            "5Y Sales CAGR",
            fmt_pct(
                row.get("revenue_cagr_5yr")
            ),
            trend_arrow(
                row.get("revenue_cagr_5yr"),
                previous.get("revenue_cagr_5yr"),
            ),
        ),

        (
            "5Y PAT CAGR",
            fmt_pct(
                row.get("pat_cagr_5yr")
            ),
            trend_arrow(
                row.get("pat_cagr_5yr"),
                previous.get("pat_cagr_5yr"),
            ),
        ),

        (
            "ROE",
            fmt_pct(
                row.get("return_on_equity_pct")
            ),
            trend_arrow(
                row.get("return_on_equity_pct"),
                previous.get("return_on_equity_pct"),
            ),
        ),

        (
            "ROCE",
            fmt_pct(
                row.get(
                    "return_on_capital_employed_pct"
                )
            ),
            trend_arrow(
                row.get(
                    "return_on_capital_employed_pct"
                ),
                previous.get(
                    "return_on_capital_employed_pct"
                ),
            ),
        ),

        (
            "CFO Quality",
            fmt(
                row.get("cfo_quality_ratio")
            ),
            trend_arrow(
                row.get("cfo_quality_ratio"),
                previous.get("cfo_quality_ratio"),
            ),
        ),

        (
            "FCF Conversion",
            fmt_pct(
                row.get("fcf_conversion_pct")
            ),
            trend_arrow(
                row.get("fcf_conversion_pct"),
                previous.get("fcf_conversion_pct"),
            ),
        ),
    ]

    cells = []

    for index, (label, value, arrow) in enumerate(kpis):

        cell_style = ParagraphStyle(
            f"KPI_{index}",
            fontSize=7.5,
            leading=11,
            alignment=TA_CENTER,
        )

        cells.append(
            Paragraph(
                f"<b>{label}</b><br/>"
                f"<br/>"
                f"<font size='12'><b>{value} {arrow}</b></font>",
                cell_style,
            )
        )

    # 2 rows x 3 columns
    data = [
        [
            cells[0],
            cells[1],
            cells[2],
        ],
        [
            cells[3],
            cells[4],
            cells[5],
        ],
    ]

    table = Table(
        data,
        colWidths=[
            55 * mm,
            55 * mm,
            55 * mm,
        ],
        rowHeights=[
            25 * mm,
            25 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F5F7FA"),
                ),

                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor("#AAB4C3"),
                ),

                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD2DC"),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


# ==============================================================
# FINANCIAL INTELLIGENCE TABLE
# ==============================================================

def make_intelligence_table(row):
    data = [
        [
            "Metric",
            "Current Value",
        ],

        [
            "CFO Quality",
            (
                f"{fmt(row.get('cfo_quality_ratio'))} — "
                f"{row.get('cfo_quality_label') or '—'}"
            ),
        ],

        [
            "CapEx Intensity",
            (
                f"{fmt_pct(row.get('capex_intensity_pct'))} — "
                f"{row.get('capex_intensity_label') or '—'}"
            ),
        ],

        [
            "Capital Allocation",
            str(
                row.get(
                    "capital_allocation_pattern"
                )
                or "—"
            ),
        ],

        [
            "Debt / Equity",
            fmt(
                row.get("debt_to_equity")
            ),
        ],

        [
            "Interest Coverage",
            fmt(
                row.get("interest_coverage")
            ),
        ],

        [
            "Dividend Payout",
            fmt_pct(
                row.get(
                    "dividend_payout_ratio_pct"
                )
            ),
        ],

        [
            "Composite Quality Score",
            fmt(
                row.get(
                    "composite_quality_score"
                )
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[
            65 * mm,
            100 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0B1F3A"),
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),

                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica",
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#B8C0CC"),
                ),

                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F5F7FA"),
                    ],
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


# ==============================================================
# TREND LEGEND
# ==============================================================

def make_trend_table():
    data = [
        [
            "Indicator",
            "Meaning",
        ],

        [
            "↑",
            "Improved versus previous available year",
        ],

        [
            "↓",
            "Declined versus previous available year",
        ],

        [
            "→",
            "Flat or previous value unavailable",
        ],
    ]

    table = Table(
        data,
        colWidths=[
            35 * mm,
            130 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#0B1F3A"),
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),

                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica",
                ),

                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#B8C0CC"),
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    return table


# ==============================================================
# COMPANY PAGE
# ==============================================================

def build_company_page(
    story,
    company,
    sector_row,
    ratio_row,
    previous_row,
    styles,
):
    ticker = company["company_id"]
    company_name = company["company_name"]

    if sector_row is not None:
        sector = sector_row.get(
            "broad_sector",
            "Unknown",
        )

        sub_sector = sector_row.get(
            "sub_sector",
            "Unknown",
        )

        index_weight = sector_row.get(
            "index_weight_pct"
        )

    else:
        sector = "Unknown"
        sub_sector = "Unknown"
        index_weight = None

    year = ratio_row.get("year")

    # ----------------------------------------------------------
    # HEADER
    # ----------------------------------------------------------

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    story.append(
        Paragraph(
            str(ticker),
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            str(company_name),
            styles["company"],
        )
    )

    latest_year = (
        str(int(year))
        if pd.notna(year)
        else "—"
    )

    story.append(
        Paragraph(
            f"{sector} · {sub_sector} · "
            f"Index Weight: {fmt_pct(index_weight)} · "
            f"Latest Ratio Year: {latest_year}",
            styles["subtitle"],
        )
    )

    # ----------------------------------------------------------
    # TOP 6 KPIs
    # ----------------------------------------------------------

    story.append(
        Paragraph(
            "Top 6 KPIs",
            styles["heading"],
        )
    )

    story.append(
        make_kpi_table(
            ratio_row,
            previous_row,
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    # ----------------------------------------------------------
    # FINANCIAL INTELLIGENCE
    # ----------------------------------------------------------

    story.append(
        Paragraph(
            "Financial Intelligence",
            styles["heading"],
        )
    )

    story.append(
        make_intelligence_table(
            ratio_row
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    # ----------------------------------------------------------
    # TREND INDICATORS
    # ----------------------------------------------------------

    story.append(
        Paragraph(
            "Trend Indicators",
            styles["heading"],
        )
    )

    story.append(
        make_trend_table()
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    # ----------------------------------------------------------
    # NOTE
    # ----------------------------------------------------------

    story.append(
        Paragraph(
            "This portfolio summary is generated from the "
            "N100 Financial Intelligence project database. "
            "Values represent the latest available financial "
            "ratio year for each company. Trend arrows compare "
            "the latest available year with the previous "
            "available year.",
            styles["small"],
        )
    )


# ==============================================================
# MAIN
# ==============================================================

def main():
    print("N100 PORTFOLIO SUMMARY GENERATOR")
    print("=" * 70)

    print(
        f"Database : {DB_PATH}"
    )

    print(
        f"Output   : {OUTPUT_PATH}"
    )

    print()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ----------------------------------------------------------
    # LOAD DATA
    # ----------------------------------------------------------

    companies = load_companies()
    sectors = load_sectors()

    company_ids = (
        companies["company_id"]
        .tolist()
    )

    latest = load_latest_ratios(
        company_ids
    )

    historical = load_historical_ratios(
        company_ids
    )

    print(
        f"Companies : {len(companies)}"
    )

    print(
        f"Latest ratio rows : {len(latest)}"
    )

    print()

    # ----------------------------------------------------------
    # REPORT DOCUMENT
    # ----------------------------------------------------------

    styles = build_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,

        rightMargin=15 * mm,
        leftMargin=15 * mm,

        topMargin=18 * mm,
        bottomMargin=14 * mm,

        title="N100 Portfolio Summary",
        author="N100 Financial Intelligence",
    )

    story = []

    generated = 0
    missing_ratios = []

    # ----------------------------------------------------------
    # ONE PAGE PER COMPANY
    # ----------------------------------------------------------

    for _, company in companies.iterrows():

        ticker = company["company_id"]

        ratio_matches = latest[
            latest["company_id"] == ticker
        ]

        if ratio_matches.empty:

            missing_ratios.append(
                ticker
            )

            continue

        ratio_row = (
            ratio_matches
            .iloc[0]
        )

        # Previous available ratio year
        historical_company = (
            historical[
                historical["company_id"]
                == ticker
            ]
            .sort_values("year")
        )

        if len(historical_company) >= 2:

            previous_row = (
                historical_company
                .iloc[-2]
            )

        else:

            previous_row = (
                pd.Series(dtype=object)
            )

        # Sector information
        sector_matches = sectors[
            sectors["company_id"]
            == ticker
        ]

        if sector_matches.empty:

            sector_row = None

        else:

            sector_row = (
                sector_matches
                .iloc[0]
            )

        build_company_page(
            story=story,
            company=company,
            sector_row=sector_row,
            ratio_row=ratio_row,
            previous_row=previous_row,
            styles=styles,
        )

        generated += 1

        # Exactly one page per company
        if generated < len(companies):
            story.append(
                PageBreak()
            )

    # ----------------------------------------------------------
    # BUILD PDF
    # ----------------------------------------------------------

    doc.build(
        story,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer,
    )

    size_kb = (
        OUTPUT_PATH.stat().st_size
        / 1024
    )

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------

    print(
        "=" * 70
    )

    print(
        f"Companies expected : {len(companies)}"
    )

    print(
        f"Company pages      : {generated}"
    )

    print(
        f"Missing ratios     : {len(missing_ratios)}"
    )

    print(
        f"Output size        : {size_kb:,.1f} KB"
    )

    print(
        f"Output             : {OUTPUT_PATH}"
    )

    if missing_ratios:

        print()

        print(
            "Companies without ratio data:"
        )

        print(
            ", ".join(
                missing_ratios
            )
        )

    print()

    print(
        "=" * 70
    )

    if generated == len(companies):

        print(
            "Day 35 portfolio summary "
            "generated successfully."
        )

    else:

        print(
            "Day 35 portfolio summary "
            "generated with missing company pages."
        )


# ==============================================================
# ENTRY POINT
# ==============================================================

if __name__ == "__main__":
    main()