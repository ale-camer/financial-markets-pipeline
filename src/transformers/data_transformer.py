import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


class DataTransformer:
    """ETL Transformer logic to map and clean SQLite data for PostgreSQL."""

    def transform_daily_prices(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Maps staging price records to PostgreSQL fct_daily_prices format."""
        transformed = []
        for r in records:
            try:
                # Standardize date format to date object
                dt = r["date"]
                if isinstance(dt, str):
                    dt = date.fromisoformat(dt[:10])
                elif isinstance(dt, datetime):
                    dt = dt.date()
                elif not isinstance(dt, date):
                    raise ValueError(f"Invalid date format: {dt}")

                transformed.append(
                    {
                        "ticker": r["ticker"].upper(),
                        "date": dt,
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "volume": int(r["volume"]),
                    }
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(
                    "Skipping daily price record due to conversion error: "
                    f"{e}. Record: {r}"
                )
        return transformed

    def transform_dividends(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Maps staging price records to PostgreSQL fct_dividends format."""
        transformed = []
        for r in records:
            try:
                # Standardize date format to date object
                dt = r["date"]
                if isinstance(dt, str):
                    dt = date.fromisoformat(dt[:10])
                elif isinstance(dt, datetime):
                    dt = dt.date()
                elif not isinstance(dt, date):
                    raise ValueError(f"Invalid date format: {dt}")

                transformed.append(
                    {
                        "ticker": r["ticker"].upper(),
                        "date": dt,
                        "dividends": float(r.get("dividends", 0.0)),
                        "stock_splits": float(r.get("stock_splits", 0.0)),
                    }
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(
                    "Skipping dividend record due to conversion error: "
                    f"{e}. Record: {r}"
                )
        return transformed

    def transform_company(
        self, company_record: dict[str, Any]
    ) -> dict[str, Any]:
        """Maps company metadata to PostgreSQL dim_companies format."""
        # Check standard camelCase / snake_case and PascalCase variants
        symbol = (
            company_record.get("symbol")
            or company_record.get("Symbol")
            or company_record.get("company_id")
        )
        name = company_record.get("name") or company_record.get("Name")
        sector = (
            company_record.get("sector")
            or company_record.get("Sector")
            or "Unknown"
        )
        industry = (
            company_record.get("industry")
            or company_record.get("Industry")
            or "Unknown"
        )
        currency = (
            company_record.get("currency")
            or company_record.get("Currency")
            or "USD"
        )

        if not symbol or not name:
            raise ValueError(
                "Company record must contain symbol/company_id and name. "
                f"Got: {company_record}"
            )

        return {
            "company_id": symbol.upper(),
            "name": name,
            "sector": sector,
            "industry": industry,
            "currency": currency,
        }
