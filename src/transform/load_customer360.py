"""
Customer 360 & RFM Loader - Build Customer 360 mart with RFM segmentation
Sprint 3 - Customer Analytics
"""

import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Customer360Loader:
    """Build Customer 360 mart with RFM segmentation"""
    
    def __init__(self, dw_engine):
        self.dw = dw_engine
        self.analysis_date = datetime.now().date()
    
    def load_customer_metrics(self):
        """Build customer behavior metrics from fact tables"""
        logger.info("Calculating customer behavior metrics...")
        
        query = text("""
            WITH customer_orders AS (
                SELECT 
                    c.customer_key,
                    c.customer_id,
                    c.customer_code,
                    c.email,
                    c.first_name,
                    c.last_name,
                    c.first_name || ' ' || c.last_name as full_name,
                    c.phone,
                    c.city,
                    c.segment,
                    
                    -- Order dates
                    MIN(d.full_date) as first_order_date,
                    MAX(d.full_date) as last_order_date,
                    
                    -- Order metrics
                    COUNT(DISTINCT f.order_id) as total_orders,
                    COUNT(f.sales_key) as total_order_items,
                    COUNT(DISTINCT f.order_id) FILTER (WHERE f.order_status = 'Cancelled') as cancelled_orders,
                    
                    -- Revenue metrics
                    SUM(f.line_total) as total_revenue,
                    SUM(f.discount_amount) as total_discount,
                    SUM(f.line_total) - SUM(COALESCE(f.discount_amount, 0)) as net_revenue,
                    
                    -- Product metrics
                    COUNT(DISTINCT f.product_key) as unique_products_purchased
                    
                FROM dw.dim_customer c
                LEFT JOIN dw.fact_sales f ON c.customer_key = f.customer_key
                LEFT JOIN dw.dim_date d ON f.date_key = d.date_key
                WHERE c.is_current = TRUE
                GROUP BY c.customer_key, c.customer_id, c.customer_code, c.email, 
                         c.first_name, c.last_name, c.phone, c.city, c.segment
            ),
            customer_payments AS (
                SELECT 
                    c.customer_key,
                    COUNT(p.payment_key) as total_payments,
                    SUM(p.amount) as total_payment_amount,
                    MODE() WITHIN GROUP (ORDER BY pm.method_code) as preferred_payment_method
                FROM dw.dim_customer c
                LEFT JOIN dw.fact_payment p ON c.customer_key = p.customer_key
                LEFT JOIN dw.dim_payment_method pm ON p.payment_method_key = pm.payment_method_key
                WHERE c.is_current = TRUE
                GROUP BY c.customer_key
            ),
            customer_channels AS (
                SELECT 
                    c.customer_key,
                    MODE() WITHIN GROUP (ORDER BY ch.channel_code) as preferred_channel
                FROM dw.dim_customer c
                LEFT JOIN dw.fact_sales f ON c.customer_key = f.customer_key
                LEFT JOIN dw.dim_channel ch ON f.channel_key = ch.channel_key
                WHERE c.is_current = TRUE
                GROUP BY c.customer_key
            ),
            customer_categories AS (
                SELECT 
                    c.customer_key,
                    COUNT(DISTINCT p.category_name) as unique_categories_purchased
                FROM dw.dim_customer c
                LEFT JOIN dw.fact_sales f ON c.customer_key = f.customer_key
                LEFT JOIN dw.dim_product p ON f.product_key = p.product_key
                WHERE c.is_current = TRUE
                GROUP BY c.customer_key
            )
            SELECT 
                co.*,
                
                -- Calculated fields
                CURRENT_DATE - co.first_order_date as customer_tenure_days,
                CURRENT_DATE - co.last_order_date as days_since_last_order,
                CASE WHEN co.total_orders > 0 
                     THEN co.total_revenue / co.total_orders 
                     ELSE 0 END as avg_order_value,
                
                -- Payment metrics
                COALESCE(cp.total_payments, 0) as total_payments,
                COALESCE(cp.total_payment_amount, 0) as total_payment_amount,
                cp.preferred_payment_method,
                
                -- Channel metrics
                cc.preferred_channel,
                
                -- Category metrics
                COALESCE(cat.unique_categories_purchased, 0) as unique_categories_purchased
                
            FROM customer_orders co
            LEFT JOIN customer_payments cp ON co.customer_key = cp.customer_key
            LEFT JOIN customer_channels cc ON co.customer_key = cc.customer_key
            LEFT JOIN customer_categories cat ON co.customer_key = cat.customer_key
        """)
        
        with self.dw.connect() as conn:
            df = pd.read_sql(query, conn)
        
        logger.info(f"  Loaded metrics for {len(df):,} customers")
        return df
    
    def calculate_rfm_scores(self, df):
        """Calculate RFM scores (1-5) using quintiles"""
        logger.info("Calculating RFM scores...")
        
        # Filter customers with orders
        active_df = df[df['total_orders'] > 0].copy()
        
        if len(active_df) == 0:
            logger.warning("No active customers found!")
            df['recency_score'] = None
            df['frequency_score'] = None
            df['monetary_score'] = None
            df['rfm_score'] = None
            df['rfm_segment'] = None
            return df
        
        # Calculate Recency score (lower days = higher score)
        active_df['recency_score'] = pd.qcut(
            active_df['days_since_last_order'].rank(method='first'), 
            q=5, 
            labels=[5, 4, 3, 2, 1]  # Reverse because lower recency = better
        ).astype(int)
        
        # Calculate Frequency score
        active_df['frequency_score'] = pd.qcut(
            active_df['total_orders'].rank(method='first'), 
            q=5, 
            labels=[1, 2, 3, 4, 5]
        ).astype(int)
        
        # Calculate Monetary score
        active_df['monetary_score'] = pd.qcut(
            active_df['total_revenue'].rank(method='first'), 
            q=5, 
            labels=[1, 2, 3, 4, 5]
        ).astype(int)
        
        # Create RFM score string
        active_df['rfm_score'] = (
            active_df['recency_score'].astype(str) + 
            active_df['frequency_score'].astype(str) + 
            active_df['monetary_score'].astype(str)
        )
        
        # Merge back to original df
        df = df.merge(
            active_df[['customer_key', 'recency_score', 'frequency_score', 'monetary_score', 'rfm_score']],
            on='customer_key',
            how='left'
        )
        
        logger.info(f"  Calculated RFM for {len(active_df):,} active customers")
        return df
    
    def assign_rfm_segments(self, df):
        """Assign RFM segment names based on score patterns"""
        logger.info("Assigning RFM segments...")
        
        # Load segment mappings
        query = text("SELECT rfm_pattern, segment_name FROM mart.rfm_segment_mapping")
        with self.dw.connect() as conn:
            segment_map = dict(conn.execute(query).fetchall())
        
        def get_segment(rfm_score):
            if pd.isna(rfm_score):
                return 'No Purchase'
            
            # Direct match
            if rfm_score in segment_map:
                return segment_map[rfm_score]
            
            # Approximate match based on first digit (recency)
            r = int(rfm_score[0])
            f = int(rfm_score[1])
            m = int(rfm_score[2])
            
            if r >= 4 and f >= 4 and m >= 4:
                return 'Champions'
            elif r >= 4 and f >= 3:
                return 'Loyal Customers'
            elif r >= 4 and f <= 2:
                return 'New Customers'
            elif r >= 3 and f >= 3:
                return 'Potential Loyalists'
            elif r >= 3:
                return 'Need Attention'
            elif r == 2:
                return 'At Risk'
            else:
                return 'Lost'
        
        df['rfm_segment'] = df['rfm_score'].apply(get_segment)
        
        # Log segment distribution
        segment_counts = df['rfm_segment'].value_counts()
        logger.info("  Segment Distribution:")
        for segment, count in segment_counts.items():
            logger.info(f"    {segment}: {count:,}")
        
        return df
    
    def calculate_ltv(self, df):
        """Calculate estimated Lifetime Value"""
        logger.info("Calculating LTV estimates...")
        
        # Simple LTV = Average Order Value * Purchase Frequency * Customer Lifespan
        # Lifespan assumed as 3 years (36 months) for active customers
        
        df['purchase_frequency_monthly'] = np.where(
            df['customer_tenure_days'] > 0,
            df['total_orders'] / (df['customer_tenure_days'] / 30),
            0
        )
        
        # Estimated LTV over 3 years (36 months)
        df['estimated_ltv'] = df['avg_order_value'] * df['purchase_frequency_monthly'] * 36
        
        # Cap at reasonable maximum
        df['estimated_ltv'] = df['estimated_ltv'].clip(upper=df['total_revenue'] * 5)
        
        return df
    
    def determine_customer_status(self, df):
        """Determine customer status based on activity"""
        logger.info("Determining customer status...")
        
        def get_status(row):
            if pd.isna(row['days_since_last_order']) or row['total_orders'] == 0:
                return 'New'  # Never ordered
            elif row['days_since_last_order'] <= 30:
                return 'Active'
            elif row['days_since_last_order'] <= 90:
                return 'Inactive'
            else:
                return 'Churned'
        
        df['customer_status'] = df.apply(get_status, axis=1)
        
        return df
    
    def save_to_mart(self, df):
        """Save Customer 360 data to mart table"""
        logger.info("Saving to mart.mart_customer_360...")
        
        # Select columns matching the table
        columns = [
            'customer_key', 'customer_id', 'customer_code', 'email',
            'first_name', 'last_name', 'full_name', 'phone', 'city', 'segment',
            'first_order_date', 'last_order_date', 'customer_tenure_days', 'days_since_last_order',
            'total_orders', 'total_order_items', 'cancelled_orders',
            'total_revenue', 'total_discount', 'net_revenue', 'avg_order_value',
            'unique_products_purchased', 'unique_categories_purchased',
            'total_payments', 'total_payment_amount', 'preferred_payment_method',
            'preferred_channel',
            'recency_score', 'frequency_score', 'monetary_score', 'rfm_score', 'rfm_segment',
            'estimated_ltv', 'customer_status'
        ]
        
        df_out = df[columns].copy()
        
        # Handle NaN/NaT values
        df_out = df_out.where(pd.notnull(df_out), None)
        
        # Insert to mart
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE mart.mart_customer_360")
            
            col_str = ', '.join([f'"{c}"' for c in columns])
            
            def clean_value(v):
                if pd.isna(v) or v is pd.NaT:
                    return None
                if isinstance(v, (np.integer, np.floating)):
                    return float(v) if isinstance(v, np.floating) else int(v)
                if hasattr(v, 'date'):
                    return v.date() if callable(getattr(v, 'date', None)) else v
                return v
            
            values = [tuple(clean_value(v) for v in row) for row in df_out.values]
            
            insert_sql = f'INSERT INTO mart.mart_customer_360 ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        logger.info(f"✅ Saved {len(df_out):,} customers to mart.mart_customer_360")
        return len(df_out)
    
    def run(self):
        """Run full Customer 360 pipeline"""
        logger.info("=" * 60)
        logger.info("SPRINT 3 - CUSTOMER 360 PIPELINE")
        logger.info(f"Analysis Date: {self.analysis_date}")
        logger.info("=" * 60)
        
        # Step 1: Load customer metrics
        df = self.load_customer_metrics()
        
        # Step 2: Calculate RFM scores
        df = self.calculate_rfm_scores(df)
        
        # Step 3: Assign RFM segments
        df = self.assign_rfm_segments(df)
        
        # Step 4: Calculate LTV
        df = self.calculate_ltv(df)
        
        # Step 5: Determine status
        df = self.determine_customer_status(df)
        
        # Step 6: Save to mart
        count = self.save_to_mart(df)
        
        logger.info("=" * 60)
        logger.info("Customer 360 pipeline complete!")
        logger.info("=" * 60)
        
        return count


def get_dw_engine():
    """Create DW database connection"""
    url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
    return create_engine(url)


if __name__ == "__main__":
    dw_engine = get_dw_engine()
    loader = Customer360Loader(dw_engine)
    loader.run()
