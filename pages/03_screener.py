import streamlit as st
import pandas as pd
from pathlib import Path

from src.dashboard.data_loader import load_db
from src.dashboard.style import configure_page, apply_styles


# ============================================================
# PAGE SETUP
# ============================================================

configure_page()
apply_styles()


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENER_FILE = PROJECT_ROOT / "output" / "screener_output.csv"


# ============================================================
# PAGE TITLE
# ============================================================

st.title("Financial Screener")

st.caption(
    "Filter and compare NIFTY 100 companies using financial "
    "screening metrics."
)


# ============================================================
# LOAD VALID COMPANY UNIVERSE FROM DATABASE
# ============================================================

companies = load_db(
    """
    SELECT
        id AS company_id,
        company_name
    FROM companies
    ORDER BY company_name
    """
)

if companies.empty:
    st.error(
        "No companies were found in the database."
    )
    st.stop()


companies["company_id"] = (
    companies["company_id"]
    .astype(str)
)


# ============================================================
# LOAD SCREENER DATA
# ============================================================

if not SCREENER_FILE.exists():

    st.error(
        f"Screener output not found: {SCREENER_FILE}"
    )

    st.stop()


df = pd.read_csv(
    SCREENER_FILE
)


if df.empty:

    st.warning(
        "Screener data is empty."
    )

    st.stop()


# ============================================================
# STANDARDIZE COMPANY ID
# ============================================================

if "company_id" not in df.columns:

    st.error(
        "The screener output does not contain "
        "'company_id'."
    )

    st.stop()


df["company_id"] = (
    df["company_id"]
    .astype(str)
    .str.strip()
)


# ============================================================
# KEEP ONLY THE REAL DATABASE COMPANY UNIVERSE
# ============================================================

valid_company_ids = set(
    companies["company_id"]
)


df = df[
    df["company_id"].isin(
        valid_company_ids
    )
].copy()


if df.empty:

    st.warning(
        "No screener records match the companies "
        "available in the database."
    )

    st.stop()


# ============================================================
# ADD OFFICIAL COMPANY NAME
# ============================================================

company_name_map = dict(
    zip(
        companies["company_id"],
        companies["company_name"],
    )
)


if "company_name" not in df.columns:

    df["company_name"] = (
        df["company_id"]
        .map(company_name_map)
    )

else:

    df["company_name"] = (
        df["company_id"]
        .map(company_name_map)
        .fillna(df["company_name"])
    )


# ============================================================
# REMOVE DUPLICATE COMPANY RECORDS
# ============================================================

