# Architecture Decisions (ADR) — P-01

This document outlines the system architecture and key design decisions made for the Financial Markets Daily Pipeline.

---

## 🏛️ Architecture Overview

The system runs a daily batch execution pipeline that automates metadata initialization, market data extraction, quality validation, transformation, and curated loading. 

```
                                 [Metadata Initialization]
             ┌────────────────────────────────────────────────────────┐
             │  [Alpha Vantage (Primary)] / [Local Fallback (CSV)]    │
             └───────────────────────────┬────────────────────────────┘
                                         ▼
                            [PostgreSQL: dim_companies]
                                         │
                                         │ (Filters existing company ids)
                                         ▼
                              [Daily Market Data ETL]
             ┌────────────────────────────────────────────────────────┐
             │                     [Yahoo Finance]                    │
             └───────────────────────────┬────────────────────────────┘
                                         ▼
                              [SQLite: raw_data table]
                                         │
                                         │ (Pydantic Schema Validation)
                                         ▼
                            [SQLite: staging_prices table]
                                         │
                                         │ (ETL Transformation / Mapping)
                                         ▼
             ┌───────────────────────────┴────────────────────────────┐
             │ [PostgreSQL: fct_daily_prices] & [fct_dividends]       │
             └───────────────────────────┬────────────────────────────┘
                                         ▼
                            [GCS Archive (JSON/Parquet)]
```

---

## 📄 Architectural Decision Records (ADRs)

### ADR 01: Multi-DB Ingestion (SQLite Staging, PostgreSQL Curated)
- **Status**: Approved
- **Context**: In traditional data engineering, raw/staging layers are separated from curated analytics tables to avoid resource locking, permit minor schema drifts, and allow reprocessing raw data locally without affecting the analytical database.
- **Decision**: We use **SQLite** (`data/market_data.db`) as our local Raw & Staging database. This provides zero-configuration local file storage for quick raw payloads and staging. We use **PostgreSQL** for the Curated analytics layer (using `dim_companies`, `fct_daily_prices`, and `fct_dividends` tables) to simulate a true production OLTP/OLAP database environment.
- **Consequences**: Enables simple local file archiving, lightweight storage for raw JSONs, and keeps the production PostgreSQL instance optimized for clean relational analysis and joins.

### ADR 02: Pydantic for Strict Data Validation
- **Status**: Approved
- **Context**: Financial market APIs are volatile, prone to schema modifications, formatting shifts, or returning invalid/illogical data (e.g. negative prices, missing volumes).
- **Decision**: We enforce data quality constraints at the entrance of our Staging layer using strict Pydantic models (`YFinanceOHLCVRecord` and `YFinanceExtractionPayload`). Specifically, we validate:
  - Positivity of all price metrics (`open`, `high`, `low`, `close` must be `> 0`).
  - Non-negativity of `volume`, `dividends`, and `stock_splits` (`>= 0`).
  - Internal logical coherency: `high` must be greater than or equal to `open` and `close`; `low` must be less than or equal to `open`, `close`, and `high`.
- **Consequences**: Prevents corrupted or illogical data from propagating to the curated layer. Outages or API updates will fail the pipeline cleanly with descriptive logs, rather than causing silent errors.

### ADR 03: Airflow Executor and DAG Scheduling Configuration
- **Status**: Approved
- **Context**: We require a production-ready scheduling mechanism that runs daily, prevents historic backfill loops by default, and handles intermittent external network or API rate-limiting issues gracefully.
- **Decision**: We use **LocalExecutor** backed by PostgreSQL inside our Docker environment to permit concurrent task runs. The main DAG (`financial_market_daily_pipeline`) is configured with:
  - `schedule_interval='@daily'` for regular execution.
  - `catchup=False` to prevent massive historical runs upon deployment.
  - A robust, general retry policy defined in `default_args`:
    - `retries`: 3.
    - `retry_delay`: `timedelta(minutes=2)`.
    - `retry_exponential_backoff`: `True` (intervals double after each failure to avoid rate-limiting bans or temporary server blocks).
    - `max_retry_delay`: `timedelta(minutes=10)`.
- **Consequences**: Increases pipeline resilience against API rate-limits and network hiccups, and minimizes manual operational interventions.

### ADR 04: Local Storage Archiving and optional GCS Integration
- **Status**: Approved
- **Context**: We need to preserve raw history of extraction payloads for auditability and recovery.
- **Decision**: Raw JSON payloads are saved locally in SQLite `raw_data` tables. In addition, when GCP credentials are provided, they are uploaded to Google Cloud Storage (`ale-camer-financial-markets-raw`).
- **Consequences**: Decoupled staging. If GCP credentials are not active/configured locally, the pipeline skips the GCS step and continues processing, ensuring it remains developer-friendly.
