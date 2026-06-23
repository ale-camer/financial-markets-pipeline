from datetime import date

def test_postgres_insert_companies(postgres_loader):
    companies = [
        {
            "company_id": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "currency": "USD"
        }
    ]
    
    postgres_loader.insert_companies(companies)
    
    # Check insertion
    with postgres_loader.SessionLocal() as session:
        from src.models.db_models import DimCompany
        result = session.query(DimCompany).all()
        assert len(result) == 1
        assert result[0].company_id == "AAPL"
        assert result[0].sector == "Technology"
        
    # Test UPSERT
    companies[0]["sector"] = "Hardware"
    postgres_loader.insert_companies(companies)
    
    with postgres_loader.SessionLocal() as session:
        from src.models.db_models import DimCompany
        result = session.query(DimCompany).all()
        assert len(result) == 1
        assert result[0].sector == "Hardware"

def test_postgres_insert_daily_prices(postgres_loader):
    # Insert company first to satisfy foreign key constraints
    postgres_loader.insert_companies([
        {
            "company_id": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "currency": "USD"
        }
    ])
    
    records = [
        {
            "ticker": "AAPL",
            "date": date(2023, 1, 1),
            "open": 150.0,
            "high": 155.0,
            "low": 149.0,
            "close": 154.0,
            "volume": 1000000
        }
    ]
    
    postgres_loader.insert_daily_prices(records)
    
    with postgres_loader.SessionLocal() as session:
        from src.models.db_models import FctDailyPrice
        result = session.query(FctDailyPrice).all()
        assert len(result) == 1
        assert result[0].close == 154.0
        
    # UPSERT
    records[0]["close"] = 160.0
    postgres_loader.insert_daily_prices(records)
    
    with postgres_loader.SessionLocal() as session:
        from src.models.db_models import FctDailyPrice
        result = session.query(FctDailyPrice).all()
        assert len(result) == 1
        assert result[0].close == 160.0

def test_postgres_insert_dividends(postgres_loader):
    # Insert company first to satisfy foreign key constraints
    postgres_loader.insert_companies([
        {
            "company_id": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "currency": "USD"
        }
    ])
    
    records = [
        {
            "ticker": "AAPL",
            "date": date(2023, 1, 1),
            "dividends": 0.5,
            "stock_splits": 0.0
        }
    ]
    
    postgres_loader.insert_dividends(records)
    
    with postgres_loader.SessionLocal() as session:
        from src.models.db_models import FctDividend
        result = session.query(FctDividend).all()
        assert len(result) == 1
        assert result[0].dividends == 0.5
        
    # UPSERT
    records[0]["dividends"] = 0.6
    postgres_loader.insert_dividends(records)
    
    with postgres_loader.SessionLocal() as session:
        from src.models.db_models import FctDividend
        result = session.query(FctDividend).all()
        assert len(result) == 1
        assert result[0].dividends == 0.6
