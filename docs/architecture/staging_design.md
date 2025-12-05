# 🗄️ Staging Layer Design

> **Document Version**: 1.0  
> **Last Updated**: December 2024  
> **Purpose**: Thiết kế Staging Layer cho Data Lake

---

## 1. Tổng Quan Staging Layer

### 1.1 Staging là gì?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAGING LAYER CONCEPT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Staging Layer (Bronze Layer) là tầng đầu tiên trong Data Lake, có        │
│   nhiệm vụ lưu trữ dữ liệu RAW từ các nguồn mà KHÔNG transform.            │
│                                                                             │
│   ┌──────────────┐                                                          │
│   │   SOURCE     │                                                          │
│   │  SYSTEMS     │                                                          │
│   └──────┬───────┘                                                          │
│          │                                                                  │
│          │  Extract (không transform)                                       │
│          │                                                                  │
│          ▼                                                                  │
│   ┌──────────────┐     ┌──────────────────────────────────────────────┐    │
│   │   STAGING    │     │  CHARACTERISTICS:                            │    │
│   │   (BRONZE)   │     │  • 1:1 copy từ source                        │    │
│   │              │     │  • Giữ nguyên schema gốc                      │    │
│   │              │     │  • Partition theo snapshot_date               │    │
│   │              │     │  • Có thể replay từ staging                   │    │
│   │              │     │  • Single Source of Truth cho raw data       │    │
│   └──────────────┘     └──────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Tại sao cần Staging Layer?

| Lý do | Giải thích |
|-------|------------|
| **Decoupling** | Tách biệt source system khỏi processing. Source down không ảnh hưởng analytics |
| **Replayability** | Có thể re-process data nếu transform logic thay đổi |
| **Auditing** | Giữ bản gốc để audit, debug khi có vấn đề |
| **Performance** | Query staging không ảnh hưởng source OLTP |
| **History** | Track thay đổi data theo thời gian |

---

## 2. Cấu Trúc Thư Mục

### 2.1 Directory Structure

```
data/
├── raw/                         # Dữ liệu thô chưa xử lý (optional)
│   └── .gitkeep
│
├── staging/                     # 🔥 BRONZE LAYER
│   │
│   ├── snapshot_date=2024-01-01/
│   │   ├── categories.csv       # Full export
│   │   ├── products.csv
│   │   ├── customers.csv
│   │   ├── orders.csv
│   │   ├── order_items.csv
│   │   ├── payments.csv
│   │   ├── invoices.csv
│   │   ├── invoice_items.csv
│   │   ├── _metadata.json       # Pipeline metadata
│   │   └── _SUCCESS             # Completion marker
│   │
│   ├── snapshot_date=2024-01-02/
│   │   └── ... (same structure)
│   │
│   └── snapshot_date=2024-01-03/
│       └── ...
│
├── processed/                   # SILVER LAYER (Sprint 2)
│   └── .gitkeep
│
└── gold/                        # GOLD LAYER - Marts (Sprint 3)
    └── .gitkeep
```

### 2.2 Giải thích các thành phần

| Component | Purpose | Example |
|-----------|---------|---------|
| `snapshot_date=YYYY-MM-DD` | Partition key (Hive-style) | `snapshot_date=2024-01-15` |
| `{table}.csv` | Data file | `customers.csv` |
| `_metadata.json` | Pipeline run info | Row counts, duration, errors |
| `_SUCCESS` | Completion marker | Empty file đánh dấu done |

---

## 3. Naming Convention

### 3.1 File Naming

```python
# Pattern: {table_name}.{format}

# Examples:
customers.csv
products.parquet
orders.csv
```

### 3.2 Partition Naming (Hive-style)

```python
# Pattern: {partition_key}={value}/

# Examples:
snapshot_date=2024-01-15/
snapshot_date=2024-01-16/

# Nhiều partition keys (future):
year=2024/month=01/day=15/
```

### 3.3 Tại sao dùng Hive-style?

