"""
Fact Loader - Load fact tables from source to DW
Sprint 2 - Data Warehouse Core
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


class FactLoader:
    """Load fact tables from source to DW"""
    
    def __init__(self, source_engine, dw_engine):
        self.source = source_engine
        self.dw = dw_engine
    
    def _get_dimension_lookups(self):
        """Load dimension lookup tables for key mapping"""
        logger.info("Loading dimension lookups...")
        
        self.dim_customer = pd.read_sql(
            "SELECT customer_key, customer_id FROM dw.dim_customer WHERE is_current = TRUE",
            self.dw
        ).set_index('customer_id')['customer_key'].to_dict()
        
        self.dim_product = pd.read_sql(
            "SELECT product_key, product_id FROM dw.dim_product",
            self.dw
        ).set_index('product_id')['product_key'].to_dict()
        
        self.dim_channel = pd.read_sql(
            "SELECT channel_key, channel_code FROM dw.dim_channel",
            self.dw
        ).set_index('channel_code')['channel_key'].to_dict()
        
        self.dim_payment_method = pd.read_sql(
            "SELECT payment_method_key, method_code FROM dw.dim_payment_method",
            self.dw
        ).set_index('method_code')['payment_method_key'].to_dict()
        
        logger.info(f"  Loaded {len(self.dim_customer)} customers, {len(self.dim_product)} products, {len(self.dim_channel)} channels")
    
    def load_fact_sales(self):
        """Transform order_items into fact_sales"""
        logger.info("Loading fact_sales from source")
        
        # Get dimension lookups
        self._get_dimension_lookups()
        
        # Query source data
        query = """
            SELECT 
                TO_CHAR(o.order_date, 'YYYYMMDD')::INT as date_key,
                o.customer_id,
                oi.product_id,
                o.channel,
                o.id as order_id,
                o.order_number,
                oi.id as order_item_id,
                o.status as order_status,
                oi.quantity,
                oi.unit_price,
                COALESCE(oi.discount_percent, 0) * oi.unit_price * oi.quantity / 100 as discount_amount,
                oi.line_total,
                p.cost_price
            FROM ecommerce.orders o
            JOIN ecommerce.order_items oi ON o.id = oi.order_id
            LEFT JOIN ecommerce.products p ON oi.product_id = p.id
            WHERE o.status NOT IN ('Cancelled', 'Refunded')
        """
        
        df = pd.read_sql(query, self.source)
        logger.info(f"  Fetched {len(df):,} rows from source")
        
        # Map dimension keys
        df['customer_key'] = df['customer_id'].map(self.dim_customer)
        df['product_key'] = df['product_id'].map(self.dim_product)
        df['channel_key'] = df['channel'].map(self.dim_channel)
        
        # Calculate profit
        df['cost_amount'] = df['cost_price'] * df['quantity']
        df['profit_amount'] = df['line_total'] - df['cost_amount'].fillna(0)
        
        # Select final columns
        fact_cols = [
            'date_key', 'customer_key', 'product_key', 'channel_key',
            'order_id', 'order_number', 'order_item_id', 'order_status',
            'quantity', 'unit_price', 'discount_amount', 'line_total',
            'cost_amount', 'profit_amount'
        ]
        
        df = df[fact_cols]
        
        # Handle NaN values
        df = df.where(pd.notnull(df), None)
        
        # Insert to DW
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE dw.fact_sales")
            
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            
            # Convert to tuples, handling NaN
            def clean_value(v):
                if pd.isna(v):
                    return None
                if isinstance(v, (np.integer, np.floating)):
                    return float(v) if isinstance(v, np.floating) else int(v)
                return v
            
            values = [tuple(clean_value(v) for v in row) for row in df.values]
            
            insert_sql = f'INSERT INTO dw.fact_sales ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        logger.info(f"✅ Loaded {len(df):,} rows into dw.fact_sales")
        return len(df)
    
    def load_fact_payment(self):
        """Transform payments into fact_payment"""
        logger.info("Loading fact_payment from source")
        
        # Query source data
        query = """
            SELECT 
                TO_CHAR(p.payment_date, 'YYYYMMDD')::INT as date_key,
                o.customer_id,
                p.payment_method,
                p.order_id,
                p.id as payment_id,
                p.payment_code,
                p.amount,
                p.status as payment_status
            FROM ecommerce.payments p
            JOIN ecommerce.orders o ON p.order_id = o.id
        """
        
        df = pd.read_sql(query, self.source)
        logger.info(f"  Fetched {len(df):,} rows from source")
        
        # Map dimension keys
        df['customer_key'] = df['customer_id'].map(self.dim_customer)
        df['payment_method_key'] = df['payment_method'].map(self.dim_payment_method)
        
        # Select final columns
        fact_cols = [
            'date_key', 'customer_key', 'payment_method_key',
            'order_id', 'payment_id', 'payment_code',
            'amount', 'payment_status'
        ]
        
        df = df[fact_cols]
        df = df.where(pd.notnull(df), None)
        
        # Insert to DW
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE dw.fact_payment")
            
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            
            def clean_value(v):
                if pd.isna(v):
                    return None
                if isinstance(v, (np.integer, np.floating)):
                    return float(v) if isinstance(v, np.floating) else int(v)
                return v
            
            values = [tuple(clean_value(v) for v in row) for row in df.values]
            
            insert_sql = f'INSERT INTO dw.fact_payment ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        logger.info(f"✅ Loaded {len(df):,} rows into dw.fact_payment")
        return len(df)
    
    def load_all_facts(self):
        """Load all fact tables"""
        logger.info("=" * 50)
        logger.info("Starting fact loading...")
        logger.info("=" * 50)
        
        results = {}
        
        results['fact_sales'] = self.load_fact_sales()
        results['fact_payment'] = self.load_fact_payment()
        
        logger.info("=" * 50)
        logger.info("Fact loading complete!")
        for fact, count in results.items():
            logger.info(f"  {fact}: {count:,} rows")
        logger.info("=" * 50)
        
        return results


def get_engines():
    """Create database engine connections"""
    source_url = f"postgresql://{os.getenv('SOURCE_DB_USER', 'postgres')}:{os.getenv('SOURCE_DB_PASSWORD', 'postgres')}@{os.getenv('SOURCE_DB_HOST', 'localhost')}:{os.getenv('SOURCE_DB_PORT', '5432')}/{os.getenv('SOURCE_DB_NAME', 'ecommerce_source')}"
    dw_url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
    
    source_engine = create_engine(source_url)
    dw_engine = create_engine(dw_url)
    
    return source_engine, dw_engine


if __name__ == "__main__":
    from load_dimensions import DimensionLoader, get_engines
    
    source_engine, dw_engine = get_engines()
    
    # Load dimensions first
    dim_loader = DimensionLoader(source_engine, dw_engine)
    dim_loader.load_all_dimensions()
    
    # Then load facts
    fact_loader = FactLoader(source_engine, dw_engine)
    fact_loader.load_all_facts()
