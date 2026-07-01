# Data Dictionary — P-01

This document outlines the database schemas across the Raw, Staging, and Curated layers of the pipeline, including exact column constraints, validations, and referential integrity policies.

---

## 🗄️ SQLite Layers (Raw & Staging)

These layers use SQLite for zero-config local file storage (`data/market_data.db`) to enable lightweight ingestion and raw history preservation.

### Table: `raw_data`
Stores the exact API response payloads as unstructured strings, allowing easy reprocessing in case of pipeline failures or model changes.

| Column | Type | Nullability | Key | Description |
|:---|:---|:---|:---|:---|
| `id` | INTEGER | NOT NULL | PK (AUTOINCREMENT) | Auto-incrementing identifier for each extraction run |
| `ticker` | TEXT | NOT NULL | | Stock ticker symbol (e.g., `AAPL`) |
| `source` | TEXT | NOT NULL | | API source name (`yfinance` or `alpha_vantage`) |
| `payload` | TEXT | NOT NULL | | Raw JSON response payload from the API |
| `extracted_at` | TEXT | NOT NULL | | ISO 8601 UTC timestamp of data extraction |

### Table: `staging_prices`
Structured, typed, and Pydantic-validated records of stock price points before ingestion into the curated database.

| Column | Type | Nullability | Key | Business Constraints & Validation | Description |
|:---|:---|:---|:---|:---|:---|
| `ticker` | TEXT | NOT NULL | PK | Min length: 1 | Stock ticker symbol |
| `date` | TEXT | NOT NULL | PK | ISO 8601 Date (`YYYY-MM-DD`) | Date of trading |
| `open` | REAL | NOT NULL | | `> 0` | Opening price |
| `high` | REAL | NOT NULL | | `> 0`, `high >= open`, `high >= close` | Daily highest trading price |
| `low` | REAL | NOT NULL | | `> 0`, `low <= open`, `low <= close`, `low <= high` | Daily lowest trading price |
| `close` | REAL | NOT NULL | | `> 0` | Closing price |
| `volume` | INTEGER | NOT NULL | | `>= 0` | Traded volume |
| `dividends` | REAL | NOT NULL | | `>= 0.0` (Default: `0.0`) | Dividends paid on this day |
| `stock_splits` | REAL | NOT NULL | | `>= 0.0` (Default: `0.0`) | Stock splits ratio |
| `inserted_at` | TEXT | NOT NULL | | ISO 8601 UTC timestamp | UTC timestamp of insertion into staging |

---

## 🐘 PostgreSQL Layer (Curated OLTP)

This layer uses PostgreSQL for relational stability and analytical workloads (`market_data` database).

### Table: `dim_companies`
Dimension table holding structural company metadata.

| Column | Type | Nullability | Key | Description |
|:---|:---|:---|:---|:---|
| `company_id` | VARCHAR(12) | NOT NULL | PK | Upper-case stock ticker (e.g., `AAPL`) |
| `name` | VARCHAR(255) | NOT NULL | | Official registered company name |
| `sector` | VARCHAR(100) | NOT NULL | | GICS industry sector |
| `industry` | VARCHAR(100) | NOT NULL | | GICS industry group |
| `currency` | VARCHAR(3) | NOT NULL | | Base reporting currency |
| `updated_at` | TIMESTAMP | NOT NULL | | Timestamp of the last metadata refresh (Default: `utcnow()`) |

### Table: `fct_daily_prices`
Fact table recording historical daily price activity.

| Column | Type | Nullability | Key | Foreign Key & Policies | Description |
|:---|:---|:---|:---|:---|:---|
| `ticker` | VARCHAR(10) | NOT NULL | PK, FK | References `dim_companies(company_id)` ON DELETE CASCADE | Stock ticker symbol |
| `date` | DATE | NOT NULL | PK | | Day of trade |
| `open` | FLOAT | NOT NULL | | | Daily opening price |
| `high` | FLOAT | NOT NULL | | | Daily highest price |
| `low` | FLOAT | NOT NULL | | | Daily lowest price |
| `close` | FLOAT | NOT NULL | | | Daily closing price |
| `volume` | BIGINT | NOT NULL | | | Number of shares traded |
| `inserted_at` | TIMESTAMP | NOT NULL | | | UTC timestamp of ETL ingestion (Default: `utcnow()`) |

### Table: `fct_dividends`
Fact table recording corporate dividend payments and stock split events.

| Column | Type | Nullability | Key | Foreign Key & Policies | Description |
|:---|:---|:---|:---|:---|:---|
| `ticker` | VARCHAR(10) | NOT NULL | PK, FK | References `dim_companies(company_id)` ON DELETE CASCADE | Stock ticker symbol |
| `date` | DATE | NOT NULL | PK | | Date of dividend payment or split |
| `dividends` | FLOAT | NOT NULL | | | Dividend amount distributed per share |
| `stock_splits` | FLOAT | NOT NULL | | | Split ratio multiplier |
| `inserted_at` | TIMESTAMP | NOT NULL | | | UTC timestamp of ETL ingestion (Default: `utcnow()`) |
