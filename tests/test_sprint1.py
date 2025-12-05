"""
===============================================================================
FILE: test_sprint1.py
PURPOSE: Test cases cho Sprint 1 - Verify schema, data generation, và staging
AUTHOR: QC/QA Team
VERSION: 1.0

HƯỚNG DẪN SỬ DỤNG:
    # Chạy tất cả tests
    pytest tests/test_sprint1.py -v
    
    # Chạy một test cụ thể
    pytest tests/test_sprint1.py::TestSourceSchema::test_all_tables_exist -v
    
    # Chạy với output detail
    pytest tests/test_sprint1.py -v --tb=short

CÁC LOẠI TEST:
    1. Schema Tests - Kiểm tra cấu trúc database
    2. Data Generation Tests - Kiểm tra dữ liệu giả lập
    3. Staging Tests - Kiểm tra export sang staging
===============================================================================
"""

import os
import sys
from pathlib import Path
from datetime import date
import pytest
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Load environment
load_dotenv()

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def db_engine():
    """
    💡 GIẢI THÍCH:
    Fixture tạo connection đến database.
    scope="module" nghĩa là connection được reuse trong cả module.
    """
    connection_string = (
        f"postgresql://{os.getenv('SOURCE_DB_USER', 'postgres')}:"
        f"{os.getenv('SOURCE_DB_PASSWORD', 'postgres')}@"
        f"{os.getenv('SOURCE_DB_HOST', 'localhost')}:"
        f"{os.getenv('SOURCE_DB_PORT', '5432')}/"
        f"{os.getenv('SOURCE_DB_NAME', 'ecommerce_source')}"
    )
    
    engine = create_engine(connection_string)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def staging_path():
    """Path đến staging directory"""
    return Path(os.getenv('STAGING_PATH', './data/staging'))


# ============================================================================
# TEST CLASS 1: SOURCE SCHEMA TESTS
# ============================================================================

class TestSourceSchema:
    """
    💡 GIẢI THÍCH:
    Test cases kiểm tra schema của database nguồn.
    Đảm bảo tất cả tables, columns, constraints đều đúng.
    """
    
    EXPECTED_TABLES = [
        'categories',
        'products',
        'customers',
        'orders',
        'order_items',
        'payments',
        'invoices',
        'invoice_items'
    ]
    
    def test_all_tables_exist(self, db_engine):
        """TC-001: Kiểm tra tất cả tables required đều tồn tại"""
        inspector = inspect(db_engine)
        actual_tables = inspector.get_table_names(schema='ecommerce')
        
        for table in self.EXPECTED_TABLES:
            assert table in actual_tables, f"Missing table: {table}"
    
    def test_categories_schema(self, db_engine):
        """TC-002: Kiểm tra schema của bảng categories"""
        inspector = inspect(db_engine)
        columns = {col['name']: col for col in inspector.get_columns('categories', schema='ecommerce')}
        
        required_columns = ['id', 'name', 'description', 'parent_id', 'is_active', 'created_at', 'updated_at']
        
        for col in required_columns:
            assert col in columns, f"Missing column in categories: {col}"
    
    def test_customers_has_required_columns(self, db_engine):
        """TC-003: Kiểm tra customers có các cột bắt buộc"""
        inspector = inspect(db_engine)
        columns = {col['name'] for col in inspector.get_columns('customers', schema='ecommerce')}
        
        required = {'id', 'customer_code', 'email', 'first_name', 'last_name', 'segment'}
        missing = required - columns
        
        assert not missing, f"Missing columns in customers: {missing}"
    
    def test_orders_has_required_columns(self, db_engine):
        """TC-004: Kiểm tra orders có các cột bắt buộc"""
        inspector = inspect(db_engine)
        columns = {col['name'] for col in inspector.get_columns('orders', schema='ecommerce')}
        
        required = {'id', 'order_number', 'customer_id', 'order_date', 'status', 'total_amount', 'channel'}
        missing = required - columns
        
        assert not missing, f"Missing columns in orders: {missing}"
    
    def test_primary_keys_exist(self, db_engine):
        """TC-005: Kiểm tra tất cả tables có Primary Key"""
        inspector = inspect(db_engine)
        
        for table in self.EXPECTED_TABLES:
            pk = inspector.get_pk_constraint(table, schema='ecommerce')
            assert pk and pk['constrained_columns'], f"No PK for table: {table}"
    
    def test_foreign_keys_exist(self, db_engine):
        """TC-006: Kiểm tra Foreign Keys đúng"""
        inspector = inspect(db_engine)
        
        # orders -> customers
        orders_fks = inspector.get_foreign_keys('orders', schema='ecommerce')
        customer_fk = [fk for fk in orders_fks if 'customer_id' in fk['constrained_columns']]
        assert customer_fk, "Missing FK orders.customer_id -> customers"
        
        # order_items -> orders
        items_fks = inspector.get_foreign_keys('order_items', schema='ecommerce')
        order_fk = [fk for fk in items_fks if 'order_id' in fk['constrained_columns']]
        assert order_fk, "Missing FK order_items.order_id -> orders"


