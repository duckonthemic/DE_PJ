"""
Main ETL Orchestrator - Run full DW ETL pipeline
Sprint 2 - Data Warehouse Core

Usage:
    python -m src.transform.run_dw_etl
    
Or from Docker:
    docker run --rm -v "${PWD}:/app" -w /app \
        --network enterperise_de_analytics-network \
        -e SOURCE_DB_HOST=postgres-source \
        -e DW_DB_HOST=postgres-dw \
        python:3.10-slim bash -c "pip install -q pandas sqlalchemy psycopg2-binary python-dotenv && python -m src.transform.run_dw_etl"
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_engines():
    """Create database engine connections"""
    from sqlalchemy import create_engine
    
    source_url = f"postgresql://{os.getenv('SOURCE_DB_USER', 'postgres')}:{os.getenv('SOURCE_DB_PASSWORD', 'postgres')}@{os.getenv('SOURCE_DB_HOST', 'localhost')}:{os.getenv('SOURCE_DB_PORT', '5432')}/{os.getenv('SOURCE_DB_NAME', 'ecommerce_source')}"
    dw_url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
    
    source_engine = create_engine(source_url)
    dw_engine = create_engine(dw_url)
    
    return source_engine, dw_engine


def main():
    """Run full DW ETL pipeline"""
    start_time = datetime.now()
    
    logger.info("=" * 60)
    logger.info("SPRINT 2 - DATA WAREHOUSE ETL PIPELINE")
    logger.info(f"Started at: {start_time}")
    logger.info("=" * 60)
    
    # Get database connections
    source_engine, dw_engine = get_engines()
    
    # Test connections
    try:
        from sqlalchemy import text
        with source_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Source database connection OK")
    except Exception as e:
        logger.error(f"❌ Source database connection failed: {e}")
        sys.exit(1)
    
    try:
        from sqlalchemy import text
        with dw_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ DW database connection OK")
    except Exception as e:
        logger.error(f"❌ DW database connection failed: {e}")
        sys.exit(1)
    
    results = {}
    
    # Step 1: Load Dimensions
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: Loading Dimensions...")
    logger.info("=" * 60)
    
    from src.transform.load_dimensions import DimensionLoader
    dim_loader = DimensionLoader(source_engine, dw_engine)
    dim_results = dim_loader.load_all_dimensions()
    results.update(dim_results)
    
    # Step 2: Load Facts
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Loading Facts...")
    logger.info("=" * 60)
    
    from src.transform.load_facts import FactLoader
    fact_loader = FactLoader(source_engine, dw_engine)
    fact_results = fact_loader.load_all_facts()
    results.update(fact_results)
    
    # Step 3: Load Reconciliation
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Loading Reconciliation...")
    logger.info("=" * 60)
    
    from src.transform.load_reconciliation import ReconciliationLoader
    recon_loader = ReconciliationLoader(source_engine, dw_engine)
    recon_count = recon_loader.load_fact_reconciliation()
    results['fact_reconciliation'] = recon_count
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 60)
    logger.info("ETL PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info("\nTable Summary:")
    total_rows = 0
    for table, count in results.items():
        logger.info(f"  {table}: {count:,} rows")
        total_rows += count
    logger.info(f"\nTotal rows loaded: {total_rows:,}")
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    main()
