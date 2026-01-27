"""
Dimension Loader - Load dimension tables from source to DW
Sprint 2 - Data Warehouse Core
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DimensionLoader:
    """Load dimension tables from source to DW"""
    
    def __init__(self, source_engine, dw_engine):
        self.source = source_engine
        self.dw = dw_engine
    
    def generate_dim_date(self, start_year=2020, end_year=2030):
        """Generate calendar dimension table"""
        logger.info(f"Generating dim_date from {start_year} to {end_year}")
        
        dates = []
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        
        current = start
        while current <= end:
            dates.append({
                'date_key': int(current.strftime('%Y%m%d')),
                'full_date': current.date(),
                'day_of_week': current.weekday() + 1,
                'day_name': current.strftime('%A'),
                'day_of_month': current.day,
                'day_of_year': current.timetuple().tm_yday,
                'week_of_year': current.isocalendar()[1],
                'month': current.month,
                'month_name': current.strftime('%B'),
                'quarter': (current.month - 1) // 3 + 1,
                'year': current.year,
                'is_weekend': current.weekday() >= 5,
                'is_holiday': False,
            })
            current += timedelta(days=1)
        
        df = pd.DataFrame(dates)
        
        # Insert using COPY for better performance
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            # Truncate existing data
            cur.execute("TRUNCATE TABLE dw.dim_date CASCADE")
            
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            values = [tuple(row) for row in df.values]
            
            insert_sql = f'INSERT INTO dw.dim_date ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        logger.info(f"✅ Loaded {len(df)} rows into dw.dim_date")
        return len(df)
    
    def load_dim_customer(self):
        """Load customer dimension from source (SCD Type 1 for now)"""
        logger.info("Loading dim_customer from source")
        
        query = """
            SELECT 
                id as customer_id,
                customer_code,
                email,
                first_name,
                last_name,
                phone,
                city,
                segment
            FROM ecommerce.customers
        """
        
        df = pd.read_sql(query, self.source)
        df['effective_date'] = datetime.now().date()
        df['end_date'] = None
        df['is_current'] = True
        
        # Insert to DW
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE dw.dim_customer CASCADE")
            
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            values = [tuple(None if pd.isna(v) else v for v in row) for row in df.values]
            
            insert_sql = f'INSERT INTO dw.dim_customer ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        logger.info(f"✅ Loaded {len(df)} rows into dw.dim_customer")
        return len(df)
    
    def load_dim_product(self):
        """Load product dimension with category denormalized"""
        logger.info("Loading dim_product from source")
        
        query = """
            SELECT 
                p.id as product_id,
                p.sku,
                p.name as product_name,
                p.category_id,
                c.name as category_name,
                p.unit_price,
                p.cost_price,
                p.is_active
            FROM ecommerce.products p
            LEFT JOIN ecommerce.categories c ON p.category_id = c.id
        """
        
        df = pd.read_sql(query, self.source)
        
        # Insert to DW
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE dw.dim_product CASCADE")
            
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            values = [tuple(None if pd.isna(v) else v for v in row) for row in df.values]
            
            insert_sql = f'INSERT INTO dw.dim_product ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        logger.info(f"✅ Loaded {len(df)} rows into dw.dim_product")
        return len(df)
    
    def load_all_dimensions(self):
        """Load all dimension tables"""
        logger.info("=" * 50)
        logger.info("Starting dimension loading...")
        logger.info("=" * 50)
        
        results = {}
        
        results['dim_date'] = self.generate_dim_date()
        results['dim_customer'] = self.load_dim_customer()
        results['dim_product'] = self.load_dim_product()
        # dim_channel and dim_payment_method are seeded in DDL
        
        logger.info("=" * 50)
        logger.info("Dimension loading complete!")
        for dim, count in results.items():
            logger.info(f"  {dim}: {count:,} rows")
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
    source_engine, dw_engine = get_engines()
    loader = DimensionLoader(source_engine, dw_engine)
    loader.load_all_dimensions()
