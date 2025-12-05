"""
===============================================================================
FILE: export_to_staging.py
PURPOSE: Export dữ liệu từ DB nguồn vào Staging Layer (Data Lake)
AUTHOR: Data Engineering Team
VERSION: 1.0

HƯỚNG DẪN SỬ DỤNG:
    # Full export tất cả tables
    python src/ingestion/export_to_staging.py
    
    # Export một table cụ thể
    python src/ingestion/export_to_staging.py --table orders
    
    # Export với format parquet
    python src/ingestion/export_to_staging.py --format parquet
    
    # Export với snapshot date cụ thể
    python src/ingestion/export_to_staging.py --date 2024-01-15

KIẾN TRÚC:
    ┌─────────────────┐          ┌─────────────────┐
    │  PostgreSQL     │  ─────►  │  Staging Layer  │
    │  (ecommerce)    │          │  (data/staging) │
    └─────────────────┘          └─────────────────┘
           │                              │
           │                              ▼
           │                     snapshot_date=YYYY-MM-DD/
           │                          ├── customers.csv
           │                          ├── products.csv
           │                          ├── orders.csv
           │                          └── ...
           │
           ▼
    SELECT * FROM table
===============================================================================
"""

import os
import sys
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
import logging
import json
import time

# Third-party imports
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class IngestConfig:
    """
    💡 GIẢI THÍCH:
    Configuration class cho pipeline ingest.
    Tập trung các config để dễ quản lý và thay đổi.
    """
    
    # Danh sách tables cần export (theo thứ tự dependency)
    TABLES = [
        'categories',
        'products', 
        'customers',
        'orders',
        'order_items',
        'payments',
        'invoices',
        'invoice_items',
    ]
    
    # Schema của source database
    SOURCE_SCHEMA = 'ecommerce'
    
    # Output formats hỗ trợ
    SUPPORTED_FORMATS = ['csv', 'parquet']
    
    # Default staging path
    STAGING_PATH = os.getenv('STAGING_PATH', './data/staging')


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

