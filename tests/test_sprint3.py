"""
Sprint 3 Tests - Customer 360 & Marketing Analytics
Test mart, RFM, segmentation, and LTV calculations
"""

import os
import pytest
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def dw_engine():
    """Create DW database connection"""
    url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
    return create_engine(url)


# ============================================
# Mart Table Tests
# ============================================

class TestCustomer360Mart:
    """Test Customer 360 mart table"""
    
    def test_mart_exists(self, dw_engine):
        """TC-301: mart_customer_360 table exists"""
        query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'mart' AND table_name = 'mart_customer_360'
        """)
        with dw_engine.connect() as conn:
            result = conn.execute(query).fetchone()
        
        assert result is not None, "mart_customer_360 table does not exist"
    
    def test_mart_has_data(self, dw_engine):
        """TC-302: mart_customer_360 is populated"""
        query = text("SELECT COUNT(*) FROM mart.mart_customer_360")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        assert count >= 5000, f"mart_customer_360 has only {count} rows (expected >=5000)"
    
    def test_mart_matches_dim_customer(self, dw_engine):
        """TC-303: Mart customer count matches dimension"""
        with dw_engine.connect() as conn:
            dim_count = conn.execute(text("SELECT COUNT(*) FROM dw.dim_customer WHERE is_current = TRUE")).scalar()
            mart_count = conn.execute(text("SELECT COUNT(*) FROM mart.mart_customer_360")).scalar()
        
        assert mart_count == dim_count, f"Count mismatch: dim={dim_count}, mart={mart_count}"


# ============================================
# RFM Tests
# ============================================

class TestRFMCalculation:
    """Test RFM score calculations"""
    
    def test_rfm_scores_valid_range(self, dw_engine):
        """TC-310: RFM scores are in range 1-5"""
        query = text("""
            SELECT 
                MIN(recency_score) as min_r, MAX(recency_score) as max_r,
                MIN(frequency_score) as min_f, MAX(frequency_score) as max_f,
                MIN(monetary_score) as min_m, MAX(monetary_score) as max_m
            FROM mart.mart_customer_360
            WHERE recency_score IS NOT NULL
        """)
        with dw_engine.connect() as conn:
            result = conn.execute(query).fetchone()
        
        assert result[0] >= 1 and result[1] <= 5, f"Recency score out of range: {result[0]}-{result[1]}"
        assert result[2] >= 1 and result[3] <= 5, f"Frequency score out of range: {result[2]}-{result[3]}"
        assert result[4] >= 1 and result[5] <= 5, f"Monetary score out of range: {result[4]}-{result[5]}"
    
    def test_rfm_score_format(self, dw_engine):
        """TC-311: RFM score is 3-digit string"""
        query = text("""
            SELECT COUNT(*) 
            FROM mart.mart_customer_360
            WHERE rfm_score IS NOT NULL 
            AND LENGTH(rfm_score) != 3
        """)
        with dw_engine.connect() as conn:
            invalid_count = conn.execute(query).scalar()
        
        assert invalid_count == 0, f"Found {invalid_count} invalid RFM score formats"
    
    def test_all_active_customers_have_rfm(self, dw_engine):
        """TC-312: All customers with orders have RFM scores"""
        query = text("""
            SELECT COUNT(*) 
            FROM mart.mart_customer_360
            WHERE total_orders > 0 AND rfm_score IS NULL
        """)
        with dw_engine.connect() as conn:
            missing_count = conn.execute(query).scalar()
        
        assert missing_count == 0, f"{missing_count} active customers missing RFM scores"


# ============================================
# Segmentation Tests
# ============================================

class TestSegmentation:
    """Test customer segmentation"""
    
    def test_segments_exist(self, dw_engine):
        """TC-320: Key segments are populated"""
        expected_segments = ['Champions', 'Loyal Customers', 'At Risk', 'Lost']
        query = text("SELECT DISTINCT rfm_segment FROM mart.mart_customer_360 WHERE rfm_segment IS NOT NULL")
        with dw_engine.connect() as conn:
            actual = [row[0] for row in conn.execute(query)]
        
        for segment in expected_segments:
            assert segment in actual, f"Missing segment: {segment}"
    
    def test_segment_distribution(self, dw_engine):
        """TC-321: Segment distribution is reasonable"""
        query = text("""
            SELECT rfm_segment, COUNT(*) as cnt
            FROM mart.mart_customer_360
            WHERE rfm_segment IS NOT NULL
            GROUP BY rfm_segment
        """)
        with dw_engine.connect() as conn:
            results = dict(conn.execute(query).fetchall())
        
        # No single segment should be more than 50% of total
        total = sum(results.values())
        for segment, count in results.items():
            pct = 100 * count / total
            assert pct < 50, f"{segment} has {pct:.1f}% of customers (too dominant)"


# ============================================
# LTV Tests
# ============================================

class TestLTV:
    """Test LTV calculations"""
    
    def test_ltv_is_positive(self, dw_engine):
        """TC-330: LTV values are non-negative"""
        query = text("""
            SELECT COUNT(*) 
            FROM mart.mart_customer_360
            WHERE estimated_ltv < 0
        """)
        with dw_engine.connect() as conn:
            negative_count = conn.execute(query).scalar()
        
        assert negative_count == 0, f"Found {negative_count} negative LTV values"
    
    def test_ltv_correlated_with_revenue(self, dw_engine):
        """TC-331: LTV is correlated with historical revenue"""
        query = text("""
            SELECT 
                CORR(total_revenue, estimated_ltv) as correlation
            FROM mart.mart_customer_360
            WHERE total_revenue > 0 AND estimated_ltv > 0
        """)
        with dw_engine.connect() as conn:
            correlation = conn.execute(query).scalar()
        
        # LTV should be positively correlated with revenue
        assert correlation > 0.3, f"LTV-Revenue correlation too low: {correlation:.3f}"


# ============================================
# Aggregate Views Tests
# ============================================

class TestAggregateViews:
    """Test aggregate views"""
    
    def test_revenue_by_month_view(self, dw_engine):
        """TC-340: Revenue by month view works"""
        query = text("SELECT COUNT(*) FROM mart.v_revenue_by_month")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        assert count > 0, "v_revenue_by_month has no data"
    
    def test_revenue_by_category_view(self, dw_engine):
        """TC-341: Revenue by category view works"""
        query = text("SELECT COUNT(*) FROM mart.v_revenue_by_category")
        with dw_engine.connect() as conn:
            count = conn.execute(query).scalar()
        
        assert count > 0, "v_revenue_by_category has no data"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--override-ini=addopts="])