if "year" in df.columns:

    df["year"] = pd.to_numeric(
        df["year"],
        errors="coerce",
    )

    df = (
        df.sort_values(
            [
                "company_id",
                "year",
            ],
            ascending=[
                True,
                False,
            ],
            na_position="last",
        )
        .drop_duplicates(
            subset=["company_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )

else:

    df = (
        df.drop_duplicates(
            subset=["company_id"],
            keep="first",
        )
        .reset_index(drop=True)
    )


# ============================================================
# COLUMN HELPERS
# ============================================================

def numeric_series(column):

    if column not in df.columns:

        return pd.Series(
            dtype="float64"
        )

    return pd.to_numeric(
        df[column],
        errors="coerce",
    )


def get_range(
    column,
    default_min=0.0,
    default_max=100.0,
):

    values = (
        numeric_series(column)
        .dropna()
    )

    if values.empty:

        return (
            float(default_min),
            float(default_max),
        )

    minimum = float(
        values.min()
    )

    maximum = float(
        values.max()
    )

    if minimum == maximum:

        maximum = minimum + 1.0

    return (
        minimum,
        maximum,
    )


# ============================================================
# PRESET DEFINITIONS
# ============================================================

PRESETS = {

    "Quality Compounder": {
        "roe": 15.0,
        "de": 2.0,
        "fcf": 0.0,
        "revenue": 10.0,
        "pat": 10.0,
        "opm": 10.0,
        "pe": 60.0,
        "pb": 15.0,
        "dividend": 0.0,
        "icr": 3.0,
    },

    "Value Pick": {
        "roe": 10.0,
        "de": 3.0,
        "fcf": 0.0,
        "revenue": 5.0,
        "pat": 5.0,
        "opm": 5.0,
        "pe": 25.0,
        "pb": 5.0,
        "dividend": 0.0,
        "icr": 2.0,
    },

    "Growth Accelerator": {
        "roe": 15.0,
        "de": 5.0,
        "fcf": 0.0,
        "revenue": 15.0,
        "pat": 15.0,
        "opm": 10.0,
        "pe": 100.0,
        "pb": 20.0,
        "dividend": 0.0,
        "icr": 2.0,
    },

    "Dividend Champion": {
        "roe": 10.0,
        "de": 3.0,
        "fcf": 0.0,
        "revenue": 5.0,
        "pat": 5.0,
        "opm": 5.0,
        "pe": 50.0,
        "pb": 15.0,
        "dividend": 2.0,
        "icr": 2.0,
    },

    "Debt-Free Blue Chip": {
        "roe": 15.0,
        "de": 0.1,
        "fcf": 0.0,
        "revenue": 8.0,
        "pat": 8.0,
        "opm": 10.0,
        "pe": 60.0,
        "pb": 15.0,
        "dividend": 0.0,
        "icr": 3.0,
    },

    "Turnaround Watch": {
        "roe": 5.0,
        "de": 5.0,
        "fcf": -500.0,
        "revenue": 0.0,
        "pat": 0.0,
        "opm": 0.0,
        "pe": 100.0,
        "pb": 20.0,
        "dividend": 0.0,
        "icr": 1.0,
    },
}


# ============================================================
# SESSION STATE DEFAULTS
# ============================================================

DEFAULTS = {

    "screener_roe": 0.0,

    "screener_de": 100.0,

    "screener_fcf": -100000.0,

    "screener_revenue": -100.0,

    "screener_pat": -100.0,

    "screener_opm": -100.0,

    "screener_pe": 1000.0,

    "screener_pb": 1000.0,

    "screener_dividend": 0.0,

    "screener_icr": -100.0,
}


for key, value in DEFAULTS.items():

    if key not in st.session_state:

        st.session_state[key] = value


if (
    "active_screener_preset"
    not in st.session_state
):

    st.session_state[
        "active_screener_preset"
    ] = "Custom"


# ============================================================
# PRESET HANDLER
# ============================================================

def apply_preset(name):

    preset = PRESETS[name]

    st.session_state[
        "screener_roe"
    ] = preset["roe"]

    st.session_state[
        "screener_de"
    ] = preset["de"]

    st.session_state[
        "screener_fcf"
    ] = preset["fcf"]

    st.session_state[
        "screener_revenue"
    ] = preset["revenue"]

    st.session_state[
        "screener_pat"
    ] = preset["pat"]

    st.session_state[
        "screener_opm"
    ] = preset["opm"]

    st.session_state[
        "screener_pe"
    ] = preset["pe"]

    st.session_state[
        "screener_pb"
    ] = preset["pb"]

    st.session_state[
        "screener_dividend"
    ] = preset["dividend"]

    st.session_state[
        "screener_icr"
    ] = preset["icr"]

    st.session_state[
        "active_screener_preset"
    ] = name


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "Screener Filters"
)

st.sidebar.caption(
    "Preset Screeners"
)


preset_names = list(
    PRESETS.keys()
)


for row_start in range(
    0,
    len(preset_names),
    2,
):

    button_columns = (
        st.sidebar.columns(2)
    )

    for offset, column in enumerate(
        button_columns
    ):

        index = (
            row_start
            + offset
        )

        if index >= len(
            preset_names
        ):

            continue

        preset_name = (
            preset_names[index]
        )

        if column.button(
            preset_name,
            key=f"preset_{index}",
            use_container_width=True,
        ):

            apply_preset(
                preset_name
            )

            st.rerun()


st.sidebar.caption(
    "Active preset: "
    + st.session_state[
        "active_screener_preset"
    ]
)


# ============================================================
# FILTER RANGES
# ============================================================

roe_min_range, roe_max_range = get_range(
    "return_on_equity_pct",
    0,
    100,
)

de_min_range, de_max_range = get_range(
    "debt_to_equity",
    0,
    20,
)

fcf_min_range, fcf_max_range = get_range(
    "free_cash_flow_cr",
    -10000,
    10000,
)

revenue_min_range, revenue_max_range = get_range(
    "revenue_cagr_5yr",
    -100,
    100,
)

pat_min_range, pat_max_range = get_range(
    "pat_cagr_5yr",
    -100,
    100,
)

opm_min_range, opm_max_range = get_range(
    "operating_profit_margin_pct",
    -100,
    100,
)

pe_min_range, pe_max_range = get_range(
    "pe_ratio",
    0,
    200,
)

pb_min_range, pb_max_range = get_range(
    "pb_ratio",
    0,
    100,
)

dividend_min_range, dividend_max_range = get_range(
    "dividend_yield_pct",
    0,
    20,
)

icr_min_range, icr_max_range = get_range(
    "interest_coverage",
    -100,
    100,
)


# ============================================================
# CLAMP FUNCTION
# ============================================================

def clamp(
    value,
    minimum,
    maximum,
):

    return min(
        max(
            float(value),
            float(minimum),
        ),
        float(maximum),
    )


# ============================================================
# CLAMP SESSION VALUES
# ============================================================

st.session_state[
    "screener_roe"
] = clamp(
    st.session_state[
        "screener_roe"
    ],
    roe_min_range,
    roe_max_range,
)

st.session_state[
    "screener_de"
] = clamp(
    st.session_state[
        "screener_de"
    ],
    de_min_range,
    de_max_range,
)

st.session_state[
    "screener_fcf"
] = clamp(
    st.session_state[
        "screener_fcf"
    ],
    fcf_min_range,
    fcf_max_range,
)

st.session_state[
    "screener_revenue"
] = clamp(
    st.session_state[
        "screener_revenue"
    ],
    revenue_min_range,
    revenue_max_range,
)

st.session_state[
    "screener_pat"
] = clamp(
    st.session_state[
        "screener_pat"
    ],
    pat_min_range,
    pat_max_range,
)

st.session_state[
    "screener_opm"
] = clamp(
    st.session_state[
        "screener_opm"
    ],
    opm_min_range,
    opm_max_range,
)

st.session_state[
    "screener_pe"
] = clamp(
    st.session_state[
        "screener_pe"
    ],
    pe_min_range,
    pe_max_range,
)

st.session_state[
    "screener_pb"
] = clamp(
    st.session_state[
        "screener_pb"
    ],
    pb_min_range,
    pb_max_range,
)

st.session_state[
    "screener_dividend"
] = clamp(
    st.session_state[
        "screener_dividend"
    ],
    dividend_min_range,
    dividend_max_range,
)

st.session_state[
    "screener_icr"
] = clamp(
    st.session_state[
        "screener_icr"
    ],
    icr_min_range,
    icr_max_range,
)


# ============================================================
# TEN REQUIRED FINANCIAL FILTERS
# ============================================================

roe_min = st.sidebar.slider(
    "ROE minimum (%)",
    min_value=float(
        roe_min_range
    ),
    max_value=float(
        roe_max_range
    ),
    key="screener_roe",
)


de_max = st.sidebar.slider(
    "Debt / Equity maximum",
    min_value=float(
        de_min_range
    ),
    max_value=float(
        de_max_range
    ),
    key="screener_de",
)


fcf_min = st.sidebar.slider(
    "Free Cash Flow minimum (Cr)",
    min_value=float(
        fcf_min_range
    ),
    max_value=float(
        fcf_max_range
    ),
    key="screener_fcf",
)


revenue_cagr_min = st.sidebar.slider(
    "Revenue CAGR 5Y minimum (%)",
    min_value=float(
        revenue_min_range
    ),
    max_value=float(
        revenue_max_range
    ),
    key="screener_revenue",
)


pat_cagr_min = st.sidebar.slider(
    "PAT CAGR 5Y minimum (%)",
    min_value=float(
        pat_min_range
    ),
    max_value=float(
        pat_max_range
    ),
    key="screener_pat",
)


opm_min = st.sidebar.slider(
    "OPM minimum (%)",
    min_value=float(
        opm_min_range
    ),
    max_value=float(
        opm_max_range
    ),
    key="screener_opm",
)


pe_max = st.sidebar.slider(
    "P/E maximum",
    min_value=float(
        pe_min_range
    ),
    max_value=float(
        pe_max_range
    ),
    key="screener_pe",
)


pb_max = st.sidebar.slider(
    "P/B maximum",
    min_value=float(
        pb_min_range
    ),
    max_value=float(
        pb_max_range
    ),
    key="screener_pb",
)


dividend_min = st.sidebar.slider(
    "Dividend Yield minimum (%)",
    min_value=float(
        dividend_min_range
    ),
    max_value=float(
        dividend_max_range
    ),
    key="screener_dividend",
)


icr_min = st.sidebar.slider(
    "Interest Coverage minimum",
    min_value=float(
        icr_min_range
    ),
    max_value=float(
        icr_max_range
    ),
    key="screener_icr",
)


# ============================================================
# FILTER FUNCTIONS
# ============================================================

def apply_min_filter(
    frame,
    column,
    value,
):

    if column not in frame.columns:

        return frame

    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    )

    return frame[
        values.notna()
        & (values >= value)
    ]


def apply_max_filter(
    frame,
    column,
    value,
):

    if column not in frame.columns:

        return frame

    values = pd.to_numeric(
        frame[column],
        errors="coerce",
    )

    return frame[
        values.notna()
        & (values <= value)
    ]


# ============================================================
# APPLY ALL FILTERS
# ============================================================

filtered = df.copy()


filtered = apply_min_filter(
    filtered,
    "return_on_equity_pct",
    roe_min,
)

filtered = apply_max_filter(
    filtered,
    "debt_to_equity",
    de_max,
)

filtered = apply_min_filter(
    filtered,
    "free_cash_flow_cr",
    fcf_min,
)

filtered = apply_min_filter(
    filtered,
    "revenue_cagr_5yr",
    revenue_cagr_min,
)

filtered = apply_min_filter(
    filtered,
    "pat_cagr_5yr",
    pat_cagr_min,
)

filtered = apply_min_filter(
    filtered,
    "operating_profit_margin_pct",
    opm_min,
)

filtered = apply_max_filter(
    filtered,
    "pe_ratio",
    pe_max,
)

filtered = apply_max_filter(
    filtered,
    "pb_ratio",
    pb_max,
)

filtered = apply_min_filter(
    filtered,
    "dividend_yield_pct",
    dividend_min,
)

filtered = apply_min_filter(
    filtered,
    "interest_coverage",
    icr_min,
)


# ============================================================
# FINAL SAFETY: ONE ROW PER COMPANY
# ============================================================

filtered = (
    filtered
    .drop_duplicates(
        subset=["company_id"],
        keep="first",
    )
    .reset_index(drop=True)
)


# ============================================================
# RESULT HEADER
# ============================================================

st.subheader(
    "Screener Results"
)


col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "NIFTY 100 Universe",
        len(companies),
    )


