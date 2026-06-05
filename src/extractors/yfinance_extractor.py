import logging
from datetime import date, datetime

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

DEFAULT_TICKERS = [
    # Index ETFs
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "VEA",
    "VWO",
    # Sectors
    "XLF",
    "XLK",
    "XLV",
    "XLE",
    "XLI",
    "XLY",
    "XLP",
    "XLB",
    "XLU",
    "XLRE",
    # Bonds
    "TLT",
    "BND",
    "LQD",
    "HYG",
    "SHY",
    # Commodities
    "GLD",
    "SLV",
    "USO",
    "UNG",
    "DBC",
    # Tech
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "NVDA",
    "TSLA",
    "NFLX",
    "AVGO",
    "CSCO",
    "ADBE",
    "CRM",
    "AMD",
    "INTC",
    "QCOM",
    # Finance
    "JPM",
    "BAC",
    "WFC",
    "C",
    "GS",
    "MS",
    "V",
    "MA",
    "PYPL",
    "AXP",
    "BLK",
    "BX",
    # Healthcare
    "JNJ",
    "UNH",
    "LLY",
    "ABBV",
    "PFE",
    "MRK",
    "TMO",
    "ABT",
    "DHR",
    "AMGN",
    # Consumer
    "WMT",
    "TGT",
    "COST",
    "HD",
    "NKE",
    "MCD",
    "SBUX",
    "KO",
    "PEP",
    "PG",
    "CL",
    # Industrials/Energy/Materials
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "LIN",
    "APD",
    "CAT",
    "GE",
    "HON",
    "UNP",
    "BA",
    "UPS",
    "FDX",
    # Utilities/Telecom/Real Estate
    "NEE",
    "DUKE",
    "SO",
    "D",
    "T",
    "VZ",
    "CMCSA",
    "DIS",
    "PLD",
    "AMT",
    "CCI",
    "EQIX",
    # ADR
    "TSM",
]


class YFinanceExtractor:
    """Wrapper class around yfinance to pull historical/daily price history."""

    def __init__(self, tickers: list[str] | None = None):
        self.tickers = tickers or DEFAULT_TICKERS

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        period: str | None = None,
    ) -> list[dict]:
        """Fetch OHLCV data for a single ticker.

        If start/end dates are not provided, default to '1d' or period.
        Returns a list of dicts representing daily records.
        """
        logger.info(
            f"Fetching data for {ticker} (start_date={start_date}, "
            f"end_date={end_date}, period={period})"
        )
        try:
            ticker_obj = yf.Ticker(ticker)

            # If both start and end dates are specified, use them.
            if start_date or end_date:
                df = ticker_obj.history(
                    start=start_date, end=end_date, interval="1d"
                )
            else:
                # Default to period if provided, otherwise '1d'
                df = ticker_obj.history(period=period or "1d", interval="1d")

            if df.empty:
                logger.warning(f"No data returned for ticker {ticker}")
                return []

            records = []
            for idx, row in df.iterrows():
                date_str = (
                    idx.strftime("%Y-%m-%d")
                    if isinstance(idx, (pd.Timestamp, datetime))
                    else str(idx)
                )
                records.append(
                    {
                        "date": date_str,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                        "dividends": float(row.get("Dividends", 0.0)),
                        "stock_splits": float(row.get("Stock Splits", 0.0)),
                    }
                )
            return records
        except Exception as e:
            logger.error(
                f"Error fetching data for {ticker}: {e}", exc_info=True
            )
            return []

    def fetch_all_ohlcv(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        period: str | None = None,
    ) -> dict[str, list[dict]]:
        """
        Fetch OHLCV data for all tickers configured.
        Returns a dict mapping ticker to a list of daily records.
        """
        results = {}
        for ticker in self.tickers:
            data = self.fetch_ohlcv(
                ticker, start_date=start_date, end_date=end_date, period=period
            )
            results[ticker] = data
        return results