# ============================================================================
# TEST CLASS 2: DATA GENERATION TESTS
# ============================================================================

class TestDataGeneration:
    """
    💡 GIẢI THÍCH:
    Test cases kiểm tra dữ liệu đã được generate đúng.
    Bao gồm: row counts, data integrity, distributions.
    """
    
    def test_categories_has_data(self, db_engine):
        """TC-010: Categories phải có ít nhất 10 records"""
        count = pd.read_sql("SELECT COUNT(*) as cnt FROM ecommerce.categories", db_engine)['cnt'][0]
        assert count >= 10, f"Expected >= 10 categories, got {count}"
    
    def test_customers_has_data(self, db_engine):
        """TC-011: Customers phải có ít nhất 1000 records"""
        count = pd.read_sql("SELECT COUNT(*) as cnt FROM ecommerce.customers", db_engine)['cnt'][0]
        assert count >= 1000, f"Expected >= 1000 customers, got {count}"
    
    def test_products_has_data(self, db_engine):
        """TC-012: Products phải có ít nhất 100 records"""
        count = pd.read_sql("SELECT COUNT(*) as cnt FROM ecommerce.products", db_engine)['cnt'][0]
        assert count >= 100, f"Expected >= 100 products, got {count}"
    
    def test_orders_has_data(self, db_engine):
        """TC-013: Orders phải có ít nhất 10000 records"""
        count = pd.read_sql("SELECT COUNT(*) as cnt FROM ecommerce.orders", db_engine)['cnt'][0]
        assert count >= 10000, f"Expected >= 10000 orders, got {count}"
    
    def test_no_orphan_orders(self, db_engine):
        """TC-020: Không có order nào trỏ tới customer không tồn tại"""
        query = """
            SELECT COUNT(*) as cnt
            FROM ecommerce.orders o
            LEFT JOIN ecommerce.customers c ON o.customer_id = c.id
            WHERE c.id IS NULL
        """
        orphans = pd.read_sql(query, db_engine)['cnt'][0]
        assert orphans == 0, f"Found {orphans} orphan orders"
    
    def test_no_orphan_order_items(self, db_engine):
        """TC-021: Không có order_item nào trỏ tới order không tồn tại"""
        query = """
            SELECT COUNT(*) as cnt
            FROM ecommerce.order_items oi
            LEFT JOIN ecommerce.orders o ON oi.order_id = o.id
            WHERE o.id IS NULL
        """
        orphans = pd.read_sql(query, db_engine)['cnt'][0]
        assert orphans == 0, f"Found {orphans} orphan order items"
    
    def test_no_orphan_order_items_products(self, db_engine):
        """TC-022: Không có order_item nào trỏ tới product không tồn tại"""
        query = """
            SELECT COUNT(*) as cnt
            FROM ecommerce.order_items oi
            LEFT JOIN ecommerce.products p ON oi.product_id = p.id
            WHERE p.id IS NULL
        """
        orphans = pd.read_sql(query, db_engine)['cnt'][0]
        assert orphans == 0, f"Found {orphans} order items with invalid product"
    
    def test_order_dates_in_range(self, db_engine):
        """TC-030: Order dates nằm trong khoảng expected"""
        query = """
            SELECT 
                MIN(order_date) as min_date,
                MAX(order_date) as max_date
            FROM ecommerce.orders
        """
        dates = pd.read_sql(query, db_engine)
        min_date = dates['min_date'][0]
        max_date = dates['max_date'][0]
        
        # Expect data from 2024
        assert min_date.year == 2024, f"Min date year should be 2024, got {min_date}"
        assert max_date.year == 2024, f"Max date year should be 2024, got {max_date}"
    
    def test_order_status_valid(self, db_engine):
        """TC-031: Tất cả order status đều là giá trị hợp lệ"""
        valid_statuses = {'Pending', 'Processing', 'Shipped', 'Delivered', 'Completed', 'Cancelled', 'Refunded'}
        
        query = "SELECT DISTINCT status FROM ecommerce.orders"
        actual_statuses = set(pd.read_sql(query, db_engine)['status'].tolist())
        
        invalid = actual_statuses - valid_statuses
        assert not invalid, f"Found invalid statuses: {invalid}"
    
    def test_payment_methods_valid(self, db_engine):
        """TC-032: Tất cả payment methods đều hợp lệ"""
        valid_methods = {'Credit Card', 'Bank Transfer', 'COD', 'E-Wallet', 'Cash'}
        
        query = "SELECT DISTINCT payment_method FROM ecommerce.payments"
        actual = set(pd.read_sql(query, db_engine)['payment_method'].tolist())
        
        invalid = actual - valid_methods
        assert not invalid, f"Found invalid payment methods: {invalid}"
    
    def test_positive_amounts(self, db_engine):
        """TC-033: Tất cả order total_amount > 0"""
        query = """
            SELECT COUNT(*) as cnt
            FROM ecommerce.orders
            WHERE total_amount <= 0
        """
        invalid = pd.read_sql(query, db_engine)['cnt'][0]
        assert invalid == 0, f"Found {invalid} orders with total_amount <= 0"
    
    def test_customer_segments_valid(self, db_engine):
        """TC-034: Customer segments đều hợp lệ"""
        valid_segments = {'VIP', 'Regular', 'Occasional', 'New', 'Churned'}
        
        query = "SELECT DISTINCT segment FROM ecommerce.customers WHERE segment IS NOT NULL"
        actual = set(pd.read_sql(query, db_engine)['segment'].tolist())
        
        invalid = actual - valid_segments
        assert not invalid, f"Found invalid segments: {invalid}"
    
    def test_unique_customer_codes(self, db_engine):
        """TC-035: Customer codes phải unique"""
        query = """
            SELECT customer_code, COUNT(*) as cnt
            FROM ecommerce.customers
            GROUP BY customer_code
            HAVING COUNT(*) > 1
        """
        duplicates = pd.read_sql(query, db_engine)
        assert len(duplicates) == 0, f"Found duplicate customer codes: {duplicates['customer_code'].tolist()}"
    
    def test_unique_order_numbers(self, db_engine):
        """TC-036: Order numbers phải unique"""
        query = """
            SELECT order_number, COUNT(*) as cnt
            FROM ecommerce.orders
            GROUP BY order_number
            HAVING COUNT(*) > 1
        """
        duplicates = pd.read_sql(query, db_engine)
        assert len(duplicates) == 0, f"Found duplicate order numbers"


