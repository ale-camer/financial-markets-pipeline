import argparse
import logging
import time
from datetime import datetime

import yfinance as yf

from src.extractors.alpha_vantage_extractor import AlphaVantageExtractor
from src.extractors.yfinance_extractor import DEFAULT_TICKERS
from src.loaders.db_loader import SQLiteLoader
from src.loaders.postgres_loader import PostgresLoader
from src.models.company_models import AlphaVantageCompanyRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_yfinance_fallback(ticker: str) -> dict | None:
    """Fetch company metadata using yfinance info as fallback."""
    logger.info(f"Fetching yfinance info fallback for {ticker}")
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info:
            logger.warning(f"No info returned by yfinance for {ticker}")
            return None

        # Map yfinance keys to standard format
        return {
            "Symbol": ticker.upper(),
            "Name": info.get("longName") or info.get("shortName") or ticker,
            "Sector": info.get("sector") or "Unknown",
            "Industry": info.get("industry") or "Unknown",
            "Currency": info.get("currency") or "USD",
        }
    except Exception as e:
        logger.error(
            f"Error fetching yfinance fallback for {ticker}: {e}"
        )
        return None


def process_single_ticker(
    ticker: str,
    av_extractor: AlphaVantageExtractor,
    sqlite_loader: SQLiteLoader,
    postgres_loader: PostgresLoader,
) -> tuple[bool, bool]:
    """Processes a single ticker. Returns (success, using_fallback)."""
    extracted_at = datetime.utcnow()
    source = "alpha_vantage"

    # Attempt fetching using Alpha Vantage
    raw_data = av_extractor.fetch_company_overview(ticker)
    using_fallback = False

    if not raw_data:
        # Fallback to yfinance if Alpha Vantage is rate-limited or fails
        logger.warning(
            f"Alpha Vantage fetch failed for {ticker}. "
            f"Attempting yfinance fallback..."
        )
        raw_data = fetch_yfinance_fallback(ticker)
        source = "yfinance_fallback"
        using_fallback = True

    if not raw_data:
        logger.error(
            f"Failed to fetch metadata for {ticker} from all sources."
        )
        return False, using_fallback

    # Save raw payload to SQLite raw_data table
    try:
        sqlite_loader.insert_raw_payload(
            ticker=ticker,
            source=source,
            raw_payload=[raw_data],
            extracted_at=extracted_at,
        )
        logger.info(f"Saved raw payload to SQLite raw_data for {ticker}")
    except Exception as e:
        logger.error(
            f"Failed to save raw payload to SQLite for {ticker}: {e}"
        )

    # Validate using Pydantic model
    try:
        record = AlphaVantageCompanyRecord(**raw_data)
        validated_dict = record.model_dump()
        logger.info(f"Successfully validated metadata for {ticker}")
    except Exception as e:
        logger.error(
            f"Pydantic validation failed for {ticker} data: {e}"
        )
        return False, using_fallback

    # Persist to PostgreSQL dim_companies table
    try:
        postgres_loader.insert_companies([validated_dict])
        logger.info(f"Persisted {ticker} to Postgres dim_companies.")
        return True, using_fallback
    except Exception as e:
        logger.error(
            f"Failed to save {ticker} to Postgres curated layer: {e}"
        )
        return False, using_fallback


def run_ingestion():
    parser = argparse.ArgumentParser(
        description="Ingest company fundamentals."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of tickers to process in this run.",
    )
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of specific tickers to run.",
    )
    args = parser.parse_args()

    # Determine tickers to process
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = DEFAULT_TICKERS

    sqlite_loader = SQLiteLoader()
    postgres_loader = PostgresLoader()

    logger.info("Initializing database tables...")
    sqlite_loader.init_tables()
    postgres_loader.init_tables()

    logger.info("Checking existing companies in Postgres...")
    existing_companies = postgres_loader.get_existing_company_ids()
    logger.info(f"Found {len(existing_companies)} existing companies.")

    # Filter out already loaded companies
    tickers_to_process = [
        t for t in tickers if t.upper() not in existing_companies
    ]

    if not tickers_to_process:
        logger.info("All selected tickers are already loaded. Exiting.")
        return

    if args.limit:
        tickers_to_process = tickers_to_process[: args.limit]

    logger.info(
        f"Processing metadata for {len(tickers_to_process)} tickers: "
        f"{tickers_to_process}"
    )

    av_extractor = AlphaVantageExtractor()
    processed_count = 0

    for i, ticker in enumerate(tickers_to_process):
        logger.info(
            f"[{i+1}/{len(tickers_to_process)}] Processing {ticker}..."
        )
        success, using_fallback = process_single_ticker(
            ticker, av_extractor, sqlite_loader, postgres_loader
        )
        if success:
            processed_count += 1

        # Sleep logic: only sleep if not the last item.
        if i < len(tickers_to_process) - 1:
            if not using_fallback:
                logger.info("Sleeping 12 seconds to respect AV API limit...")
                time.sleep(12)
            else:
                time.sleep(1)

    logger.info(
        f"Metadata ingestion run completed. "
        f"Successfully loaded {processed_count} company records."
    )


if __name__ == "__main__":
    run_ingestion()
