"""
Reconciliation Loader - Build reconciliation fact table
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


class ReconciliationLoader:
    """Build reconciliation fact table from source data"""
    
    def __init__(self, source_engine, dw_engine):
        self.source = source_engine
        self.dw = dw_engine
    
    def load_fact_reconciliation(self):
        """Build reconciliation fact comparing orders, payments, and invoices"""
        logger.info("Building fact_reconciliation from source")
        
        # Query: Order summary with payment and invoice aggregates
        query = """
            WITH order_summary AS (
                SELECT 
                    o.id as order_id,
                    o.order_number,
                    o.customer_id,
                    TO_CHAR(o.order_date, 'YYYYMMDD')::INT as date_key,
                    o.total_amount as order_amount,
                    o.status as order_status,
                    o.order_date
                FROM ecommerce.orders o
                WHERE o.status NOT IN ('Cancelled')
            ),
            payment_summary AS (
                SELECT 
                    order_id,
                    COUNT(*) as payment_count,
                    SUM(amount) as payment_amount,
                    MAX(payment_date) as last_payment_date
                FROM ecommerce.payments
                WHERE status = 'Completed'
                GROUP BY order_id
            ),
            invoice_summary AS (
                SELECT 
                    order_id,
                    COUNT(*) as invoice_count,
                    SUM(total_amount) as invoice_amount
                FROM ecommerce.invoices
                GROUP BY order_id
            )
            SELECT 
                os.order_id,
                os.order_number,
                os.customer_id,
                os.date_key,
                os.order_amount,
                os.order_status,
                os.order_date,
                COALESCE(ps.payment_count, 0) as payment_count,
                COALESCE(ps.payment_amount, 0) as payment_amount,
                ps.last_payment_date,
                COALESCE(inv.invoice_count, 0) as invoice_count,
                COALESCE(inv.invoice_amount, 0) as invoice_amount
            FROM order_summary os
            LEFT JOIN payment_summary ps ON os.order_id = ps.order_id
            LEFT JOIN invoice_summary inv ON os.order_id = inv.order_id
        """
        
        df = pd.read_sql(query, self.source)
        logger.info(f"  Fetched {len(df):,} orders for reconciliation")
        
        # Calculate reconciliation status
        def get_order_payment_status(row):
            if row['payment_amount'] == 0:
                return 'NO_PAYMENT'
            elif abs(row['order_amount'] - row['payment_amount']) <= 1:
                return 'MATCHED'
            elif row['payment_amount'] < row['order_amount']:
                return 'UNDERPAID'
            else:
                return 'OVERPAID'
        
        def get_payment_invoice_status(row):
            if row['invoice_amount'] == 0:
                return 'NO_INVOICE'
            elif abs(row['payment_amount'] - row['invoice_amount']) <= 1:
                return 'MATCHED'
            elif row['invoice_amount'] < row['payment_amount']:
                return 'UNDER_INVOICED'
            else:
                return 'OVER_INVOICED'
        
        def get_overall_status(row):
            if row['order_payment_status'] == 'MATCHED' and row['payment_invoice_status'] in ('MATCHED', 'NO_INVOICE'):
                return 'MATCHED'
            else:
                return 'UNMATCHED'
        
        df['recon_date'] = datetime.now().date()
        df['order_payment_status'] = df.apply(get_order_payment_status, axis=1)
        df['payment_invoice_status'] = df.apply(get_payment_invoice_status, axis=1)
        df['overall_status'] = df.apply(get_overall_status, axis=1)
        
        # Calculate variances
        df['order_payment_variance'] = df['payment_amount'] - df['order_amount']
        df['payment_invoice_variance'] = df['invoice_amount'] - df['payment_amount']
        
        # Handle NaN/NaT values
        df = df.where(pd.notnull(df), None)
        
        # Select final columns
        recon_cols = [
            'recon_date', 'order_id', 'order_number', 'customer_id', 'date_key',
            'order_amount', 'order_status', 'order_date',
            'payment_count', 'payment_amount', 'last_payment_date',
            'invoice_count', 'invoice_amount',
            'order_payment_status', 'payment_invoice_status', 'overall_status',
            'order_payment_variance', 'payment_invoice_variance'
        ]
        
        df = df[recon_cols]
        
        # Insert to DW
        from psycopg2.extras import execute_values
        conn = self.dw.raw_connection()
        try:
            cur = conn.cursor()
            cur.execute("TRUNCATE TABLE reconcile.fact_reconciliation")
            
            columns = df.columns.tolist()
            col_str = ', '.join([f'"{c}"' for c in columns])
            
            def clean_value(v):
                if pd.isna(v) or v is pd.NaT:
                    return None
                if isinstance(v, (np.integer, np.floating)):
                    return float(v) if isinstance(v, np.floating) else int(v)
                if hasattr(v, 'date'):  # Handle pandas Timestamp
                    return v.date() if hasattr(v, 'date') else v
                return v
            
            values = [tuple(clean_value(v) for v in row) for row in df.values]
            
            insert_sql = f'INSERT INTO reconcile.fact_reconciliation ({col_str}) VALUES %s'
            execute_values(cur, insert_sql, values, page_size=1000)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        
        # Log summary
        matched = len(df[df['overall_status'] == 'MATCHED'])
        unmatched = len(df[df['overall_status'] == 'UNMATCHED'])
        match_rate = 100.0 * matched / len(df) if len(df) > 0 else 0
        
        logger.info(f"✅ Loaded {len(df):,} rows into reconcile.fact_reconciliation")
        logger.info(f"   Matched: {matched:,} ({match_rate:.1f}%)")
        logger.info(f"   Unmatched: {unmatched:,}")
        
        return len(df)


def get_engines():
    """Create database engine connections"""
    source_url = f"postgresql://{os.getenv('SOURCE_DB_USER', 'postgres')}:{os.getenv('SOURCE_DB_PASSWORD', 'postgres')}@{os.getenv('SOURCE_DB_HOST', 'localhost')}:{os.getenv('SOURCE_DB_PORT', '5432')}/{os.getenv('SOURCE_DB_NAME', 'ecommerce_source')}"
    dw_url = f"postgresql://{os.getenv('DW_DB_USER', 'postgres')}:{os.getenv('DW_DB_PASSWORD', 'postgres')}@{os.getenv('DW_DB_HOST', 'localhost')}:{os.getenv('DW_DB_PORT', '5433')}/{os.getenv('DW_DB_NAME', 'data_warehouse')}"
    
    source_engine = create_engine(source_url)
    dw_engine = create_engine(dw_url)
    
    return source_engine, dw_engine


if __name__ == "__main__":
    source_engine, dw_engine = get_engines()
    loader = ReconciliationLoader(source_engine, dw_engine)
    loader.load_fact_reconciliation()
