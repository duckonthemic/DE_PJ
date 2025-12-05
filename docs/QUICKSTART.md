# 🚀 Quick Start Guide - Sprint 1

> **Hướng dẫn nhanh để chạy Sprint 1 trong 15 phút**

---

## 📋 Prerequisites Checklist

- [ ] Docker Desktop đã cài và đang chạy
- [ ] Python 3.10+ đã cài
- [ ] Git đã cài

---

## 🔥 Step-by-Step Guide

### Step 1: Clone và Setup (2 phút)

```powershell
# Di chuyển vào thư mục project
cd C:\Users\hoang\Downloads\Enterperise_DE

# Tạo và kích hoạt virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### Step 2: Start Docker Services (3 phút)

```powershell
# Khởi động databases
docker-compose up -d postgres-source postgres-dw

# Kiểm tra trạng thái
docker-compose ps

# Expected output:
# NAME                 STATUS
# ecommerce_source_db  running
# data_warehouse_db    running
```

### Step 3: Tạo file .env (1 phút)

```powershell
# Copy template
Copy-Item .env.example .env

# Kiểm tra nội dung (không cần sửa nếu dùng default)
Get-Content .env
```

File `.env` nên có nội dung:
```
SOURCE_DB_HOST=localhost
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=ecommerce_source
SOURCE_DB_USER=postgres
SOURCE_DB_PASSWORD=postgres
STAGING_PATH=./data/staging
```

### Step 4: Generate Synthetic Data (5 phút)

```powershell
# Chạy script sinh dữ liệu
python scripts/data_generation/generate_data.py

# Expected output:
# ✅ Connected to database: ecommerce_source
# 📦 Step 1: Generating Categories...
# ✅ Inserted 20 rows into ecommerce.categories
# 📦 Step 2: Generating Products...
# ✅ Inserted 1000 rows into ecommerce.products
# ...
# ✅ Data Generation Complete!
```

### Step 5: Export to Staging (3 phút)

```powershell
# Export tất cả tables sang staging
python src/ingestion/export_to_staging.py

# Expected output:
# ✅ Connected to: ecommerce_source
# 📦 Exporting: categories
# ✅ Written: data\staging\snapshot_date=2024-12-04\categories.csv
# ...
# ✅ Ingest Pipeline Completed
```

### Step 6: Verify Results (1 phút)

```powershell
# Kiểm tra files đã tạo
Get-ChildItem -Path "data\staging" -Recurse

# Expected:
# snapshot_date=2024-12-04/
#     categories.csv
#     products.csv
#     customers.csv
#     orders.csv
#     order_items.csv
#     payments.csv
#     invoices.csv
#     invoice_items.csv
#     _metadata.json
#     _SUCCESS
```

---

## ✅ Success Criteria

Sau khi hoàn thành, bạn nên có:

| Item | Expected |
|------|----------|
| PostgreSQL running | `docker ps` shows container |
| Tables created | 8 tables in ecommerce schema |
| Data generated | ~10k customers, ~100k orders |
| Staging files | CSV files in data/staging/ |
| Metadata | _metadata.json with row counts |

---

## 🔧 Troubleshooting

### Docker không start
```powershell
# Restart Docker Desktop
# Hoặc chạy lại:
docker-compose down
docker-compose up -d postgres-source
```

### Connection refused
```powershell
# Kiểm tra container có chạy không
docker-compose ps

# Kiểm tra logs
docker-compose logs postgres-source
```

### Module not found
```powershell
# Đảm bảo đã activate venv
.\venv\Scripts\Activate

# Cài lại dependencies
pip install -r requirements.txt
```

### Permission denied
```powershell
# Chạy PowerShell as Administrator
# Hoặc thay đổi execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📊 Quick SQL Queries

Sau khi có data, thử các query sau trong pgAdmin hoặc DBeaver:

```sql
-- Kết nối: localhost:5432, database: ecommerce_source

-- Đếm số records
SELECT 'customers' as tbl, COUNT(*) FROM ecommerce.customers
UNION ALL SELECT 'orders', COUNT(*) FROM ecommerce.orders
UNION ALL SELECT 'payments', COUNT(*) FROM ecommerce.payments;

-- Doanh thu theo tháng
SELECT 
    DATE_TRUNC('month', order_date) as month,
    COUNT(*) as orders,
    SUM(total_amount) as revenue
FROM ecommerce.orders
WHERE status = 'Completed'
GROUP BY 1
ORDER BY 1;

-- Top 10 khách hàng
SELECT 
    c.customer_code,
    c.email,
    COUNT(o.id) as order_count,
    SUM(o.total_amount) as total_spent
FROM ecommerce.customers c
JOIN ecommerce.orders o ON c.id = o.customer_id
GROUP BY c.id
ORDER BY total_spent DESC
LIMIT 10;
```

---

## 📚 Next Steps

1. **Đọc documentation**: `docs/sprint1_detailed_guide.md`
2. **Hiểu schema**: `docs/data_dictionary/source_schema.md`
3. **Review code**: Đọc comments trong các Python files
4. **Thử sửa đổi**: Thay đổi số lượng records trong config

---

## 🆘 Need Help?

1. Đọc error message kỹ
2. Search Google với error message
3. Check Docker logs: `docker-compose logs -f`
4. Hỏi mentor với context đầy đủ

---

> 💡 **Tip**: Bookmark trang này và quay lại khi cần!
