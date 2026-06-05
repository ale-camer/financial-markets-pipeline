import pytest
from pydantic import ValidationError

from src.extractors.alpha_vantage_extractor import AlphaVantageExtractor
from src.models.company_models import AlphaVantageCompanyRecord


# --- Model Tests ---


def test_company_record_validation_success():
    data = {
        "Symbol": "AAPL",
        "Name": "Apple Inc.",
        "Sector": "Technology",
        "Industry": "Consumer Electronics",
        "Currency": "USD",
    }
    record = AlphaVantageCompanyRecord(**data)
    assert record.symbol == "AAPL"
    assert record.name == "Apple Inc."
    assert record.sector == "Technology"
    assert record.industry == "Consumer Electronics"
    assert record.currency == "USD"


def test_company_record_validation_missing_fields_defaults():
    data = {
        "Symbol": "AAPL",
        "Name": "Apple Inc.",
    }
    record = AlphaVantageCompanyRecord(**data)
    assert record.symbol == "AAPL"
    assert record.name == "Apple Inc."
    assert record.sector == "Unknown"
    assert record.industry == "Unknown"
    assert record.currency == "USD"


def test_company_record_validation_failure_empty_symbol():
    data = {
        "Symbol": "",
        "Name": "Apple Inc.",
    }
    with pytest.raises(ValidationError):
        AlphaVantageCompanyRecord(**data)


# --- Extractor Tests ---


def test_alpha_vantage_extractor_success(mocker):
    mock_get = mocker.patch("requests.get")
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Symbol": "AAPL",
        "Name": "Apple Inc.",
        "Sector": "Technology",
        "Industry": "Consumer Electronics",
        "Currency": "USD",
    }
    mock_get.return_value = mock_response

    extractor = AlphaVantageExtractor(api_key="mock_key")
    data = extractor.fetch_company_overview("AAPL")

    assert data is not None
    assert data["Symbol"] == "AAPL"
    assert data["Name"] == "Apple Inc."
    mock_get.assert_called_once()


def test_alpha_vantage_extractor_rate_limit(mocker):
    mock_get = mocker.patch("requests.get")
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Note": (
            "Thank you for visiting Alpha Vantage! Our standard API "
            "rate limit is 25 requests per day."
        )
    }
    mock_get.return_value = mock_response

    extractor = AlphaVantageExtractor(api_key="mock_key")
    data = extractor.fetch_company_overview("AAPL")

    assert data is None


def test_alpha_vantage_extractor_error_msg(mocker):
    mock_get = mocker.patch("requests.get")
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Error Message": "Invalid API Key or Symbol"
    }
    mock_get.return_value = mock_response

    extractor = AlphaVantageExtractor(api_key="mock_key")
    data = extractor.fetch_company_overview("AAPL")

    assert data is None


def test_alpha_vantage_extractor_no_api_key():
    extractor = AlphaVantageExtractor(api_key=None)
    # Ensure extractor handles missing API key gracefully without crashes
    extractor.api_key = None
    data = extractor.fetch_company_overview("AAPL")
    assert data is None
