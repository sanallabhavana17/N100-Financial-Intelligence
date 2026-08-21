import pytest

from src.etl.normaliser import normalize_year, normalize_ticker


# ============================================================
# normalize_year() — 20 tests
# ============================================================

@pytest.mark.parametrize(
    "value, expected",
    [
        ("Dec 2012", 2012),
        ("Mar 2014", 2014),
        ("Mar-15", 2015),
        ("Mar-16", 2016),
        ("Dec 2020", 2020),
        ("Mar 2021", 2021),
        ("Jun 2022", 2022),
        ("Sep 2023", 2023),
        ("2024", 2024),
        (2025, 2025),
        ("Jan 2010", 2010),
        ("Feb 2011", 2011),
        ("Apr 2017", 2017),
        ("May 2018", 2018),
        ("Jul 2019", 2019),
        ("Aug 2020", 2020),
        ("Sep 2021", 2021),
        ("Oct 2022", 2022),
        ("Nov 2023", 2023),
        ("Dec 2024", 2024),
    ],
)
def test_normalize_year_valid(value, expected):
    assert normalize_year(value) == expected


def test_normalize_year_none():
    assert normalize_year(None) is None


def test_normalize_year_nan():
    import pandas as pd

    assert normalize_year(pd.NA) is None


# ============================================================
# normalize_ticker() — 15 tests
# ============================================================

@pytest.mark.parametrize(
    "value, expected",
    [
        (" abb ", "ABB"),
        ("abb", "ABB"),
        ("ABB", "ABB"),
        ("hdfcbank", "HDFCBANK"),
        (" HDFCBANK ", "HDFCBANK"),
        ("ADANIENT", "ADANIENT"),
        (" adaniensol ", "ADANIENSOL"),
        ("TCS", "TCS"),
        (" tcs ", "TCS"),
        ("INFY", "INFY"),
        (" infy ", "INFY"),
        ("RELIANCE", "RELIANCE"),
        (" reliance ", "RELIANCE"),
        ("ICICIBANK", "ICICIBANK"),
        (" ICICIBANK ", "ICICIBANK"),
    ],
)
def test_normalize_ticker_valid(value, expected):
    assert normalize_ticker(value) == expected


def test_normalize_ticker_none():
    assert normalize_ticker(None) is None


def test_normalize_ticker_nan():
    import pandas as pd

    assert normalize_ticker(pd.NA) is None