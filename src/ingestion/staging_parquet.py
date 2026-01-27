"""
Parquet Staging Layer
Exports source data to Parquet format in MinIO for optimized ETL processing.
"""

import os
import io
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# MinIO Configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin123')
STAGING_BUCKET = 'staging'


def get_source_engine():
    url = f"postgresql://{os.getenv('SOURCE_DB_USER', 'postgres')}:{os.getenv('SOURCE_DB_PASSWORD', 'postgres')}@{os.getenv('SOURCE_DB_HOST', 'localhost')}:{os.getenv('SOURCE_DB_PORT', '5432')}/{os.getenv('SOURCE_DB_NAME', 'ecommerce_source')}"
    return create_engine(url)


def get_minio_client():
    """Get MinIO client for S3-compatible storage."""
    try:
        from minio import Minio
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        return client
    except ImportError:
        logger.warning("minio package not installed. Install with: pip install minio")
        return None


class ParquetStaging:
    """Export source tables to Parquet in MinIO."""
    
    TABLES_TO_EXPORT = [
        ('ecommerce', 'customers'),
        ('ecommerce', 'products'),
        ('ecommerce', 'categories'),
        ('ecommerce', 'orders'),
        ('ecommerce', 'order_items'),
        ('ecommerce', 'payments'),
    ]
    
    def __init__(self, source_engine, minio_client=None):
        self.source_engine = source_engine
        self.minio_client = minio_client
        self.run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def export_table_to_parquet(self, schema, table):
        """Export a single table to Parquet format."""
        logger.info(f"Exporting {schema}.{table}...")
        
        # Read from source
        query = f"SELECT * FROM {schema}.{table}"
        df = pd.read_sql(query, self.source_engine)
        
        if df.empty:
            logger.warning(f"  {schema}.{table} is empty, skipping")
            return 0
        
        # Generate Parquet filename
        filename = f"{table}/{self.run_timestamp}.parquet"
        
        if self.minio_client:
            # Write to MinIO
            buffer = io.BytesIO()
            df.to_parquet(buffer, engine='pyarrow', index=False)
            buffer.seek(0)
            
            self.minio_client.put_object(
                STAGING_BUCKET,
                filename,
                buffer,
                length=buffer.getbuffer().nbytes,
                content_type='application/octet-stream'
            )
            logger.info(f"  ✅ Uploaded to minio://{STAGING_BUCKET}/{filename} ({len(df)} rows)")
        else:
            # Fallback: Save locally
            local_path = f"data/staging/{table}"
            os.makedirs(local_path, exist_ok=True)
            filepath = f"{local_path}/{self.run_timestamp}.parquet"
            df.to_parquet(filepath, engine='pyarrow', index=False)
            logger.info(f"  ✅ Saved to {filepath} ({len(df)} rows)")
        
        return len(df)
    
    def run(self):
        """Export all tables to Parquet."""
        logger.info("=" * 60)
        logger.info("PARQUET STAGING PIPELINE")
        logger.info(f"Run Timestamp: {self.run_timestamp}")
        logger.info("=" * 60)
        
        # Ensure bucket exists (if using MinIO)
        if self.minio_client:
            if not self.minio_client.bucket_exists(STAGING_BUCKET):
                self.minio_client.make_bucket(STAGING_BUCKET)
                logger.info(f"Created bucket: {STAGING_BUCKET}")
        
        total_rows = 0
        for schema, table in self.TABLES_TO_EXPORT:
            rows = self.export_table_to_parquet(schema, table)
            total_rows += rows
        
        logger.info("=" * 60)
        logger.info(f"Staging complete! Total rows exported: {total_rows:,}")
        logger.info("=" * 60)
        
        return total_rows


def run_staging():
    """Main entry point for Parquet staging."""
    source_engine = get_source_engine()
    minio_client = get_minio_client()
    
    stager = ParquetStaging(source_engine, minio_client)
    return stager.run()


if __name__ == "__main__":
    run_staging()
