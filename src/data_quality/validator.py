"""
Data Quality Validator
Simple framework to run SQL-based data quality checks
"""

import os
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataValidator:
    def __init__(self):
        url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
        self.engine = create_engine(url)
        self.checks = []

    def add_check(self, name, sql, expected_condition=lambda x: x == 0):
        self.checks.append({
            'name': name,
            'sql': sql,
            'condition': expected_condition
        })

    def run(self):
        logger.info("Starting Data Quality Checks...")
        failures = 0
        
        with self.engine.connect() as conn:
            for check in self.checks:
                try:
                    result = conn.execute(text(check['sql'])).scalar()
                    if check['condition'](result):
                        logger.info(f"✅ PASS: {check['name']}")
                    else:
                        logger.error(f"❌ FAIL: {check['name']} (Value: {result})")
                        failures += 1
                except Exception as e:
                    logger.error(f"❌ ERROR: {check['name']} - {str(e)}")
                    failures += 1
        
        if failures > 0:
            logger.error(f"Data Quality Validation FAILED with {failures} errors")
            return False
        
        logger.info("All Data Quality Checks PASSED")
        return True

def run_validations():
    validator = DataValidator()
    
    # Check 1: dim_customer uniqueness
    validator.add_check(
        "dim_customer Unique Key",
        "SELECT COUNT(*) - COUNT(DISTINCT customer_key) FROM dw.dim_customer"
    )
    
    # Check 2: fact_sales negative values (should be 0)
    validator.add_check(
        "fact_sales Negative Quantity",
        "SELECT COUNT(*) FROM dw.fact_sales WHERE quantity < 0"
    )
    
    # Check 3: fact_reconciliation orphan payments (should be 0)
    validator.add_check(
        "fact_reconciliation Orphans",
        "SELECT COUNT(*) FROM reconcile.fact_reconciliation WHERE order_payment_status = 'NO_PAYMENT' AND payment_count > 0"
    )
    
    # Check 4: mart_customer_360 missing RFM (should be 0 for active)
    validator.add_check(
        "mart_customer_360 Missing RFM",
        "SELECT COUNT(*) FROM mart.mart_customer_360 WHERE total_orders > 0 AND rfm_score IS NULL"
    )

    return validator.run()

if __name__ == "__main__":
    import sys
    success = run_validations()
    sys.exit(0 if success else 1)
