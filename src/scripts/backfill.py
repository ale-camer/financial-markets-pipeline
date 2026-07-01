import argparse
import logging
from datetime import datetime, timedelta

from src.extractors.yfinance_extractor import YFinanceExtractor
from src.loaders.db_loader import SQLiteLoader
from src.models.price_models import (
    YFinanceExtractionPayload,
    YFinanceOHLCVRecord,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical stock data to SQLite database."
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated list of tickers to backfill.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of years of historical data to backfill.",
    )
    args = parser.parse_args()

    extractor = YFinanceExtractor()
    loader = SQLiteLoader()

    # Determine tickers to run
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = extractor.tickers

    # Determine date range
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=365 * args.years)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    logger.info(
        f"Starting backfill from {start_str} to {end_str} "
        f"for {len(tickers)} tickers."
    )

    # Initialize tables
    loader.init_tables()

    extracted_at = datetime.utcnow()

    import time
    for idx, ticker in enumerate(tickers, start=1):
        logger.info(
            f"[{idx}/{len(tickers)}] Fetching {ticker}..."
        )
        try:
            records = extractor.fetch_ohlcv(
                ticker=ticker,
                start_date=start_str,
                end_date=end_str,
            )
            if not records:
                logger.warning(
                    f"No records found for {ticker}."
                )
                if idx < len(tickers):
                    time.sleep(0.5)
                continue

            # Ingest raw payload
            loader.insert_raw_payload(
                ticker=ticker,
                source="yfinance",
                raw_payload=records,
                extracted_at=extracted_at,
            )

            # Validate and ingest staging records
            payload = YFinanceExtractionPayload(
                ticker=ticker,
                extracted_at=extracted_at,
                records=[YFinanceOHLCVRecord(**r) for r in records],
            )
            loader.insert_staging_records(payload)
            logger.info(
                f"Successfully loaded {len(records)} records for {ticker}."
            )
        except Exception as e:
            logger.error(
                f"Failed to backfill ticker {ticker}: {e}"
            )
        
        if idx < len(tickers):
            time.sleep(0.5)

    logger.info("Backfill process finished.")


if __name__ == "__main__":
    main()