class SourceDatabase:
    """
    💡 GIẢI THÍCH:
    Class quản lý kết nối đến database nguồn.
    Sử dụng SQLAlchemy để có thể dễ dàng switch sang DB khác.
    """
    
    def __init__(self):
        """Khởi tạo connection từ environment variables"""
        self.host = os.getenv('SOURCE_DB_HOST', 'localhost')
        self.port = os.getenv('SOURCE_DB_PORT', '5432')
        self.database = os.getenv('SOURCE_DB_NAME', 'ecommerce_source')
        self.user = os.getenv('SOURCE_DB_USER', 'postgres')
        self.password = os.getenv('SOURCE_DB_PASSWORD', 'postgres')
        
        self.connection_string = (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )
        self.engine = None
    
    def connect(self):
        """Tạo kết nối đến database"""
        try:
            self.engine = create_engine(
                self.connection_string,
                # Connection pool settings
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True  # Kiểm tra connection còn sống không
            )
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"✅ Connected to: {self.database}")
                logger.debug(f"PostgreSQL version: {version}")
                
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            raise
    
    def close(self):
        """Đóng kết nối"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def get_table_data(self, table_name: str, schema: str = 'ecommerce') -> pd.DataFrame:
        """
        Đọc toàn bộ dữ liệu từ một table.
        
        💡 GIẢI THÍCH:
        Full load - đọc hết SELECT * FROM table
        Sprint 2 sẽ implement incremental load với WHERE updated_at > last_run
        
        Args:
            table_name: Tên bảng
            schema: Schema name
            
        Returns:
            DataFrame chứa data
        """
        query = f"SELECT * FROM {schema}.{table_name}"
        
        try:
            df = pd.read_sql(query, self.engine)
            logger.info(f"Read {len(df)} rows from {schema}.{table_name}")
            return df
        except Exception as e:
            logger.error(f"Failed to read {table_name}: {e}")
            raise
    
    def get_row_count(self, table_name: str, schema: str = 'ecommerce') -> int:
        """Lấy số lượng rows trong table"""
        query = f"SELECT COUNT(*) FROM {schema}.{table_name}"
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return result.fetchone()[0]


# ============================================================================
# STAGING LAYER
# ============================================================================

class StagingLayer:
    """
    💡 GIẢI THÍCH:
    Class quản lý Staging Layer - nơi lưu trữ dữ liệu raw từ source.
    
    Staging Layer có nhiệm vụ:
    1. Lưu trữ dữ liệu raw (không transform)
    2. Partition theo snapshot_date để track lịch sử
    3. Cho phép replay/recover khi cần
    
    Structure:
        data/staging/
            snapshot_date=2024-01-01/
                customers.csv
                products.csv
                ...
            snapshot_date=2024-01-02/
                ...
    """
    
    def __init__(self, base_path: str, snapshot_date: date = None):
        """
        Args:
            base_path: Đường dẫn gốc của staging (e.g., ./data/staging)
            snapshot_date: Ngày snapshot, mặc định là hôm nay
        """
        self.base_path = Path(base_path)
        self.snapshot_date = snapshot_date or date.today()
        
        # Tạo đường dẫn cho snapshot này
        self.snapshot_path = self.base_path / f"snapshot_date={self.snapshot_date.isoformat()}"
    
    def setup(self):
        """Tạo thư mục nếu chưa tồn tại"""
        self.snapshot_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Staging path: {self.snapshot_path}")
    
    def write_csv(self, df: pd.DataFrame, table_name: str) -> Path:
        """
        Ghi DataFrame ra file CSV.
        
        💡 GIẢI THÍCH:
        CSV được dùng trong Sprint 1 vì:
        - Dễ debug (mở bằng Excel)
        - Human-readable
        - Không cần cài thêm thư viện
        
        Args:
            df: DataFrame cần ghi
            table_name: Tên table (làm tên file)
            
        Returns:
            Path đến file đã ghi
        """
        file_path = self.snapshot_path / f"{table_name}.csv"
        
        try:
            df.to_csv(
                file_path,
                index=False,
                encoding='utf-8',
                date_format='%Y-%m-%d %H:%M:%S'  # Format datetime chuẩn
            )
            logger.info(f"✅ Written: {file_path} ({len(df)} rows)")
            return file_path
        except Exception as e:
            logger.error(f"❌ Failed to write {table_name}.csv: {e}")
            raise
    
    def write_parquet(self, df: pd.DataFrame, table_name: str) -> Path:
        """
        Ghi DataFrame ra file Parquet.
        
        💡 GIẢI THÍCH:
        Parquet được khuyên dùng trong production vì:
        - Nén tốt (70-90% smaller than CSV)
        - Columnar format (query nhanh)
        - Schema được lưu trong file
        - Hỗ trợ partition tốt
        
        Args:
            df: DataFrame cần ghi
            table_name: Tên table
            
        Returns:
            Path đến file đã ghi
        """
        file_path = self.snapshot_path / f"{table_name}.parquet"
        
        try:
            df.to_parquet(
                file_path,
                index=False,
                engine='pyarrow',  # Dùng pyarrow engine
                compression='snappy'  # Nén bằng snappy (nhanh, ratio tốt)
            )
            
            # Log file size comparison
            csv_size = len(df.to_csv(index=False).encode('utf-8'))
            parquet_size = file_path.stat().st_size
            compression_ratio = (1 - parquet_size / csv_size) * 100
            
            logger.info(f"✅ Written: {file_path} ({len(df)} rows, {compression_ratio:.1f}% smaller than CSV)")
            return file_path
        except Exception as e:
            logger.error(f"❌ Failed to write {table_name}.parquet: {e}")
            raise
    
    def write_metadata(self, metadata: Dict) -> Path:
        """
        Ghi metadata file cho snapshot.
        
        💡 GIẢI THÍCH:
        Metadata giúp track:
        - Thời điểm chạy pipeline
        - Số rows mỗi table
        - Version, errors...
        
        Args:
            metadata: Dict chứa thông tin
            
        Returns:
            Path đến metadata file
        """
        file_path = self.snapshot_path / "_metadata.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Written metadata: {file_path}")
        return file_path
    
    def write_success_marker(self) -> Path:
        """
        Tạo _SUCCESS file đánh dấu export thành công.
        
        💡 GIẢI THÍCH:
        Pattern phổ biến trong data engineering:
        - Spark, Hadoop đều dùng _SUCCESS marker
        - Downstream jobs kiểm tra file này trước khi đọc
        - Nếu không có = export chưa hoàn thành
        """
        file_path = self.snapshot_path / "_SUCCESS"
        file_path.touch()
        logger.info(f"Written success marker: {file_path}")
        return file_path


# ============================================================================
# INGEST PIPELINE
# ============================================================================

class IngestPipeline:
    """
    💡 GIẢI THÍCH:
    Main pipeline class điều phối toàn bộ quá trình ingest.
    
    Pipeline flow:
    1. Connect to source database
    2. For each table:
       a. Read data from source
       b. Write to staging layer
       c. Log results
    3. Write metadata
    4. Write success marker
    """
    
    def __init__(
        self,
        tables: List[str] = None,
        output_format: str = 'csv',
        snapshot_date: date = None,
        staging_path: str = None
    ):
        """
        Args:
            tables: List tables cần export (None = all)
            output_format: 'csv' hoặc 'parquet'
            snapshot_date: Ngày snapshot
            staging_path: Đường dẫn staging
        """
        self.tables = tables or IngestConfig.TABLES
        self.output_format = output_format
        self.snapshot_date = snapshot_date or date.today()
        self.staging_path = staging_path or IngestConfig.STAGING_PATH
        
        # Validate format
        if output_format not in IngestConfig.SUPPORTED_FORMATS:
            raise ValueError(f"Format must be one of: {IngestConfig.SUPPORTED_FORMATS}")
        
        # Initialize components
        self.db = SourceDatabase()
        self.staging = StagingLayer(self.staging_path, self.snapshot_date)
        
        # Track results
        self.results = []
    
    def run(self) -> Dict:
        """
        Chạy pipeline ingest.
        
        Returns:
            Dict chứa kết quả và thống kê
        """
        logger.info("="*60)
        logger.info("Starting Ingest Pipeline")
        logger.info(f"Snapshot date: {self.snapshot_date}")
        logger.info(f"Output format: {self.output_format}")
        logger.info(f"Tables: {', '.join(self.tables)}")
        logger.info("="*60)
        
        start_time = time.time()
        
        try:
            # Setup
            self.db.connect()
            self.staging.setup()
            
            # Export each table
            for table in self.tables:
                self._export_table(table)
            
            # Write metadata
            duration = time.time() - start_time
            metadata = self._create_metadata(duration)
            self.staging.write_metadata(metadata)
            
            # Write success marker
            self.staging.write_success_marker()
            
            # Summary
            self._print_summary(duration)
            
            return {
                'success': True,
                'snapshot_date': self.snapshot_date.isoformat(),
                'duration_seconds': round(duration, 2),
                'tables': self.results
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tables': self.results
            }
        finally:
            self.db.close()
    
    def _export_table(self, table_name: str):
        """
        Export một table từ source sang staging.
        
        Args:
            table_name: Tên table cần export
        """
        logger.info(f"\n📦 Exporting: {table_name}")
        start_time = time.time()
        
        try:
            # Read from source
            df = self.db.get_table_data(table_name)
            
            # Write to staging
            if self.output_format == 'csv':
                output_path = self.staging.write_csv(df, table_name)
            else:
                output_path = self.staging.write_parquet(df, table_name)
            
            duration = time.time() - start_time
            
            # Record result
            self.results.append({
                'table': table_name,
                'status': 'success',
                'rows': len(df),
                'file': str(output_path),
                'duration_seconds': round(duration, 2)
            })
            
        except Exception as e:
            logger.error(f"Failed to export {table_name}: {e}")
            self.results.append({
                'table': table_name,
                'status': 'failed',
                'error': str(e)
            })
            raise
    
    def _create_metadata(self, duration: float) -> Dict:
        """Tạo metadata dict"""
        return {
            'pipeline': 'source_to_staging',
            'snapshot_date': self.snapshot_date.isoformat(),
            'run_timestamp': datetime.now().isoformat(),
            'duration_seconds': round(duration, 2),
            'output_format': self.output_format,
            'source': {
                'host': self.db.host,
                'database': self.db.database,
                'schema': IngestConfig.SOURCE_SCHEMA
            },
            'tables': self.results
        }
    
    def _print_summary(self, duration: float):
        """In summary sau khi chạy xong"""
        logger.info("\n" + "="*60)
        logger.info("✅ Ingest Pipeline Completed")
        logger.info("="*60)
        
        total_rows = sum(r.get('rows', 0) for r in self.results)
        success_count = sum(1 for r in self.results if r['status'] == 'success')
        
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Tables: {success_count}/{len(self.results)} successful")
        logger.info(f"Total rows: {total_rows:,}")
        logger.info(f"Output: {self.staging.snapshot_path}")
        
        # Table-by-table summary
        logger.info("\n📊 Table Summary:")
        for result in self.results:
            status_icon = "✅" if result['status'] == 'success' else "❌"
            rows = result.get('rows', 0)
            logger.info(f"  {status_icon} {result['table']}: {rows:,} rows")


# ============================================================================
# DATA VALIDATION
# ============================================================================

class DataValidator:
    """
    💡 GIẢI THÍCH:
    Class để validate dữ liệu sau khi export.
    Đây là phần quan trọng của QC/QA trong data engineering.
    
    Các loại validation:
    1. Row count: Số rows trong staging = source
    2. Schema: Các cột đầy đủ và đúng type
    3. Null check: Các cột required không có null
    4. Sample check: Spot check vài rows
    """
    
    def __init__(self, db: SourceDatabase, staging: StagingLayer):
        self.db = db
        self.staging = staging
    
    def validate_row_counts(self) -> List[Dict]:
        """
        So sánh row count giữa source và staging.
        
        Returns:
            List các validation results
        """
        results = []
        
        for table in IngestConfig.TABLES:
            # Source count
            source_count = self.db.get_row_count(table)
            
            # Staging count
            staging_file = self.staging.snapshot_path / f"{table}.csv"
            if staging_file.exists():
                staging_df = pd.read_csv(staging_file)
                staging_count = len(staging_df)
            else:
                staging_file = self.staging.snapshot_path / f"{table}.parquet"
                if staging_file.exists():
                    staging_df = pd.read_parquet(staging_file)
                    staging_count = len(staging_df)
                else:
                    staging_count = None
            
            # Compare
            match = source_count == staging_count if staging_count is not None else False
            
            results.append({
                'table': table,
                'source_count': source_count,
                'staging_count': staging_count,
                'match': match,
                'status': 'PASS' if match else 'FAIL'
            })
            
            status_icon = "✅" if match else "❌"
            logger.info(f"{status_icon} {table}: source={source_count}, staging={staging_count}")
        
        return results
    
    def validate_sample(self, table: str, sample_size: int = 5) -> pd.DataFrame:
        """
        Lấy sample từ source và staging để so sánh manual.
        
        Args:
            table: Tên table
            sample_size: Số rows để sample
            
        Returns:
            DataFrame comparison
        """
        # Source sample
        source_df = self.db.get_table_data(table).head(sample_size)
        
        # Staging sample
        staging_file = self.staging.snapshot_path / f"{table}.csv"
        if staging_file.exists():
            staging_df = pd.read_csv(staging_file).head(sample_size)
        else:
            staging_df = pd.read_parquet(
                self.staging.snapshot_path / f"{table}.parquet"
            ).head(sample_size)
        
        return source_df, staging_df


# ============================================================================
# CLI INTERFACE
# ============================================================================

def parse_args():
    """
    Parse command line arguments.
    
    💡 GIẢI THÍCH:
    argparse cho phép script nhận tham số từ command line.
    Ví dụ:
        python export_to_staging.py --table orders --format parquet
    """
    parser = argparse.ArgumentParser(
        description='Export data from source database to staging layer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Export all tables as CSV
    python export_to_staging.py
    
    # Export specific table
    python export_to_staging.py --table orders
    
    # Export as Parquet
    python export_to_staging.py --format parquet
    
    # Export with specific date
    python export_to_staging.py --date 2024-01-15
    
    # Validate after export
    python export_to_staging.py --validate
        """
    )
    
    parser.add_argument(
        '--table', '-t',
        type=str,
        help='Specific table to export (default: all tables)'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        default='csv',
        choices=['csv', 'parquet'],
        help='Output format (default: csv)'
    )
    
    parser.add_argument(
        '--date', '-d',
        type=str,
        help='Snapshot date in YYYY-MM-DD format (default: today)'
    )
    
    parser.add_argument(
        '--validate', '-v',
        action='store_true',
        help='Run validation after export'
    )
    
    parser.add_argument(
        '--staging-path',
        type=str,
        default=IngestConfig.STAGING_PATH,
        help=f'Staging layer path (default: {IngestConfig.STAGING_PATH})'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Parse snapshot date
    snapshot_date = None
    if args.date:
        try:
            snapshot_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            sys.exit(1)
    
    # Determine tables
    tables = [args.table] if args.table else None
    
    # Run pipeline
    pipeline = IngestPipeline(
        tables=tables,
        output_format=args.format,
        snapshot_date=snapshot_date,
        staging_path=args.staging_path
    )
    
    result = pipeline.run()
    
    # Run validation if requested
    if args.validate and result['success']:
        logger.info("\n" + "="*60)
        logger.info("Running Validation")
        logger.info("="*60)
        
        validator = DataValidator(pipeline.db, pipeline.staging)
        
        # Reconnect for validation
        pipeline.db.connect()
        validation_results = validator.validate_row_counts()
        pipeline.db.close()
        
        # Check if all passed
        all_passed = all(r['status'] == 'PASS' for r in validation_results)
        
        if all_passed:
            logger.info("\n✅ All validations PASSED")
        else:
            logger.warning("\n⚠️ Some validations FAILED")
            sys.exit(1)
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    main()
