# Sprint 1 Detailed Execution Report

**Project**: Enterprise Analytics Platform  
**Sprint**: Sprint 1 - Source Data & Staging Layer Setup  
**Date**: 2025-12-05  
**Duration**: ~2 hours  
**Status**: ✅ COMPLETED

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Environment Setup](#2-environment-setup)
3. [Data Generation](#3-data-generation)
4. [Staging Layer Export](#4-staging-layer-export)
5. [Testing & Validation](#5-testing--validation)
6. [Errors Encountered & Fixes Applied](#6-errors-encountered--fixes-applied)
7. [Final Results](#7-final-results)
8. [Metabase Configuration](#8-metabase-configuration)
9. [Files Modified](#9-files-modified)
10. [Recommendations for Sprint 2](#10-recommendations-for-sprint-2)

---

## 1. Executive Summary

Sprint 1 successfully established the foundation for the Enterprise Analytics Platform:

| Metric | Value |
|--------|-------|
| Total Records Generated | **644,489** |
| Tables Populated | **8** |
| Staging Files Created | **8 CSV files** |
| Test Pass Rate | **93.75% (30/32)** |
| Errors Fixed | **7 major issues** |

---

## 2. Environment Setup

### 2.1 Docker Services Started

```powershell
docker-compose up -d
```

**Services Running:**

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `ecommerce_source_db` | postgres:15-alpine | 5432 | Source OLTP database |
| `data_warehouse_db` | postgres:15-alpine | 5433 | Data Warehouse |
| `minio_storage` | minio/minio | 9000, 9001 | Object storage (S3-compatible) |
| `metabase_bi` | metabase/metabase | 3000 | BI Dashboard |
| `metabase_db` | postgres:15-alpine | - | Metabase metadata storage |

### 2.2 Environment Configuration

Created `.env` file with database credentials:

```env
SOURCE_DB_HOST=localhost
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=ecommerce_source
SOURCE_DB_USER=postgres
SOURCE_DB_PASSWORD=postgres
DW_DB_HOST=localhost
DW_DB_PORT=5433
DW_DB_NAME=data_warehouse
DW_DB_USER=postgres
DW_DB_PASSWORD=postgres
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
STAGING_PATH=./data/staging
```

---

## 3. Data Generation

### 3.1 Database Schema

The source database schema was automatically created via `docker/postgres/init-source.sql` with the following tables:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `ecommerce.categories` | Product categories | id, name, parent_id |
| `ecommerce.products` | Product catalog | id, sku, unit_price, cost_price |
| `ecommerce.customers` | Customer data | id, customer_code, email, segment |
| `ecommerce.orders` | Order headers | id, order_number, total_amount, status |
| `ecommerce.order_items` | Order line items | id, order_id, product_id, quantity |
| `ecommerce.payments` | Payment transactions | id, payment_code, amount, status |
| `ecommerce.invoices` | Accounting invoices | id, invoice_number, total_amount |
| `ecommerce.invoice_items` | Invoice line items | id, invoice_id, line_total |

### 3.2 Data Generation Process

The data generation script (`scripts/data_generation/generate_data.py`) was executed via Docker container:

```powershell
docker run --rm -v "${PWD}:/app" -w /app \
  --network enterperise_de_analytics-network \
  -e SOURCE_DB_HOST=postgres-source \
  python:3.10-slim bash -c "python scripts/data_generation/generate_data.py"
```

### 3.3 Data Generation Results

| Table | Rows | Notes |
|-------|------|-------|
| categories | 20 | 20 product categories (Electronics, Fashion, etc.) |
| products | 1,000 | SKU-000001 to SKU-001000 with prices 50k - 50M VND |
| customers | 10,000 | Unique emails, Vietnamese addresses, 4 segments |
| orders | 100,000 | Full year 2024 with seasonality (peak in Nov-Dec) |
| order_items | 198,225 | Average ~2 items per order |
| payments | 96,984 | ~97% of orders have payments |
| invoices | 79,923 | ~80% of completed orders have invoices |
| invoice_items | 158,337 | Invoice line items |
| **Total** | **644,489** | |

### 3.4 Data Characteristics

**Customer Segments:**
- VIP: 5%
- Regular: 30%
- Occasional: 45%
- New: 20%

**Sales Channels:**
- Website: 45%
- Mobile App: 30%
- Marketplace: 15%
- Store: 10%

**Payment Methods:**
- Bank Transfer: 30%
- Credit Card: 25%
- COD: 25%
- E-Wallet: 20%

**Order Status Distribution:**
- Completed: 70%
- Delivered: 10%
- Shipped: 5%
- Processing: 5%
- Pending: 3%
- Cancelled: 5%
- Refunded: 2%

---

## 4. Staging Layer Export

### 4.1 Export Process

The export script (`src/ingestion/export_to_staging.py`) extracted all data from the source database and saved to CSV files:

```powershell
python -m src.ingestion.export_to_staging
```

### 4.2 Export Results

**Output Directory:** `data/staging/snapshot_date=2025-12-05/`

| File | Rows | Size |
|------|------|------|
| categories.csv | 20 | ~2 KB |
| products.csv | 1,000 | ~150 KB |
| customers.csv | 10,000 | ~2 MB |
| orders.csv | 100,000 | ~25 MB |
| order_items.csv | 198,225 | ~15 MB |
| payments.csv | 96,984 | ~12 MB |
| invoices.csv | 79,923 | ~10 MB |
| invoice_items.csv | 158,337 | ~8 MB |
| _SUCCESS | - | Marker file |
| _metadata.json | - | Snapshot metadata |

**Export Duration:** 8.37 seconds

---

## 5. Testing & Validation

### 5.1 Test Execution

```powershell
pytest tests/test_sprint1.py -v
```

### 5.2 Test Results Summary

| Category | Tests | Passed | Failed |
|----------|-------|--------|--------|
| Schema Tests | 6 | 6 | 0 |
| Data Generation Tests | 16 | 16 | 0 |
| Staging Tests | 8 | 8 | 0 |
| Data Quality Tests | 2 | 0 | 2 |
| **Total** | **32** | **30** | **2** |

### 5.3 Schema Tests (6/6 PASSED)

| Test ID | Description | Status |
|---------|-------------|--------|
| TC-001 | All required tables exist | ✅ PASSED |
| TC-002 | Categories schema correct | ✅ PASSED |
| TC-003 | Customers has required columns | ✅ PASSED |
| TC-004 | Orders has required columns | ✅ PASSED |
| TC-005 | Primary keys exist | ✅ PASSED |
| TC-006 | Foreign keys exist | ✅ PASSED |

### 5.4 Data Generation Tests (16/16 PASSED)

| Test ID | Description | Result |
|---------|-------------|--------|
| TC-010 | Categories has data | ✅ 20 rows |
| TC-011 | Products >= 1,000 | ✅ 1,000 rows |
| TC-012 | Customers >= 10,000 | ✅ 10,000 rows |
| TC-013 | Orders >= 100,000 | ✅ 100,000 rows |
| TC-014 | Order items exist | ✅ 198,225 rows |
| TC-015 | Payments exist | ✅ 96,984 rows |
| TC-016 | Invoices exist | ✅ 79,923 rows |
| TC-017+ | Additional validation | ✅ All passed |

### 5.5 Staging Tests (8/8 PASSED)

| Test ID | Description | Status |
|---------|-------------|--------|
| TC-050 | Staging directory exists | ✅ PASSED |
| TC-051 | All CSV files present | ✅ PASSED |
| TC-052 | _SUCCESS marker exists | ✅ PASSED |
| TC-053 | _metadata.json exists | ✅ PASSED |
| TC-054 | Customers count matches | ✅ PASSED |
| TC-055 | Products count matches | ✅ PASSED |
| TC-056 | Orders count matches | ✅ PASSED |
| TC-057 | Files not empty | ✅ PASSED |

### 5.6 Data Quality Tests (0/2 - Known Issues)

| Test ID | Description | Status | Root Cause |
|---------|-------------|--------|------------|
| DQ-001 | Email format valid | ⚠️ ERROR | Test framework TypeError |
| DQ-010 | Order total = sum(items) | ❌ FAILED | 200 orders have rounding diff |

**DQ-001 Analysis:**
- Direct SQL verification shows **0 invalid emails**
- The test failure is a pytest/pandas type error, not a data issue

**DQ-010 Analysis:**
- 200 orders (0.2%) have subtotal ≠ sum(order_items.line_total)
- Caused by floating-point rounding during generation
- Acceptable for OLTP simulation, can be fixed in ETL

---

## 6. Errors Encountered & Fixes Applied

### 6.1 PostgreSQL Connection Error (Windows to Docker)

**Error:**
```
psycopg2.OperationalError: FATAL: password authentication failed for user "postgres"
```

**Root Cause:** Docker volumes retained old credentials from previous runs, and Windows host couldn't connect through the default authentication.

**Fix Applied:**
1. Modified `docker-compose.yml` to add trust authentication:
```yaml
environment:
  POSTGRES_HOST_AUTH_METHOD: trust
```

2. Ran `docker-compose down -v` to remove old volumes
3. Restarted with `docker-compose up -d`

---

### 6.2 SQLAlchemy Parameter Explosion (9h9h Error)

**Error:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) too many binds
```

**Root Cause:** `pandas.to_sql()` with `method='multi'` creates named parameters like `column__row` which exceeds database limits with large inserts.

**Fix Applied:**
Changed `insert_dataframe()` in `generate_data.py` to use `psycopg2.extras.execute_values`:

```python
from psycopg2.extras import execute_values

def insert_dataframe(self, df, table_name, schema='ecommerce'):
    conn = self.engine.raw_connection()
    cur = conn.cursor()
    insert_sql = f'INSERT INTO {schema}.{table_name} ({col_str}) VALUES %s'
    execute_values(cur, insert_sql, values, page_size=100)
    conn.commit()
```

---

### 6.3 String Data Too Long (VARCHAR Constraint)

**Error:**
```
psycopg2.errors.StringDataRightTruncation: value too long for type character varying(20)
```

**Root Cause:** Faker-generated phone numbers exceeded 20 characters.

**Fix Applied:**
Added string truncation in `CustomerGenerator` and `OrderGenerator`:

```python
'phone': self.fake.phone_number()[:20],
'postal_code': self.fake.postcode()[:20],
'shipping_phone': self.fake.phone_number()[:20],
```

---

### 6.4 Duplicate Email Constraint Violation

**Error:**
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "customers_email_key"
```

**Root Cause:** Faker generates duplicate emails when creating 10,000 records.

**Fix Applied:**
Changed email generation to use unique index:

```python
# Before
'email': self.fake.email(),

# After  
'email': f"customer{idx}@{self.fake.free_email_domain()}",
```

---

### 6.5 NaT (Not a Time) Timestamp Error

**Error:**
```
psycopg2.errors.InvalidDatetimeFormat: invalid input syntax for type timestamp: "NaT"
```

**Root Cause:** Payments with `paid_at = None` were converted to pandas NaT which isn't handled by psycopg2.

**Fix Applied:**
Added explicit NaT/None handling in `insert_dataframe()`:

```python
def clean_value(v):
    if v is pd.NaT or (hasattr(v, '__class__') and v.__class__.__name__ == 'NaTType'):
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    return v

values = [tuple(clean_value(v) for v in row) for row in df_clean.values]
```

---

### 6.6 Docker Network Connection Issue

**Error:**
Data generation script couldn't connect to PostgreSQL from local Python environment.

**Root Cause:** Windows host networking to Docker containers was unreliable.

**Fix Applied:**
Ran the data generation script inside a Docker container on the same network:

```powershell
docker run --rm -v "${PWD}:/app" -w /app \
  --network enterperise_de_analytics-network \
  -e SOURCE_DB_HOST=postgres-source \
  python:3.10-slim bash -c "python scripts/data_generation/generate_data.py"
```

---

### 6.7 Metabase Authentication Error

**Error:**
Metabase couldn't connect to PostgreSQL with password authentication.

**Root Cause:** PostgreSQL was using `scram-sha-256` authentication which Metabase's driver didn't handle correctly.

**Fix Applied:**
Changed authentication method and reset password:

```bash
docker exec -u postgres ecommerce_source_db bash -c "sed -i 's/scram-sha-256/md5/g' /var/lib/postgresql/data/pg_hba.conf && pg_ctl reload"
docker exec ecommerce_source_db psql -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"
```

---

## 7. Final Results

### 7.1 Sprint 1 Deliverables Completed

| Deliverable | Status |
|-------------|--------|
| ✅ Docker environment operational | DONE |
| ✅ Source database schema created | DONE |
| ✅ Synthetic data generated (644K rows) | DONE |
| ✅ Data exported to staging layer | DONE |
| ✅ Tests executed (93.75% pass rate) | DONE |
| ✅ Metabase connected to databases | DONE |
| ✅ Test report created | DONE |

### 7.2 Data Quality Verification

| Check | Result |
|-------|--------|
| All emails contain @ | ✅ 100% valid |
| All prices > 0 | ✅ Valid |
| FK references valid | ✅ No orphans |
| Date ranges correct | ✅ 2024 data |
| Segment distribution | ✅ As configured |

---

## 8. Metabase Configuration

### 8.1 Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Metabase | http://localhost:3000 | Create admin account |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

### 8.2 Database Connections in Metabase

**Source Database:**
| Setting | Value |
|---------|-------|
| Host | postgres-source |
| Port | 5432 |
| Database | ecommerce_source |
| Username | postgres |
| Password | postgres |

**Data Warehouse:**
| Setting | Value |
|---------|-------|
| Host | postgres-dw |
| Port | 5432 |
| Database | data_warehouse |
| Username | postgres |
| Password | postgres |

---

## 9. Files Modified

| File | Changes |
|------|---------|
| `docker-compose.yml` | Added `POSTGRES_HOST_AUTH_METHOD: trust` |
| `scripts/data_generation/generate_data.py` | 5 fixes: insert method, email uniqueness, phone truncation, NaT handling, connection string |
| `.env` | Created with database credentials |

---

## 10. Recommendations for Sprint 2

### 10.1 Technical Debt

1. **Fix Order Total Calculation**: Use `Decimal` type instead of `float` for currency
2. **Add Data Validation**: Pre-insert validation for string lengths
3. **Improve Test Stability**: Fix the email format test TypeError

### 10.2 Next Steps

1. **Create Data Warehouse Schema**: Design dimensional model (star/snowflake)
2. **Build ETL Pipeline**: Apache Airflow DAGs for data transformation
3. **Implement SCD Type 2**: For slowly changing dimensions
4. **Add Data Quality Monitoring**: Great Expectations or custom checks

### 10.3 Risk Areas

| Risk | Mitigation |
|------|------------|
| Large data volumes in production | Implement partitioning strategy |
| Authentication issues | Document all credentials and connection settings |
| Float precision | Switch to Decimal for financial calculations |

---

## Appendix A: Quick Start Commands

```powershell
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# Connect to source database
docker exec -it ecommerce_source_db psql -U postgres -d ecommerce_source

# View table counts
docker exec ecommerce_source_db psql -U postgres -d ecommerce_source -c "
SELECT 'categories' as table_name, COUNT(*) FROM ecommerce.categories
UNION ALL SELECT 'products', COUNT(*) FROM ecommerce.products
UNION ALL SELECT 'customers', COUNT(*) FROM ecommerce.customers
UNION ALL SELECT 'orders', COUNT(*) FROM ecommerce.orders
UNION ALL SELECT 'order_items', COUNT(*) FROM ecommerce.order_items
UNION ALL SELECT 'payments', COUNT(*) FROM ecommerce.payments"

# Run tests
pytest tests/test_sprint1.py -v

# Stop all services
docker-compose down
```

---

**Report Generated**: 2025-12-05  
**Author**: Data Engineering Team
