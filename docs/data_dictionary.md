# Data Dictionary — P-01

This document outlines the database schemas across the Raw, Staging, and Curated layers of the pipeline.

---

## 🗄️ SQLite Layers (Raw & Staging)

### Table: `raw_ingestion`
Stores the exact API response payloads as unstructured strings, allowing reprocessing.

| Column | Type | Description | Key |
|:---|:---|:---|:---|
| `id` | INTEGER | Auto-incrementing identifier | PK |
| `ticker` | VARCHAR(12) | Stock ticker symbol | |
| `source` | VARCHAR(24) | API source (`yahoo_finance` or `alpha_vantage`) | |
| `extracted_at` | TIMESTAMP | Timestamp of data extraction (UTC) | |
| `payload` | TEXT | Raw JSON string response | |

### Table: `stg_daily_prices`
Structured, validated records of stock price points.

| Column | Type | Description | Key |
|:---|:---|:---|:---|
| `ticker` | VARCHAR(12) | Stock ticker symbol | PK |
| `price_date` | DATE | Date of trading | PK |
| `open` | NUMERIC | Open price | |
| `high` | NUMERIC | Daily highest trade price | |
| `low` | NUMERIC | Daily lowest trade price | |
| `close` | NUMERIC | Close price | |
| `volume` | BIGINT | Traded volume | |
| `validated_at` | TIMESTAMP | UTC timestamp of validation check | |

---

## 🐘 PostgreSQL Layer (Curated OLTP)

### Table: `dim_companies`
Dimension table holding structural company information.

| Column | Type | Description | Key |
|:---|:---|:---|:---|
| `company_id` | VARCHAR(12) | Upper-case stock ticker (e.g., `AAPL`) | PK |
| `name` | VARCHAR(255) | Official registered company name | |
| `sector` | VARCHAR(100) | GICS industry sector | |
| `industry` | VARCHAR(100) | GICS industry group | |
| `currency` | VARCHAR(3) | Base reporting currency | |
| `updated_at` | TIMESTAMP | Last metadata refresh timestamp | |

### Table: `fct_daily_prices`
Fact table recording historical price activity.

| Column | Type | Description | Key |
|:---|:---|:---|:---|
| `company_id` | VARCHAR(12) | Ticker FK referencing `dim_companies` | PK, FK |
| `price_date` | DATE | Day of trade | PK |
| `open_price` | NUMERIC(12,4) | Daily opening price | |
| `high_price` | NUMERIC(12,4) | Daily high price | |
| `low_price` | NUMERIC(12,4) | Daily low price | |
| `close_price` | NUMERIC(12,4) | Daily close price | |
| `volume` | BIGINT | Number of shares traded | |
| `inserted_at` | TIMESTAMP | ETL ingestion time | |
