# Architecture Decisions (ADR) — P-01

This document outlines the system architecture and architectural decisions made for the Financial Markets Daily Pipeline.

---

## 🏛️ Architecture Overview

The system runs a daily batch execution pipeline that processes market data through three refinement stages.

```
[Yahoo Finance / Alpha Vantage]
               │
               ▼  (Raw Extract)
    [SQLite: raw_data table]
               │
               ▼  (Pydantic Validation)
   [SQLite: staging_data tables]
               │
               ▼  (Business Logic & Normalization)
[PostgreSQL: dim_companies / fct_prices] ──► [GCS Archive (JSON/Parquet)]
```

---

## 📄 Architectural Decision Records (ADRs)

### ADR 01: Multi-DB Ingestion (SQLite Staging, PostgreSQL Curated)
- **Status**: Approved
- **Context**: In traditional data engineering, raw/staging layers are separated from curated analytics tables to avoid locking resources, permit schema drift, and enable reprocessing raw files.
- **Decision**: We use **SQLite** as our local Raw & Staging database file storage. This ensures zero-config local file setup for raw tables. We use **PostgreSQL** for the Curated analytics layer to simulate a true production OLTP database environment.
- **Consequences**: Easy local file archiving, lightweight storage for raw JSONs, and robust Postgres engine for complex dimension/fact analytical joins.

### ADR 02: Pydantic for Data Validation
- **Status**: Approved
- **Context**: External financial APIs are highly volatile and prone to schema changes, missing values, or format drifts.
- **Decision**: Implement strict schema enforcement at the entrance of our Staging layer using Pydantic models. Any payload that fails validation is quarantined, and the DAG fails/retries.
- **Consequences**: We guarantee data quality inside our staging/curated tables. Outages or API updates will fail the pipeline cleanly with clear logs instead of silent corruptions.

### ADR 03: Airflow LocalExecutor
- **Status**: Approved
- **Context**: Airflow supports several executors: Sequential (default, but sqlite-backed and single-threaded), Local (multi-process on one node), and Celery/Kubernetes (highly scalable, complex setup).
- **Decision**: We use **LocalExecutor** backed by PostgreSQL.
- **Consequences**: Permits parallel task executions, runs efficiently inside a single docker-compose stack without the overhead of Redis/RabbitMQ, and maintains high reliability for small-to-medium workflows.

### ADR 04: Local Storage Archiving and optional GCS Integration
- **Status**: Approved
- **Context**: We need to keep a raw history of the extracted JSON payloads for recovery and audits.
- **Decision**: Raw JSON strings will be saved locally inside SQLite raw tables, and optionally uploaded to a Google Cloud Storage bucket (`ale-camer-financial-markets-raw`) when GCS credentials are provided.
- **Consequences**: Decoupled staging. If GCP credentials are not active/configured locally, the pipeline skips the GCS step and continues processing, ensuring it remains developer-friendly.