# ============================================================================
# TEST CLASS 3: STAGING TESTS
# ============================================================================

class TestStaging:
    """
    💡 GIẢI THÍCH:
    Test cases kiểm tra staging layer.
    Verify files được tạo đúng và data khớp với source.
    """
    
    EXPECTED_TABLES = [
        'categories',
        'products',
        'customers',
        'orders',
        'order_items',
        'payments',
        'invoices',
        'invoice_items'
    ]
    
    @pytest.fixture
    def latest_snapshot(self, staging_path):
        """Lấy snapshot mới nhất"""
        snapshots = sorted(staging_path.glob("snapshot_date=*"))
        if not snapshots:
            pytest.skip("No staging snapshots found")
        return snapshots[-1]
    
    def test_staging_directory_exists(self, staging_path):
        """TC-050: Staging directory phải tồn tại"""
        assert staging_path.exists(), f"Staging path not found: {staging_path}"
    
    def test_snapshot_exists(self, staging_path):
        """TC-051: Ít nhất 1 snapshot phải tồn tại"""
        snapshots = list(staging_path.glob("snapshot_date=*"))
        assert len(snapshots) > 0, "No snapshots found in staging"
    
    def test_all_tables_exported(self, latest_snapshot):
        """TC-052: Tất cả tables phải được export"""
        for table in self.EXPECTED_TABLES:
            csv_file = latest_snapshot / f"{table}.csv"
            parquet_file = latest_snapshot / f"{table}.parquet"
            
            assert csv_file.exists() or parquet_file.exists(), f"Missing export for: {table}"
    
    def test_success_marker_exists(self, latest_snapshot):
        """TC-053: _SUCCESS marker phải tồn tại"""
        success_file = latest_snapshot / "_SUCCESS"
        assert success_file.exists(), f"Missing _SUCCESS marker in {latest_snapshot}"
    
    def test_metadata_exists(self, latest_snapshot):
        """TC-054: _metadata.json phải tồn tại"""
        metadata_file = latest_snapshot / "_metadata.json"
        assert metadata_file.exists(), f"Missing _metadata.json in {latest_snapshot}"
    
    def test_row_count_customers(self, db_engine, latest_snapshot):
        """TC-060: Row count customers staging = source"""
        # Source count
        source_count = pd.read_sql(
            "SELECT COUNT(*) as cnt FROM ecommerce.customers", 
            db_engine
        )['cnt'][0]
        
        # Staging count
        staging_file = latest_snapshot / "customers.csv"
        if staging_file.exists():
            staging_count = len(pd.read_csv(staging_file))
        else:
            staging_file = latest_snapshot / "customers.parquet"
            staging_count = len(pd.read_parquet(staging_file))
        
        assert source_count == staging_count, f"Mismatch: source={source_count}, staging={staging_count}"
    
    def test_row_count_orders(self, db_engine, latest_snapshot):
        """TC-061: Row count orders staging = source"""
        source_count = pd.read_sql(
            "SELECT COUNT(*) as cnt FROM ecommerce.orders", 
            db_engine
        )['cnt'][0]
        
        staging_file = latest_snapshot / "orders.csv"
        if staging_file.exists():
            staging_count = len(pd.read_csv(staging_file))
        else:
            staging_file = latest_snapshot / "orders.parquet"
            staging_count = len(pd.read_parquet(staging_file))
        
        assert source_count == staging_count, f"Mismatch: source={source_count}, staging={staging_count}"
    
    def test_files_not_empty(self, latest_snapshot):
        """TC-070: Các files không được empty"""
        for table in self.EXPECTED_TABLES:
            csv_file = latest_snapshot / f"{table}.csv"
            if csv_file.exists():
                size = csv_file.stat().st_size
                assert size > 100, f"File {table}.csv seems empty (size={size})"


