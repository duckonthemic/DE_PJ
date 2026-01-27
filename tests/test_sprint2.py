"""
Sprint 2 Tests - Data Warehouse Core
Test schema, data mapping, aggregations, and reconciliation
"""

import os
import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


# ============================================
# Fixtures
# ============================================

@pytest.fixture(scope="module")
def source_engine():
    """Create source database connection"""
    url = f"postgresql://{os.getenv('SOURCE_DB_USER', 'postgres')}:{os.getenv('SOURCE_DB_PASSWORD', 'postgres')}@{os.getenv('SOURCE_DB_HOST', 'localhost')}:{os.getenv('SOURCE_DB_PORT', '5432')}/{os.getenv('SOURCE_DB_NAME', 'ecommerce_source')}"
    return create_engine(url)


@pytest.fixture(scope="module")
def dw_engine():
    """Create DW database connection"""
    url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
    return create_engine(url)


# ============================================
# Schema Tests
# ============================================

class TestDWSchema:
    """Test DW schema structure"""
    
    def test_all_dimensions_exist(self, dw_engine):
        """TC-201: All dimension tables exist"""
        expected = ['dim_customer', 'dim_product', 'dim_date', 'dim_channel', 'dim_payment_method']
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'dw' AND table_name LIKE 'dim_%'
        """)
        with dw_engine.connect() as conn:
            actual = [row[0] for row in conn.execute(query)]
        
        for dim in expected:
            assert dim in actual, f"Missing dimension: {dim}"
    
    def test_all_facts_exist(self, dw_engine):
        """TC-202: All fact tables exist"""
        expected = ['fact_sales', 'fact_payment']
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'dw' AND table_name LIKE 'fact_%'
        """)
        with dw_engine.connect() as conn:
            actual = [row[0] for row in conn.execute(query)]
        
        for fact in expected:
            assert fact in actual, f"Missing fact: {fact}"
    
    def test_reconciliation_exists(self, dw_engine):
        """TC-203: Reconciliation table exists"""
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'reconcile'
        """)
        with dw_engine.connect() as conn:
            actual = [row[0] for row in conn.execute(query)]
        
        assert 'fact_reconciliation' in actual


# ============================================
# Dimension Data Tests
# ============================================

class TestDimensionData:
    """Test dimension table data"""
    
    def test_dim_date_has_data(self, dw_engine):
        """TC-210: dim_date has calendar data"""
        query = text("SELECT COUNT(*) FROM dw.dim_date")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        # Should have ~11 years of data (2020-2030)
        assert count >= 4000, f"dim_date has only {count} rows"
    
    def test_dim_customer_matches_source(self, source_engine, dw_engine):
        """TC-211: dim_customer count matches source"""
        with source_engine.connect() as conn:
            source_count = conn.execute(text("SELECT COUNT(*) FROM ecommerce.customers")).scalar()
        
        with dw_engine.connect() as conn:
            dw_count = conn.execute(text("SELECT COUNT(*) FROM dw.dim_customer")).scalar()
        
        assert source_count == dw_count, f"Mismatch: source={source_count}, dw={dw_count}"
    
    def test_dim_product_matches_source(self, source_engine, dw_engine):
        """TC-212: dim_product count matches source"""
        with source_engine.connect() as conn:
            source_count = conn.execute(text("SELECT COUNT(*) FROM ecommerce.products")).scalar()
        
        with dw_engine.connect() as conn:
            dw_count = conn.execute(text("SELECT COUNT(*) FROM dw.dim_product")).scalar()
        
        assert source_count == dw_count, f"Mismatch: source={source_count}, dw={dw_count}"


# ============================================
# Fact Data Tests
# ============================================

class TestFactData:
    """Test fact table data"""
    
    def test_fact_sales_has_data(self, dw_engine):
        """TC-220: fact_sales is populated"""
        query = text("SELECT COUNT(*) FROM dw.fact_sales")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        assert count > 100000, f"fact_sales has only {count} rows (expected >100k)"
    
    def test_fact_payment_has_data(self, dw_engine):
        """TC-221: fact_payment is populated"""
        query = text("SELECT COUNT(*) FROM dw.fact_payment")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        assert count > 50000, f"fact_payment has only {count} rows (expected >50k)"
    
    def test_fact_sales_total_revenue(self, source_engine, dw_engine):
        """TC-222: Total revenue matches between source and DW"""
        source_query = text("""
            SELECT SUM(oi.line_total) as total 
            FROM ecommerce.order_items oi
            JOIN ecommerce.orders o ON oi.order_id = o.id
            WHERE o.status NOT IN ('Cancelled', 'Refunded')
        """)
        with source_engine.connect() as conn:
            source_revenue = float(conn.execute(source_query).scalar() or 0)
        
        dw_query = text("SELECT SUM(line_total) as total FROM dw.fact_sales")
        with dw_engine.connect() as conn:
            dw_revenue = float(conn.execute(dw_query).scalar() or 0)
        
        # Allow 0.1% variance
        variance = abs(source_revenue - dw_revenue) / source_revenue if source_revenue > 0 else 0
        assert variance < 0.001, f"Revenue mismatch: source={source_revenue:.2f}, dw={dw_revenue:.2f}, variance={variance:.4%}"


# ============================================
# Reconciliation Tests
# ============================================

class TestReconciliation:
    """Test reconciliation logic"""
    
    def test_reconciliation_has_data(self, dw_engine):
        """TC-230: fact_reconciliation is populated"""
        query = text("SELECT COUNT(*) FROM reconcile.fact_reconciliation")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        assert count > 50000, f"fact_reconciliation has only {count} rows"
    
    def test_reconciliation_status_values(self, dw_engine):
        """TC-231: Reconciliation has valid status values"""
        query = text("""
            SELECT DISTINCT order_payment_status 
            FROM reconcile.fact_reconciliation
        """)
        with dw_engine.connect() as conn:
            statuses = [row[0] for row in conn.execute(query)]
        
        valid_statuses = ['MATCHED', 'UNDERPAID', 'OVERPAID', 'NO_PAYMENT']
        for status in statuses:
            assert status in valid_statuses, f"Invalid status: {status}"
    
    def test_no_orphan_payments(self, source_engine):
        """TC-232: All payments have matching orders"""
        query = text("""
            SELECT COUNT(*) 
            FROM ecommerce.payments p
            LEFT JOIN ecommerce.orders o ON p.order_id = o.id
            WHERE o.id IS NULL
        """)
        with source_engine.connect() as conn:
            orphans = conn.execute(query).scalar()
        
        assert orphans == 0, f"Found {orphans} orphan payments"
    
    def test_reconciliation_summary(self, dw_engine):
        """TC-233: Reconciliation summary is consistent"""
        query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE overall_status = 'MATCHED') as matched,
                COUNT(*) FILTER (WHERE overall_status = 'UNMATCHED') as unmatched
            FROM reconcile.fact_reconciliation
        """)
        with dw_engine.connect() as conn:
            result = conn.execute(query).fetchone()
        
        total, matched, unmatched = result
        assert total == matched + unmatched, "Status counts don't add up"


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--override-ini=addopts="])
