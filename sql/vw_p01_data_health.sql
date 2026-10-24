CREATE OR REPLACE VIEW public.vw_p01_data_health AS
WITH global_bounds AS (
    SELECT 
        MIN(fdp."date") AS "global_min_date",
        MAX(fdp."date") AS "global_max_date",
        COUNT(DISTINCT fdp."date") AS "expected_dates_count"
    FROM public.fct_daily_prices fdp
),
ticker_metrics AS (
    SELECT 
        fdp."ticker" AS "ticker",
        COUNT(DISTINCT fdp."date") AS "dates_count",
        MIN(fdp."date") AS "ticker_min_date",
        MAX(fdp."date") AS "ticker_max_date",
        COUNT(*) AS "total_rows",
        SUM(CASE WHEN fdp."high" < fdp."low" OR fdp."high" < fdp."open" OR fdp."high" < fdp."close" THEN 1 ELSE 0 END) AS "ohlc_invalid_count",
        SUM(CASE WHEN fdp."open" <= 0 OR fdp."high" <= 0 OR fdp."low" <= 0 OR fdp."close" <= 0 THEN 1 ELSE 0 END) AS "non_positive_prices_count",
        SUM(CASE WHEN fdp."volume" < 0 THEN 1 ELSE 0 END) AS "negative_volume_count"
    FROM public.fct_daily_prices fdp
    GROUP BY fdp."ticker"
)
SELECT 
    tm."ticker" AS "ticker",
    tm."dates_count" AS "dates_count",
    gb."expected_dates_count" AS "expected_dates_count",
    CASE 
        WHEN tm."dates_count" = gb."expected_dates_count" 
         AND tm."ticker_min_date" = gb."global_min_date"
         AND tm."ticker_max_date" = gb."global_max_date"
        THEN 1 
        ELSE 0 
    END AS "is_dates_coverage_ok",
    tm."ohlc_invalid_count" AS "ohlc_invalid_count",
    tm."non_positive_prices_count" AS "non_positive_prices_count",
    tm."negative_volume_count" AS "negative_volume_count",
    CASE 
        WHEN tm."dates_count" = gb."expected_dates_count"
         AND tm."ticker_min_date" = gb."global_min_date"
         AND tm."ticker_max_date" = gb."global_max_date"
         AND tm."ohlc_invalid_count" = 0
         AND tm."non_positive_prices_count" = 0
         AND tm."negative_volume_count" = 0
        THEN 1
        ELSE 0
    END AS "is_healthy",
    tm."ticker_min_date" AS "ticker_min_date",
    tm."ticker_max_date" AS "ticker_max_date"
FROM ticker_metrics tm
CROSS JOIN global_bounds gb;