# ============================================================================
# TEST CLASS 4: DATA QUALITY TESTS
# ============================================================================

class TestDataQuality:
    """
    💡 GIẢI THÍCH:
    Test cases kiểm tra chất lượng dữ liệu.
    Những rules này sẽ được mở rộng trong Sprint 4.
    """
    
    def test_no_null_customer_email(self, db_engine):
        """DQ-001: Email khách hàng không được NULL"""
        query = "SELECT COUNT(*) as cnt FROM ecommerce.customers WHERE email IS NULL"
        null_count = pd.read_sql(query, db_engine)['cnt'][0]
        assert null_count == 0, f"Found {null_count} customers with NULL email"
    
    def test_no_null_order_customer_id(self, db_engine):
        """DQ-002: Order customer_id không được NULL"""
        query = "SELECT COUNT(*) as cnt FROM ecommerce.orders WHERE customer_id IS NULL"
        null_count = pd.read_sql(query, db_engine)['cnt'][0]
        assert null_count == 0, f"Found {null_count} orders with NULL customer_id"
    
    def test_email_format_valid(self, db_engine):
        """DQ-003: Email phải có format hợp lệ (chứa @)"""
        query = """
            SELECT COUNT(*) as cnt 
            FROM ecommerce.customers 
            WHERE email NOT LIKE '%@%'
        """
        invalid = pd.read_sql(query, db_engine)['cnt'][0]
        assert invalid == 0, f"Found {invalid} customers with invalid email format"
    
    def test_order_total_equals_sum_items(self, db_engine):
        """DQ-010: Order subtotal gần bằng sum(order_items.line_total)"""
        # Kiểm tra random sample 100 orders
        query = """
            SELECT 
                o.id,
                o.subtotal as order_subtotal,
                COALESCE(SUM(oi.line_total), 0) as items_total,
                ABS(o.subtotal - COALESCE(SUM(oi.line_total), 0)) as diff
            FROM ecommerce.orders o
            LEFT JOIN ecommerce.order_items oi ON o.id = oi.order_id
            GROUP BY o.id
            HAVING ABS(o.subtotal - COALESCE(SUM(oi.line_total), 0)) > 1
            LIMIT 100
        """
        mismatches = pd.read_sql(query, db_engine)
        
        # Cho phép một số sai lệch nhỏ do rounding
        assert len(mismatches) < 10, f"Found {len(mismatches)} orders with total mismatch"


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
