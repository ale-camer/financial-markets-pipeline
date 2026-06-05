from datetime import date, datetime
import pytest

from src.transformers.data_transformer import DataTransformer


def test_transform_daily_prices_success():
    transformer = DataTransformer()
    records = [
        {
            "ticker": "aapl",
            "date": "2023-10-01",
            "open": "170.5",
            "high": 172.0,
            "low": 169.8,
            "close": "171.2",
            "volume": 50000000,
        },
        {
            "ticker": "MSFT",
            "date": datetime(2023, 10, 2),
            "open": 315.0,
            "high": 320.0,
            "low": 314.0,
            "close": 318.5,
            "volume": "45000000",
        },
        {
            "ticker": "TSLA",
            "date": date(2023, 10, 3),
            "open": 250.0,
            "high": 255.0,
            "low": 248.0,
            "close": 252.0,
            "volume": 30000000,
        },
    ]

    transformed = transformer.transform_daily_prices(records)

    assert len(transformed) == 3
    # Check AAPL
    assert transformed[0]["ticker"] == "AAPL"
    assert transformed[0]["date"] == date(2023, 10, 1)
    assert transformed[0]["open"] == 170.5
    assert transformed[0]["close"] == 171.2
    assert transformed[0]["volume"] == 50000000

    # Check MSFT
    assert transformed[1]["ticker"] == "MSFT"
    assert transformed[1]["date"] == date(2023, 10, 2)
    assert transformed[1]["volume"] == 45000000

    # Check TSLA
    assert transformed[2]["ticker"] == "TSLA"
    assert transformed[2]["date"] == date(2023, 10, 3)


def test_transform_daily_prices_handles_failures():
    transformer = DataTransformer()
    records = [
        {
            # Valid record
            "ticker": "AAPL",
            "date": "2023-10-01",
            "open": 170.5,
            "high": 172.0,
            "low": 169.8,
            "close": 171.2,
            "volume": 50000000,
        },
        {
            # Invalid date format
            "ticker": "MSFT",
            "date": 1234567,
            "open": 315.0,
            "high": 320.0,
            "low": 314.0,
            "close": 318.5,
            "volume": 45000000,
        },
        {
            # Missing key (close)
            "ticker": "TSLA",
            "date": "2023-10-03",
            "open": 250.0,
            "high": 255.0,
            "low": 248.0,
            "volume": 30000000,
        },
        {
            # Non-convertible float/int
            "ticker": "TSLA",
            "date": "2023-10-03",
            "open": "invalid_float",
            "high": 255.0,
            "low": 248.0,
            "close": 252.0,
            "volume": 30000000,
        },
    ]

    transformed = transformer.transform_daily_prices(records)

    # Should only return the single valid record, skipping the others
    assert len(transformed) == 1
    assert transformed[0]["ticker"] == "AAPL"


def test_transform_dividends():
    transformer = DataTransformer()
    records = [
        {
            "ticker": "AAPL",
            "date": "2023-10-01",
            "dividends": "0.24",
            "stock_splits": 0.0,
        },
        {
            "ticker": "msft",
            "date": date(2023, 10, 2),
            "dividends": 0.68,
            "stock_splits": "1.0",
        },
    ]

    transformed = transformer.transform_dividends(records)

    assert len(transformed) == 2
    assert transformed[0]["ticker"] == "AAPL"
    assert transformed[0]["date"] == date(2023, 10, 1)
    assert transformed[0]["dividends"] == 0.24

    assert transformed[1]["ticker"] == "MSFT"
    assert transformed[1]["date"] == date(2023, 10, 2)
    assert transformed[1]["stock_splits"] == 1.0


def test_transform_company_success():
    transformer = DataTransformer()

    # CamelCase / PascalCase Alpha Vantage style
    av_record = {
        "Symbol": "AAPL",
        "Name": "Apple Inc.",
        "Sector": "Technology",
        "Industry": "Consumer Electronics",
        "Currency": "USD",
    }
    res_av = transformer.transform_company(av_record)
    assert res_av["company_id"] == "AAPL"
    assert res_av["name"] == "Apple Inc."
    assert res_av["sector"] == "Technology"

    # Lowercase / snake_case style
    sc_record = {
        "symbol": "msft",
        "name": "Microsoft Corp.",
        "sector": "Technology",
        "industry": "Software",
        "currency": "USD",
    }
    res_sc = transformer.transform_company(sc_record)
    assert res_sc["company_id"] == "MSFT"
    assert res_sc["name"] == "Microsoft Corp."

    # Partial record with defaults
    partial_record = {
        "company_id": "tsla",
        "name": "Tesla Inc.",
    }
    res_partial = transformer.transform_company(partial_record)
    assert res_partial["company_id"] == "TSLA"
    assert res_partial["sector"] == "Unknown"
    assert res_partial["currency"] == "USD"


def test_transform_company_failure():
    transformer = DataTransformer()

    # Missing name
    with pytest.raises(ValueError, match="Company record must contain symbol/company_id and name"):
        transformer.transform_company({"Symbol": "AAPL"})

    # Missing symbol
    with pytest.raises(ValueError, match="Company record must contain symbol/company_id and name"):
        transformer.transform_company({"Name": "Apple Inc."})