with col2:

    st.metric(
        "Companies Matching",
        filtered[
            "company_id"
        ].nunique(),
    )


with col3:

    if (
        not filtered.empty
        and "composite_score"
        in filtered.columns
    ):

        scores = pd.to_numeric(
            filtered[
                "composite_score"
            ],
            errors="coerce",
        )

        average_score = (
            scores.mean()
        )

    else:

        average_score = None

    st.metric(
        "Average Composite Score",
        (
            f"{average_score:.1f}"
            if pd.notna(
                average_score
            )
            else "N/A"
        ),
    )


# ============================================================
# RESULT COLUMNS
# ============================================================

display_columns = [

    "company_id",

    "company_name",

    "broad_sector",

    "composite_score",

    "return_on_equity_pct",

    "revenue_cagr_5yr",

    "pat_cagr_5yr",

    "operating_profit_margin_pct",

    "pe_ratio",

    "pb_ratio",

    "dividend_yield_pct",

    "debt_to_equity",

    "interest_coverage",

    "free_cash_flow_cr",
]


display_columns = [
    column
    for column in display_columns
    if column in filtered.columns
]


# ============================================================
# DISPLAY RESULTS
# ============================================================

if filtered.empty:

    st.warning(
        "No companies match the selected filters."
    )

else:

    visible_data = filtered[
        display_columns
    ].copy()


    # --------------------------------------------------------
    # RENAME COLUMNS
    # --------------------------------------------------------

    rename_map = {

        "company_id":
            "Company ID",

        "company_name":
            "Company Name",

        "broad_sector":
            "Sector",

        "composite_score":
            "Composite Score",

        "return_on_equity_pct":
            "ROE (%)",

        "revenue_cagr_5yr":
            "Revenue CAGR 5Y (%)",

        "pat_cagr_5yr":
            "PAT CAGR 5Y (%)",

        "operating_profit_margin_pct":
            "OPM (%)",

        "pe_ratio":
            "P/E",

        "pb_ratio":
            "P/B",

        "dividend_yield_pct":
            "Dividend Yield (%)",

        "debt_to_equity":
            "Debt / Equity",

        "interest_coverage":
            "Interest Coverage",

        "free_cash_flow_cr":
            "FCF (Cr)",
    }


    visible_data = (
        visible_data
        .rename(
            columns=rename_map
        )
    )


    # --------------------------------------------------------
    # N/A DISPLAY
    # --------------------------------------------------------

    visible_data = (
        visible_data
        .where(
            pd.notna(
                visible_data
            ),
            "N/A",
        )
    )


    st.dataframe(
        visible_data,
        use_container_width=True,
        hide_index=True,
    )


    # ========================================================
    # CSV DOWNLOAD
    # ========================================================

    csv_data = (
        visible_data
        .to_csv(
            index=False
        )
        .encode("utf-8")
    )


    st.download_button(
        label="Download Results as CSV",
        data=csv_data,
        file_name=(
            "screener_filtered_results.csv"
        ),
        mime="text/csv",
    )


# ============================================================
# ACTIVE FILTER SUMMARY
# ============================================================

with st.expander(
    "Active Filter Summary"
):

    summary = pd.DataFrame(
        [
            [
                "ROE minimum",
                roe_min,
            ],

            [
                "Debt / Equity maximum",
                de_max,
            ],

            [
                "FCF minimum",
                fcf_min,
            ],

            [
                "Revenue CAGR 5Y minimum",
                revenue_cagr_min,
            ],

            [
                "PAT CAGR 5Y minimum",
                pat_cagr_min,
            ],

            [
                "OPM minimum",
                opm_min,
            ],

            [
                "P/E maximum",
                pe_max,
            ],

            [
                "P/B maximum",
                pb_max,
            ],

            [
                "Dividend Yield minimum",
                dividend_min,
            ],

            [
                "Interest Coverage minimum",
                icr_min,
            ],
        ],
        columns=[
            "Filter",
            "Value",
        ],
    )


    st.dataframe(
        summary,
        hide_index=True,
        use_container_width=True,
    )