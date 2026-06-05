import logging
import os

import requests

logger = logging.getLogger(__name__)


class AlphaVantageExtractor:
    """Wrapper class around Alpha Vantage API to pull company metadata."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logger.warning(
                "Alpha Vantage API Key is missing in configuration."
            )


    def fetch_company_overview(self, symbol: str) -> dict | None:
        """Fetch the fundamental overview for a single symbol.

        Returns a dictionary of the response or None if rate limited/failed.
        """
        if not self.api_key:
            logger.error("Cannot fetch data: API Key is not configured.")
            return None

        params = {
            "function": "OVERVIEW",
            "symbol": symbol.upper(),
            "apikey": self.api_key,
        }

        try:
            logger.info(f"Requesting Alpha Vantage OVERVIEW for {symbol}")
            response = requests.get(
                self.BASE_URL, params=params, timeout=15
            )
            response.raise_for_status()
            data = response.json()

            # Handle rate-limiting message (Note or Information keys)
            if "Note" in data:
                logger.warning(
                    f"Alpha Vantage rate limit reached for {symbol}: "
                    f"{data['Note']}"
                )
                return None
            if "Information" in data:
                logger.warning(
                    f"Alpha Vantage information response for {symbol}: "
                    f"{data['Information']}"
                )
                return None

            # Handle error/invalid symbol message
            if "Error Message" in data:
                logger.error(
                    f"Alpha Vantage error for {symbol}: "
                    f"{data['Error Message']}"
                )
                return None

            # If the response is empty dict, symbol may not be found
            if not data:
                logger.warning(f"No data returned for ticker {symbol}")
                return None

            return data

        except Exception as e:
            logger.error(
                f"Error calling Alpha Vantage for {symbol}: {e}",
                exc_info=True,
            )
            return None
