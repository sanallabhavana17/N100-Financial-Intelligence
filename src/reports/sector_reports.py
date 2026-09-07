from pathlib import Path
import sqlite3
import re

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

ROOT = Path(__file__).resolve().parents[2]

DB_PATH = ROOT / "data" / "nifty100.db"
OUTPUT_DIR = ROOT / "reports" / "sector"


def get_connection():
    return sqlite3.connect(DB_PATH)


def clean_filename(value):
    value = str(value).strip()
    value = re.sub(r"[^A-Za-z0-9]+", "_", value)
    return value.strip("_")


def load_sector_data():
    conn = get_connection()

    query = """
        SELECT
            s.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM sectors s
        LEFT JOIN companies c
            ON c.id = s.company_id
        ORDER BY s.broad_sector, s.company_id
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
            return_on_equity_pct AS roe_percentage,
            return_on_capital_employed_pct AS roce_percentage,
            free_cash_flow_cr AS free_cash_flow,
            capital_allocation_pattern AS capital_allocation
        FROM financial_ratios
        WHERE company_id IN ({placeholders})
        ORDER BY company_id, year
    """

    df = pd.read_sql_query(query, conn, params=company_ids)
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


def load_cashflow_intelligence(company_ids):
    path = ROOT / "output" / "cashflow_intelligence.xlsx"

    if not path.exists():
        return pd.DataFrame()

    try:
        df = pd.read_excel(path, sheet_name="cashflow_intelligence")
    except Exception:
        return pd.DataFrame()

    if "company_id" not in df.columns:
        return pd.DataFrame()

    return df[df["company_id"].isin(company_ids)].copy()


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


def build_styles():
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "SectorTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        "subtitle": ParagraphStyle(
            "SectorSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
            spaceAfter=6 * mm,
        ),
        "heading": ParagraphStyle(
            "SectorHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "SectorBody",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "SectorSmall",
            parent=styles["BodyText"],
            fontSize=7,
            leading=9,
        ),
    }


def header_footer(canvas, doc):
    canvas.saveState()

    width, height = A4

    canvas.setFillColor(colors.HexColor("#0B1F3A"))
    canvas.rect(0, height - 12 * mm, width, 12 * mm, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(
        15 * mm,
        height - 8 * mm,
        "N100 FINANCIAL INTELLIGENCE",
    )

    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.setFont("Helvetica", 7)

    canvas.drawString(
        15 * mm,
        8 * mm,
        "Sprint 5 — Sector Intelligence Report",
    )

    canvas.drawRightString(
        width - 15 * mm,
        8 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


def create_sector_report(sector, sector_df, ratios_df, cashflow_df):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{clean_filename(sector)}_report.pdf"
    output_path = OUTPUT_DIR / filename

    styles = build_styles()

    company_ids = sector_df["company_id"].tolist()

    merged = sector_df.merge(
        ratios_df,
        on="company_id",
        how="left",
    )

    if not cashflow_df.empty:
        cash_cols = [
            "company_id",
            "cfo_quality_label",
            "capex_label",
            "capital_allocation_label",
        ]

        available = [c for c in cash_cols if c in cashflow_df.columns]

        if "company_id" in available:
            merged = merged.merge(
                cashflow_df[available],
                on="company_id",
                how="left",
            )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=18 * mm,
        bottomMargin=14 * mm,
        title=f"N100 Sector Report — {sector}",
        author="N100 Financial Intelligence",
    )

    story = []

    # --------------------------------------------------------------
    # TITLE
    # --------------------------------------------------------------

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            f"N100 Sector Report — {sector}",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            f"{len(sector_df)} Nifty 100 companies covered in this sector",
            styles["subtitle"],
        )
    )

    # --------------------------------------------------------------
    # SECTOR SUMMARY
    # --------------------------------------------------------------

    story.append(
        Paragraph(
            "Sector Overview",
            styles["heading"],
        )
    )

    total_weight = sector_df["index_weight_pct"].sum()

    market_caps = (
        sector_df["market_cap_category"]
        .fillna("Unknown")
        .value_counts()
        .to_dict()
    )

    subsectors = (
        sector_df["sub_sector"]
        .fillna("Unknown")
        .value_counts()
        .head(8)
    )

    overview_data = [
        ["Metric", "Value"],
        ["Companies", str(len(sector_df))],
        ["Total index weight", fmt_pct(total_weight)],
        [
            "Large Cap",
            str(market_caps.get("Large Cap", 0)),
        ],
        [
            "Mid Cap",
            str(market_caps.get("Mid Cap", 0)),
        ],
        [
            "Small Cap",
            str(market_caps.get("Small Cap", 0)),
        ],
    ]

    table = Table(
        overview_data,
        colWidths=[65 * mm, 55 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F5F7FA"),
                ]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 4 * mm))

    # --------------------------------------------------------------
    # SUB-SECTORS
    # --------------------------------------------------------------

    story.append(
        Paragraph(
            "Sub-sector Composition",
            styles["heading"],
        )
    )

    sub_data = [["Sub-sector", "Companies", "Index Weight"]]

    for sub_sector, count in subsectors.items():
        weight = sector_df.loc[
            sector_df["sub_sector"].fillna("Unknown") == sub_sector,
            "index_weight_pct",
        ].sum()

        sub_data.append(
            [
                str(sub_sector),
                str(count),
                fmt_pct(weight),
            ]
        )

    table = Table(
        sub_data,
        colWidths=[80 * mm, 30 * mm, 35 * mm],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BBBBBB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F5F7FA"),
                ]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)

    # --------------------------------------------------------------
    # COMPANY TABLE
    # --------------------------------------------------------------

    story.append(
        Paragraph(
            "Company Intelligence",
            styles["heading"],
        )
    )

    company_data = [
        [
            "Ticker",
            "Company",
            "Weight",
            "5Y Sales CAGR",
            "5Y PAT CAGR",
            "ROE",
            "ROCE",
        ]
    ]

    for _, row in merged.sort_values("company_id").iterrows():

        company_data.append(
            [
                str(row["company_id"]),
                str(row["company_name"])[:30],
                fmt_pct(row["index_weight_pct"]),
                fmt_pct(row.get("revenue_cagr_5yr")),
                fmt_pct(row.get("pat_cagr_5yr")),
                fmt_pct(row.get("roe_percentage")),
                fmt_pct(row.get("roce_percentage")),
            ]
        )

    table = Table(
        company_data,
        colWidths=[
            23 * mm,
            58 * mm,
            18 * mm,
            25 * mm,
            25 * mm,
            19 * mm,
            19 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F7F8FA"),
                ]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    story.append(table)

    # --------------------------------------------------------------
    # CASH FLOW INTELLIGENCE
    # --------------------------------------------------------------

    story.append(
        Paragraph(
            "Cash Flow Intelligence",
            styles["heading"],
        )
    )

    if not cashflow_df.empty:

        cash_summary = []

        if "cfo_quality_label" in merged.columns:
            cash_summary.append(
                [
                    "CFO Quality",
                    ", ".join(
                        f"{k}: {v}"
                        for k, v in merged["cfo_quality_label"]
                        .fillna("Unknown")
                        .value_counts()
                        .items()
                    ),
                ]
            )

        if "capex_label" in merged.columns:
            cash_summary.append(
                [
                    "CapEx Intensity",
                    ", ".join(
                        f"{k}: {v}"
                        for k, v in merged["capex_label"]
                        .fillna("Unknown")
                        .value_counts()
                        .items()
                    ),
                ]
            )

        if "capital_allocation_label" in merged.columns:
            cash_summary.append(
                [
                    "Capital Allocation",
                    ", ".join(
                        f"{k}: {v}"
                        for k, v in merged["capital_allocation_label"]
                        .fillna("Unknown")
                        .value_counts()
                        .items()
                    ),
                ]
            )

        if cash_summary:
            cash_table = Table(
                cash_summary,
                colWidths=[42 * mm, 125 * mm],
            )

            cash_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF0F7")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )

            story.append(cash_table)

    # --------------------------------------------------------------
    # TOP WEIGHTED COMPANIES
    # --------------------------------------------------------------

    story.append(
        Paragraph(
            "Largest Index Weights",
            styles["heading"],
        )
    )

    top = sector_df.sort_values(
        "index_weight_pct",
        ascending=False,
    ).head(10)

    top_data = [
        ["Ticker", "Company", "Weight"]
    ]

    for _, row in top.iterrows():
        top_data.append(
            [
                str(row["company_id"]),
                str(row["company_name"])[:40],
                fmt_pct(row["index_weight_pct"]),
            ]
        )

    table = Table(
        top_data,
        colWidths=[30 * mm, 105 * mm, 30 * mm],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1F3A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BBBBBB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F5F7FA"),
                ]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)

    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "Note: Sector intelligence is generated from the N100 project database. "
            "Metrics may be unavailable for companies with limited historical coverage.",
            styles["small"],
        )
    )

    doc.build(
        story,
        onFirstPage=header_footer,
        onLaterPages=header_footer,
    )

    return output_path


