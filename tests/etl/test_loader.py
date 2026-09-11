import pandas as pd
import pytest

from src.etl.loader import load_excel, load_all_files, normalize_dataframe


def test_load_all_files_returns_dictionary():
    datasets = load_all_files()
    assert isinstance(datasets, dict)


def test_companies_row_count():
    datasets = load_all_files()
    assert len(datasets["companies.xlsx"]) == 92


def test_profitandloss_row_count():
    datasets = load_all_files()
    assert len(datasets["profitandloss.xlsx"]) == 1276


def test_balancesheet_row_count():
    datasets = load_all_files()
    assert len(datasets["balancesheet.xlsx"]) == 1312


def test_cashflow_row_count():
    datasets = load_all_files()
    assert len(datasets["cashflow.xlsx"]) == 1187


def test_market_cap_row_count():
    datasets = load_all_files()
    assert len(datasets["market_cap.xlsx"]) == 552


def test_companies_required_columns():
    datasets = load_all_files()
    expected = {
        "id",
        "company_name",
        "roe_percentage",
        "roce_percentage",
    }
    assert expected.issubset(set(datasets["companies.xlsx"].columns))


def test_profitandloss_required_columns():
    datasets = load_all_files()
    expected = {
        "company_id",
        "year",
        "sales",
        "operating_profit",
        "net_profit",
        "eps",
    }
    assert expected.issubset(set(datasets["profitandloss.xlsx"].columns))


def test_normalize_dataframe_strips_column_names():
    df = pd.DataFrame(
        {
            " company_id ": ["TCS"],
            " year ": ["Mar 2024"],
        }
    )

    result = normalize_dataframe(df)

    assert list(result.columns) == ["company_id", "year"]
    assert result.loc[0, "year"] == 2024


def test_load_excel_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_excel("data/raw/file_that_does_not_exist.xlsx")


def test_load_all_files_contains_core_datasets():
    datasets = load_all_files()

    expected_files = {
        "companies.xlsx",
        "profitandloss.xlsx",
        "balancesheet.xlsx",
        "cashflow.xlsx",
        "market_cap.xlsx",
        "peer_groups.xlsx",
        "sectors.xlsx",
        "stock_prices.xlsx",
    }

    assert expected_files.issubset(set(datasets.keys()))
