"""
N100 Financial Intelligence
Sprint 5 - Day 33
Company Tearsheet PDF Generator

Generates a 2-page PDF tearsheet for N100 companies.
"""

from __future__ import annotations

import sqlite3
from io import BytesIO
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
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
    Image,
)


# ============================================================================
# PATHS
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "data" / "nifty100.db"
PROS_CONS_PATH = ROOT / "output" / "pros_cons_generated.csv"
OUTPUT_DIR = ROOT / "reports" / "tearsheets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# COLORS
# ============================================================================

NAVY = colors.HexColor("#0B1F3A")
BLUE = colors.HexColor("#1F4E79")
LIGHT_BLUE = colors.HexColor("#EAF2F8")

GREEN = colors.HexColor("#198754")
LIGHT_GREEN = colors.HexColor("#EAF7EE")

RED = colors.HexColor("#C62828")
LIGHT_RED = colors.HexColor("#FDECEC")

GREY = colors.HexColor("#667085")
LIGHT_GREY = colors.HexColor("#F3F4F6")
DARK = colors.HexColor("#1F2937")
WHITE = colors.white


# ============================================================================
# DATABASE
# ============================================================================

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def load_company(company_id: str) -> pd.DataFrame:
    """
    companies.id is the company ticker/identifier.
    """

    conn = get_connection()

    query = """
        SELECT
            id AS company_id,
            company_name,
            roce_percentage,
            roe_percentage,
            face_value,
            book_value,
            website
        FROM companies
        WHERE id = ?
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=[company_id],
    )

    conn.close()

    return df


def load_profit_loss(company_id: str) -> pd.DataFrame:

    conn = get_connection()

    query = """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=[company_id],
    )

    conn.close()

    return df


def load_ratios(company_id: str) -> pd.DataFrame:

    conn = get_connection()

    query = """
        SELECT
            company_id,
            year,
            revenue_cagr_5yr,
            pat_cagr_5yr,
            return_on_equity_pct,
            return_on_capital_employed_pct,
            free_cash_flow_cr,
            cash_from_operations_cr,
            debt_to_equity,
            interest_coverage,
            capital_allocation_pattern
        FROM financial_ratios
        WHERE company_id = ?
        ORDER BY year
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=[company_id],
    )

    conn.close()

    return df


def load_balance_sheet(company_id: str) -> pd.DataFrame:

    conn = get_connection()

    query = """
        SELECT
            company_id,
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
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=[company_id],
    )

    conn.close()

    return df