```
Hive-style partitioning (key=value/) là standard trong Big Data:

✅ Ưu điểm:
  • Tự động recognized bởi Spark, Hive, Presto, Athena
  • Dễ dàng filter theo partition (partition pruning)
  • Human-readable
  • Self-documenting

❌ Nếu KHÔNG dùng Hive-style:
  data/staging/2024-01-15/customers.csv
  -> Tool không biết "2024-01-15" là gì
  -> Phải custom code để parse
```

---

## 4. File Formats

### 4.1 CSV (Sprint 1)

```python
# Configuration khi export CSV
df.to_csv(
    file_path,
    index=False,              # Không lưu index
    encoding='utf-8',         # Encoding chuẩn
    date_format='%Y-%m-%d %H:%M:%S',  # ISO format
    na_rep='',                # NULL = empty string
    quoting=csv.QUOTE_MINIMAL  # Chỉ quote khi cần
)
```

**Pros**:
- Human-readable
- Mở được bằng Excel
- Dễ debug

**Cons**:
- Lớn (không nén)
- Không có schema
- Slow to read/write

### 4.2 Parquet (Recommended for Production)

```python
# Configuration khi export Parquet
df.to_parquet(
    file_path,
    index=False,
    engine='pyarrow',
    compression='snappy',     # Fast compression
    # compression='gzip',     # Better ratio but slower
)
```

**Pros**:
- Columnar format (query nhanh)
- Built-in compression (70-90% smaller)
- Schema embedded
- Industry standard

**Cons**:
- Không readable bằng text editor
- Cần tool để view

### 4.3 Format Selection Guide

| Use Case | Recommended | Reason |
|----------|-------------|--------|
| Development/Debug | CSV | Dễ xem, dễ fix |
| Small data (<100MB) | CSV | Không cần optimize |
| Large data (>100MB) | Parquet | Performance |
| Production | Parquet | Standard |
| Ad-hoc analysis | Parquet | Fast queries |

---

## 5. Metadata File

### 5.1 _metadata.json Structure

```json
{
  "pipeline": "source_to_staging",
  "snapshot_date": "2024-01-15",
  "run_timestamp": "2024-01-15T08:00:00+07:00",
  "duration_seconds": 125.5,
  "output_format": "csv",
  "source": {
    "host": "localhost",
    "database": "ecommerce_source",
    "schema": "ecommerce"
  },
  "tables": [
    {
      "table": "customers",
      "status": "success",
      "rows": 10000,
      "file": "customers.csv",
      "duration_seconds": 2.5
    },
    {
      "table": "orders",
      "status": "success",
      "rows": 100000,
      "file": "orders.csv",
      "duration_seconds": 45.2
    }
  ]
}
```

### 5.2 Purpose of Metadata

| Field | Use Case |
|-------|----------|
| `run_timestamp` | Audit: khi nào pipeline chạy |
| `duration_seconds` | Monitoring: pipeline có chậm không |
| `rows` | Validation: so sánh với source |
| `status` | Alerting: phát hiện failures |

---

## 6. Data Quality Expectations

### 6.1 Staging Layer Quality Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STAGING QUALITY RULES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   MUST HAVE (Blocking):                                                     │
│   ─────────────────────                                                     │
│   ✅ Row count staging = Row count source                                   │
│   ✅ No file corruption (file readable)                                     │
│   ✅ All tables exported                                                    │
│   ✅ _SUCCESS marker present                                                │
│                                                                             │
│   SHOULD HAVE (Warning):                                                    │
│   ──────────────────────                                                    │
│   ⚠️ Export time < threshold (e.g., 30 min)                                │
│   ⚠️ File size within expected range                                       │
│   ⚠️ Schema unchanged from previous run                                    │
│                                                                             │
│   NICE TO HAVE (Info):                                                      │
│   ───────────────────                                                       │
│   ℹ️ Column statistics (nulls, distinct values)                            │
│   ℹ️ Sample data validation                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Validation Queries