def main():
    print("N100 SECTOR REPORT GENERATOR")
    print("=" * 70)
    print(f"Database : {DB_PATH}")
    print(f"Output   : {OUTPUT_DIR}")
    print()

    sector_df = load_sector_data()

    if sector_df.empty:
        raise RuntimeError("No sector data found.")

    sectors = sorted(
        sector_df["broad_sector"]
        .dropna()
        .unique()
        .tolist()
    )

    print(f"Companies loaded : {sector_df['company_id'].nunique()}")
    print(f"Sectors found    : {len(sectors)}")
    print()

    all_company_ids = sector_df["company_id"].tolist()

    ratios_df = load_latest_ratios(all_company_ids)
    cashflow_df = load_cashflow_intelligence(all_company_ids)

    generated = []
    failed = []

    for index, sector in enumerate(sectors, start=1):

        current = sector_df[
            sector_df["broad_sector"] == sector
        ].copy()

        print(
            f"[{index:02d}/{len(sectors)}] "
            f"{sector:<30} "
            f"{len(current):>2} companies",
            end=" "
        )

        try:
            path = create_sector_report(
                sector,
                current,
                ratios_df,
                cashflow_df,
            )

            size_kb = path.stat().st_size / 1024

            print(
                f"OK  {path.name:<40} "
                f"{size_kb:,.1f} KB"
            )

            generated.append(path)

        except Exception as exc:
            print(f"FAILED - {exc}")
            failed.append(
                {
                    "sector": sector,
                    "error": str(exc),
                }
            )

    print()
    print("=" * 70)
    print(f"Generated : {len(generated)}")
    print(f"Failed    : {len(failed)}")

    if failed:
        print()
        print("FAILED SECTORS")
        print("-" * 70)

        for item in failed:
            print(
                f"{item['sector']}: "
                f"{item['error']}"
            )

        raise RuntimeError(
            f"{len(failed)} sector report(s) failed."
        )

    print()
    print("Day 34 sector reports generated successfully.")


if __name__ == "__main__":
    main()