def load_cashflow(company_id: str) -> pd.DataFrame:

    conn = get_connection()

    query = """
        SELECT
            company_id,
            year,
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        WHERE company_id = ?
        ORDER BY year
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=[company_id],
    )

    conn.close()

    return df


# ============================================================================
# NLP PROS / CONS
# ============================================================================

def load_pros_cons(company_id: str):

    if not PROS_CONS_PATH.exists():
        return [], []

    df = pd.read_csv(PROS_CONS_PATH)

    df["company_id"] = df["company_id"].astype(str)

    df = df[
        df["company_id"] == str(company_id)
    ].copy()

    if df.empty:
        return [], []

    df["confidence_pct"] = pd.to_numeric(
        df["confidence_pct"],
        errors="coerce",
    )

    pros = (
        df[
            df["type"]
            .astype(str)
            .str.lower()
            == "pro"
        ]
        .sort_values(
            "confidence_pct",
            ascending=False,
        )
        .head(5)
        .to_dict("records")
    )

    cons = (
        df[
            df["type"]
            .astype(str)
            .str.lower()
            == "con"
        ]
        .sort_values(
            "confidence_pct",
            ascending=False,
        )
        .head(5)
        .to_dict("records")
    )

    return pros, cons


# ============================================================================
# FORMATTING
# ============================================================================

def safe_float(value, default=None):

    try:
        if pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


def fmt_pct(value):

    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:.1f}%"


def fmt_cr(value):

    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"₹{value:,.0f} Cr"


def fmt_ratio(value):

    value = safe_float(value)

    if value is None:
        return "N/A"

    return f"{value:.2f}x"


def clean_text(value):

    if value is None:
        return ""

    if pd.isna(value):
        return ""

    return str(value).strip()


def latest_value(df, column):

    if df.empty or column not in df.columns:
        return None

    values = df[column].dropna()

    if values.empty:
        return None

    return values.iloc[-1]


# ============================================================================
# CHART HELPERS
# ============================================================================

def save_chart(fig):

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    buffer.seek(0)

    return buffer


def revenue_profit_chart(pl):

    df = pl.tail(10).copy()

    if df.empty:
        return None

    df["sales"] = pd.to_numeric(
        df["sales"],
        errors="coerce",
    )

    df["net_profit"] = pd.to_numeric(
        df["net_profit"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["sales"]
    )

    if df.empty:
        return None

    fig, ax = plt.subplots(
        figsize=(7.0, 2.35)
    )

    x = list(range(len(df)))
    width = 0.36

    ax.bar(
        [i - width / 2 for i in x],
        df["sales"],
        width=width,
        label="Revenue",
    )

    ax.bar(
        [i + width / 2 for i in x],
        df["net_profit"].fillna(0),
        width=width,
        label="Net Profit",
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        df["year"]
        .astype(int)
        .astype(str),
        fontsize=7,
    )

    ax.set_ylabel(
        "₹ Cr",
        fontsize=8,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.grid(
        axis="y",
        alpha=0.20,
    )

    ax.legend(
        fontsize=7,
        frameon=False,
        loc="upper left",
    )

    fig.tight_layout()

    return save_chart(fig)


def roe_roce_chart(ratios):

    df = ratios.tail(10).copy()

    if df.empty:
        return None

    df["roe"] = pd.to_numeric(
        df["return_on_equity_pct"],
        errors="coerce",
    )

    df["roce"] = pd.to_numeric(
        df["return_on_capital_employed_pct"],
        errors="coerce",
    )

    if df[["roe", "roce"]].dropna(
        how="all"
    ).empty:
        return None

    fig, ax1 = plt.subplots(
        figsize=(7.0, 2.35)
    )

    x = list(range(len(df)))

    ax1.plot(
        x,
        df["roe"],
        marker="o",
        linewidth=1.7,
        label="ROE",
    )

    ax1.set_ylabel(
        "ROE %",
        fontsize=8,
    )

    ax1.tick_params(
        axis="y",
        labelsize=7,
    )

    ax2 = ax1.twinx()

    ax2.plot(
        x,
        df["roce"],
        marker="s",
        linestyle="--",
        linewidth=1.7,
        label="ROCE",
    )

    ax2.set_ylabel(
        "ROCE %",
        fontsize=8,
    )

    ax2.tick_params(
        axis="y",
        labelsize=7,
    )

    ax1.set_xticks(x)

    ax1.set_xticklabels(
        df["year"]
        .astype(int)
        .astype(str),
        fontsize=7,
    )

    ax1.grid(
        axis="y",
        alpha=0.20,
    )

    lines1, labels1 = (
        ax1.get_legend_handles_labels()
    )

    lines2, labels2 = (
        ax2.get_legend_handles_labels()
    )

    ax1.legend(
        lines1 + lines2,
        labels1 + labels2,
        fontsize=7,
        frameon=False,
        loc="upper left",
    )

    fig.tight_layout()

    return save_chart(fig)


def balance_sheet_chart(bs):

    df = bs.tail(10).copy()

    if df.empty:
        return None

    cols = [
        "equity_capital",
        "reserves",
        "borrowings",
        "other_liabilities",
    ]

    for col in cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        ).fillna(0)

    fig, ax = plt.subplots(
        figsize=(7.0, 2.45)
    )

    x = list(range(len(df)))

    bottom = pd.Series(
        0.0,
        index=df.index,
    )

    for col in cols:

        values = df[col]

        ax.bar(
            x,
            values,
            bottom=bottom,
            label=col.replace(
                "_",
                " ",
            ).title(),
        )

        bottom = bottom + values

    ax.set_xticks(x)

    ax.set_xticklabels(
        df["year"]
        .astype(int)
        .astype(str),
        fontsize=7,
    )

    ax.set_ylabel(
        "₹ Cr",
        fontsize=8,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.legend(
        fontsize=6.5,
        ncol=4,
        frameon=False,
        loc="upper left",
    )

    ax.grid(
        axis="y",
        alpha=0.20,
    )

    fig.tight_layout()

    return save_chart(fig)


def cashflow_chart(cf):

    df = cf.tail(5).copy()

    if df.empty:
        return None

    cols = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
    ]

    for col in cols:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        ).fillna(0)

    fig, ax = plt.subplots(
        figsize=(7.0, 2.35)
    )

    x = list(range(len(df)))
    width = 0.23

    ax.bar(
        [i - width for i in x],
        df["operating_activity"],
        width=width,
        label="CFO",
    )

    ax.bar(
        x,
        df["investing_activity"],
        width=width,
        label="CFI",
    )

    ax.bar(
        [i + width for i in x],
        df["financing_activity"],
        width=width,
        label="CFF",
    )

    ax.axhline(
        0,
        linewidth=0.8,
    )

    ax.set_xticks(x)

    ax.set_xticklabels(
        df["year"]
        .astype(int)
        .astype(str),
        fontsize=7,
    )

    ax.set_ylabel(
        "₹ Cr",
        fontsize=8,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.legend(
        fontsize=6.5,
        ncol=3,
        frameon=False,
        loc="upper left",
    )

    ax.grid(
        axis="y",
        alpha=0.20,
    )

    fig.tight_layout()

    return save_chart(fig)


# ============================================================================
# REPORTLAB HELPERS
# ============================================================================

def make_styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="SectionTitleN100",
            parent=styles["Heading2"],
            fontSize=10,
            leading=12,
            textColor=NAVY,
            spaceBefore=2,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallN100",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=DARK,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallGreyN100",
            parent=styles["Normal"],
            fontSize=6.8,
            leading=8.5,
            textColor=GREY,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ProsN100",
            parent=styles["Normal"],
            fontSize=6.9,
            leading=8.5,
            textColor=GREEN,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ConsN100",
            parent=styles["Normal"],
            fontSize=6.9,
            leading=8.5,
            textColor=RED,
        )
    )

    return styles


def kpi_tile(title, value):

    title_style = ParagraphStyle(
        "KpiTitle",
        fontSize=6.2,
        leading=7,
        textColor=GREY,
        alignment=1,
    )

    value_style = ParagraphStyle(
        "KpiValue",
        fontSize=9.2,
        leading=11,
        textColor=NAVY,
        alignment=1,
    )

    table = Table(
        [
            [
                Paragraph(
                    f"<b>{title}</b>",
                    title_style,
                )
            ],
            [
                Paragraph(
                    f"<b>{value}</b>",
                    value_style,
                )
            ],
        ],
        colWidths=[57 * mm],
        rowHeights=[
            7 * mm,
            9 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_BLUE,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D5DFEA"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    return table


def capital_badge(pattern):

    pattern = clean_text(pattern)

    if pattern == "Shareholder Returns":

        bg = LIGHT_GREEN
        fg = GREEN

    elif pattern in (
        "Growth Funded by Debt",
        "Distress Signal",
        "Liquidating Assets",
    ):

        bg = LIGHT_RED
        fg = RED

    else:

        bg = LIGHT_BLUE
        fg = NAVY

    style = ParagraphStyle(
        "Badge",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=fg,
    )

    table = Table(
        [
            [
                Paragraph(
                    f"<b>{pattern}</b>",
                    style,
                )
            ]
        ],
        colWidths=[60 * mm],
        rowHeights=[10 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    bg,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    fg,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ]
        )
    )

    return table


def pros_cons_table(pros, cons, styles):

    rows = [
        [
            Paragraph(
                "<b>PROS</b>",
                styles["ProsN100"],
            ),
            Paragraph(
                "<b>CONS</b>",
                styles["ConsN100"],
            ),
        ]
    ]

    count = max(
        len(pros),
        len(cons),
        1,
    )

    for i in range(count):

        if i < len(pros):

            p = pros[i]

            confidence = safe_float(
                p.get("confidence_pct"),
                0,
            )

            ptext = (
                f"• {clean_text(p.get('text'))} "
                f"<font size='6' color='#667085'>"
                f"({confidence:.0f}%)"
                f"</font>"
            )

        else:

            ptext = "—"

        if i < len(cons):

            c = cons[i]

            confidence = safe_float(
                c.get("confidence_pct"),
                0,
            )

            ctext = (
                f"• {clean_text(c.get('text'))} "
                f"<font size='6' color='#667085'>"
                f"({confidence:.0f}%)"
                f"</font>"
            )

        else:

            ctext = "—"

        rows.append(
            [
                Paragraph(
                    ptext,
                    styles["ProsN100"],
                ),
                Paragraph(
                    ctext,
                    styles["ConsN100"],
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            88 * mm,
            88 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    LIGHT_GREEN,
                ),
                (
                    "BACKGROUND",
                    (1, 0),
                    (1, 0),
                    LIGHT_RED,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#D9DDE3"
                    ),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor(
                        "#E5E7EB"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    return table


# ============================================================================
# HEADER / FOOTER
# ============================================================================

def draw_header_footer(canvas, doc):

    canvas.saveState()

    canvas.setStrokeColor(
        colors.HexColor("#D9DDE3")
    )

    canvas.setLineWidth(0.5)

    canvas.line(
        15 * mm,
        9 * mm,
        A4[0] - 15 * mm,
        9 * mm,
    )

    canvas.setFont(
        "Helvetica",
        6.5,
    )

    canvas.setFillColor(GREY)

    canvas.drawString(
        15 * mm,
        5.5 * mm,
        "N100 Financial Intelligence",
    )

    canvas.drawRightString(
        A4[0] - 15 * mm,
        5.5 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================================
# TEARSHEET GENERATOR
# ============================================================================

def generate_tearsheet(company_id):

    styles = make_styles()

    company_df = load_company(company_id)

    pl = load_profit_loss(company_id)

    ratios = load_ratios(company_id)

    bs = load_balance_sheet(company_id)

    cf = load_cashflow(company_id)

    if company_df.empty:

        raise ValueError(
            f"{company_id} not found in companies table."
        )

    if len(pl) < 3:

        raise ValueError(
            f"{company_id} has fewer than 3 years of P&L data."
        )

    company = company_df.iloc[0]

    company_name = (
        clean_text(
            company["company_name"]
        )
        or company_id
    )

    pros, cons = load_pros_cons(
        company_id
    )

    revenue_cagr = latest_value(
        ratios,
        "revenue_cagr_5yr",
    )

    profit_cagr = latest_value(
        ratios,
        "pat_cagr_5yr",
    )

    roe = latest_value(
        ratios,
        "return_on_equity_pct",
    )

    roce = latest_value(
        ratios,
        "return_on_capital_employed_pct",
    )

    fcf = latest_value(
        ratios,
        "free_cash_flow_cr",
    )

    cfo = latest_value(
        ratios,
        "cash_from_operations_cr",
    )

    debt_equity = latest_value(
        ratios,
        "debt_to_equity",
    )

    interest_coverage = latest_value(
        ratios,
        "interest_coverage",
    )

    capital_allocation = latest_value(
        ratios,
        "capital_allocation_pattern",
    )

    if capital_allocation is None:
        capital_allocation = "Not Available"

    latest_year = int(
        pl.iloc[-1]["year"]
    )

    output_path = (
        OUTPUT_DIR
        / f"{company_id}_tearsheet.pdf"
    )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title=(
            f"{company_name} - "
            "N100 Financial Intelligence"
        ),
        author="N100 Financial Intelligence",
    )

    story = []

    # ========================================================================
    # PAGE 1 HEADER
    # ========================================================================

    header_style = ParagraphStyle(
        "HeaderStyle",
        fontSize=8.5,
        textColor=WHITE,
    )

    company_header_style = ParagraphStyle(
        "CompanyHeaderStyle",
        fontSize=17,
        leading=20,
        textColor=WHITE,
    )

    header = Table(
        [
            [
                Paragraph(
                    "<b>N100 FINANCIAL INTELLIGENCE</b>",
                    header_style,
                )
            ],
            [
                Paragraph(
                    f"<b>{company_name}</b>"
                    f"<br/>"
                    f"<font size='9' color='#D7E3F0'>"
                    f"{company_id}"
                    f"</font>",
                    company_header_style,
                )
            ],
        ],
        colWidths=[180 * mm],
        rowHeights=[
            8 * mm,
            18 * mm,
        ],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    NAVY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(header)

    story.append(
        Spacer(1, 4 * mm)
    )

    # ========================================================================
    # SIX KPI TILES
    # ========================================================================

    kpis = [
        (
            "Revenue CAGR (5Y)",
            fmt_pct(revenue_cagr),
        ),
        (
            "Profit CAGR (5Y)",
            fmt_pct(profit_cagr),
        ),
        (
            "ROE",
            fmt_pct(roe),
        ),
        (
            "ROCE",
            fmt_pct(roce),
        ),
        (
            "FCF",
            fmt_cr(fcf),
        ),
        (
            "CFO",
            fmt_cr(cfo),
        ),
    ]

    kpi_table = Table(
        [
            [
                kpi_tile(*kpis[0]),
                kpi_tile(*kpis[1]),
                kpi_tile(*kpis[2]),
            ],
            [
                kpi_tile(*kpis[3]),
                kpi_tile(*kpis[4]),
                kpi_tile(*kpis[5]),
            ],
        ],
        colWidths=[
            60 * mm,
            60 * mm,
            60 * mm,
        ],
        rowHeights=[
            17 * mm,
            17 * mm,
        ],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
            ]
        )
    )

    story.append(kpi_table)

    story.append(
        Spacer(1, 3 * mm)
    )

    # ========================================================================
    # REVENUE / PROFIT CHART
    # ========================================================================

    story.append(
        Paragraph(
            "10-Year Revenue & Net Profit Trend",
            styles["SectionTitleN100"],
        )
    )

    chart = revenue_profit_chart(pl)

    if chart:

        story.append(
            Image(
                chart,
                width=178 * mm,
                height=57 * mm,
            )
        )

    story.append(
        Spacer(1, 1 * mm)
    )

    # ========================================================================
    # ROE / ROCE CHART
    # ========================================================================

    story.append(
        Paragraph(
            "ROE / ROCE Trend",
            styles["SectionTitleN100"],
        )
    )

    chart = roe_roce_chart(ratios)

    if chart:

        story.append(
            Image(
                chart,
                width=178 * mm,
                height=57 * mm,
            )
        )

    story.append(
        Spacer(1, 1 * mm)
    )

    # ========================================================================
    # METADATA
    # ========================================================================

    metadata = Table(
        [
            [
                Paragraph(
                    f"<b>Latest FY:</b> {latest_year}",
                    styles["SmallN100"],
                ),
                Paragraph(
                    f"<b>Debt / Equity:</b> "
                    f"{fmt_ratio(debt_equity)}",
                    styles["SmallN100"],
                ),
                Paragraph(
                    f"<b>Interest Coverage:</b> "
                    f"{fmt_ratio(interest_coverage)}",
                    styles["SmallN100"],
                ),
            ]
        ],
        colWidths=[
            60 * mm,
            60 * mm,
            60 * mm,
        ],
    )

    metadata.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#D9DDE3"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    story.append(metadata)

    # ========================================================================
    # PAGE BREAK
    # ========================================================================

    story.append(PageBreak())

    # ========================================================================
    # PAGE 2 - BALANCE SHEET
    # ========================================================================

    story.append(
        Paragraph(
            "Balance Sheet Structure",
            styles["SectionTitleN100"],
        )
    )

    chart = balance_sheet_chart(bs)

    if chart:

        story.append(
            Image(
                chart,
                width=178 * mm,
                height=57 * mm,
            )
        )

    story.append(
        Spacer(1, 2 * mm)
    )

    # ========================================================================
    # CASH FLOW
    # ========================================================================

    story.append(
        Paragraph(
            "Cash Flow Intelligence",
            styles["SectionTitleN100"],
        )
    )

    chart = cashflow_chart(cf)

    if chart:

        story.append(
            Image(
                chart,
                width=178 * mm,
                height=55 * mm,
            )
        )

    story.append(
        Spacer(1, 2 * mm)
    )

    # ========================================================================
    # CAPITAL ALLOCATION
    # ========================================================================

    allocation_table = Table(
        [
            [
                Paragraph(
                    "<b>Capital Allocation Pattern</b>",
                    styles["SmallN100"],
                ),
                capital_badge(
                    capital_allocation
                ),
            ]
        ],
        colWidths=[
            105 * mm,
            65 * mm,
        ],
    )

    allocation_table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    story.append(
        allocation_table
    )

    story.append(
        Spacer(1, 2 * mm)
    )

    # ========================================================================
    # PROS / CONS
    # ========================================================================

    story.append(
        Paragraph(
            "NLP-Generated Pros & Cons",
            styles["SectionTitleN100"],
        )
    )

    story.append(
        pros_cons_table(
            pros,
            cons,
            styles,
        )
    )

    story.append(
        Spacer(1, 2 * mm)
    )

    # ========================================================================
    # DATA NOTE
    # ========================================================================

    note = Table(
        [
            [
                Paragraph(
                    "<b>Data note:</b> "
                    "Metrics are generated from the N100 Financial "
                    "Intelligence database and Sprint 5 NLP rules. "
                    "CAGR metrics are displayed when the required "
                    "historical period is available.",
                    styles["SmallGreyN100"],
                )
            ]
        ],
        colWidths=[178 * mm],
    )

    note.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    LIGHT_GREY,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(
                        "#D9DDE3"
                    ),
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
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    story.append(note)

    # ========================================================================
    # BUILD PDF
    # ========================================================================

    doc.build(
        story,
        onFirstPage=draw_header_footer,
        onLaterPages=draw_header_footer,
    )

    return output_path


# ============================================================================
# TEST COMPANIES
# ============================================================================

TEST_COMPANIES = [
    "TCS",
    "HDFCBANK",
    "RELIANCE",
    "SUNPHARMA",
    "TATASTEEL",
]


# ============================================================================
# MAIN
# ============================================================================

def main():

    print()
    print(
        "N100 COMPANY TEARSHEET GENERATOR"
    )
    print("=" * 70)

    print(
        f"Database : {DB_PATH}"
    )

    print(
        f"Output   : {OUTPUT_DIR}"
    )

    print()

    generated = 0
    failures = []

    for company_id in TEST_COMPANIES:

        try:

            output = generate_tearsheet(
                company_id
            )

            size_kb = (
                output.stat().st_size
                / 1024
            )

            print(
                f"{company_id:<12} "
                f"OK  "
                f"{output.name:<32} "
                f"{size_kb:,.1f} KB"
            )

            generated += 1

        except Exception as exc:

            print(
                f"{company_id:<12} "
                f"ERROR - {exc}"
            )

            failures.append(
                (
                    company_id,
                    str(exc),
                )
            )

    print()
    print("=" * 70)

    print(
        f"Generated: "
        f"{generated}/{len(TEST_COMPANIES)}"
    )

    print(
        f"Failed   : "
        f"{len(failures)}"
    )

    if failures:

        print()
        print("Failures:")

        for company_id, error in failures:

            print(
                f"  {company_id}: "
                f"{error}"
            )

        raise SystemExit(1)

    print()
    print(
        "Day 33 test tearsheets "
        "generated successfully."
    )


if __name__ == "__main__":
    main()