```python
# 1. Row count validation
source_count = db.execute("SELECT COUNT(*) FROM table")
staging_count = len(pd.read_csv("staging/table.csv"))
assert source_count == staging_count, f"Mismatch: {source_count} vs {staging_count}"

# 2. Schema validation
source_columns = set(db.execute("SELECT * FROM table LIMIT 0").columns)
staging_columns = set(pd.read_csv("staging/table.csv", nrows=0).columns)
assert source_columns == staging_columns, "Schema changed!"

# 3. Null check on required columns
staging_df = pd.read_csv("staging/customers.csv")
assert staging_df['email'].notna().all(), "Found NULL emails"
```

---

## 7. Best Practices

### 7.1 DO's ✅

```
✅ Partition by date (snapshot_date)
   → Dễ dàng query theo thời gian
   → Có thể delete old partitions

✅ Use consistent naming
   → Table name in lowercase
   → Use underscores, not spaces
   → Same name as source table

✅ Include metadata
   → Row counts
   → Timestamps
   → Schema version

✅ Use success markers
   → _SUCCESS file
   → Downstream jobs wait for this

✅ Keep raw data immutable
   → Never modify staging files
   → Create new files instead
```

### 7.2 DON'Ts ❌

```
❌ DON'T transform data in staging
   → Staging = exact copy of source
   → Transform happens in SILVER layer

❌ DON'T delete old snapshots without policy
   → Keep at least 30 days
   → Or based on storage policy

❌ DON'T use spaces in file/folder names
   → Bad: "Order Items.csv"
   → Good: "order_items.csv"

❌ DON'T mix formats in same layer
   → All CSV or all Parquet
   → Not mixed

❌ DON'T hardcode paths
   → Use environment variables
   → Or config files
```

---

## 8. Usage Examples

### 8.1 Reading Staging Data

```python
import pandas as pd
from pathlib import Path

# Read latest snapshot
staging_path = Path("data/staging")
latest_snapshot = sorted(staging_path.glob("snapshot_date=*"))[-1]

# Read customers
customers = pd.read_csv(latest_snapshot / "customers.csv")

# Read orders
orders = pd.read_csv(latest_snapshot / "orders.csv", parse_dates=['order_date'])

print(f"Loaded {len(customers)} customers and {len(orders)} orders")
```

### 8.2 Finding Specific Snapshot

```python
# Read specific date
target_date = "2024-01-15"
snapshot_path = staging_path / f"snapshot_date={target_date}"

if snapshot_path.exists():
    df = pd.read_csv(snapshot_path / "orders.csv")
else:
    print(f"No snapshot for {target_date}")
```

### 8.3 Processing All Snapshots

```python
# Process all available snapshots
for snapshot in sorted(staging_path.glob("snapshot_date=*")):
    snapshot_date = snapshot.name.split("=")[1]
    
    # Check if success
    if not (snapshot / "_SUCCESS").exists():
        print(f"Skip {snapshot_date} - incomplete")
        continue
    
    # Process
    orders = pd.read_csv(snapshot / "orders.csv")
    print(f"{snapshot_date}: {len(orders)} orders")
```

---

## 9. Future Enhancements (Sprint 2+)

### 9.1 Incremental Loading

```python
# Instead of full load every day:
# SELECT * FROM orders

# Use incremental:
# SELECT * FROM orders WHERE updated_at > :last_run

# Staging structure with incremental:
# staging/snapshot_date=2024-01-15/orders_full.parquet     # Initial
# staging/snapshot_date=2024-01-16/orders_delta.parquet   # Only changes
```

### 9.2 Schema Evolution

```python
# Track schema changes
# staging/snapshot_date=2024-01-15/
#   ├── orders.parquet
#   └── _schema/
#       └── orders_schema.json  # Column names, types
```

### 9.3 Data Compaction

```python
# Compact small files into larger ones
# Before: 100 files x 1MB = 100MB
# After:  1 file x 100MB = 100MB (faster to read)
```

---

## 10. Checklist for Sprint 1

- [ ] Staging folder structure created
- [ ] Naming convention documented and followed
- [ ] Export script working (CSV format)
- [ ] Metadata file generated
- [ ] Success marker created
- [ ] Row count validation passing
- [ ] Documentation complete

---

> 📝 **Note**: Staging layer design này phù hợp cho MVP và learning. Production system có thể cần thêm features như versioning, encryption, access control.
