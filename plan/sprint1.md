<!-- filename: sprint_1.md -->

# sprint_1 – Thiết lập nguồn dữ liệu & tầng staging

Sprint 1 tập trung vào 3 việc chính:

1. Thiết kế **schema nguồn (OLTP)** cho hệ thống e-commerce mô phỏng.  
2. Sinh **dữ liệu giả lập** đủ phong phú.  
3. Thiết lập **tầng staging/bronze** và pipeline ingest dữ liệu từ nguồn vào staging.

Mỗi mục dưới đây đều có **Input → Output → Các bước** + **nguồn tài liệu để tự học**.

---

## 0. Phạm vi & kết quả Sprint 1

### 0.1. Input (đầu vào tổng thể)

- Máy cá nhân (Windows/Linux/macOS) có thể chạy:
  - Docker (khuyến nghị) hoặc một DB như PostgreSQL/MySQL.
  - Python 3.10+.
- GitHub repo trống cho dự án (hoặc repo đã có README khung).
- Yêu cầu nghiệp vụ mức high-level:  
  > Bán hàng e-commerce với **customers, products, orders, order_items, payments, accounting/ERP**.

### 0.2. Output (kết quả tổng thể)

- **Schema nguồn (ERD + DDL)** cho hệ thống e-commerce.
- **Database nguồn** có dữ liệu giả lập (6–12 tháng).
- **Data Lake/staging layer**:
  - Cấu trúc thư mục rõ ràng (hoặc bucket trên MinIO/S3).
  - Các file CSV/Parquet dump từ DB nguồn (per table, per snapshot/ngày).
- **Tài liệu**:
  - `docs/business_requirements.md` – mô tả use case & câu hỏi phân tích.
  - `docs/source_schema.md` – mô tả bảng & quan hệ.
  - `docs/staging_design.md` – mô tả staging layer & naming convention.

---

## 1. Chuẩn bị môi trường

### 1.1. Input

- Hệ điều hành đã cài Docker (hoặc sẵn PostgreSQL/MySQL).
- Quyết định tech-stack:
  - **DB nguồn**: PostgreSQL (khuyến nghị cho analytics).
  - **Ngôn ngữ**: Python.
  - **Storage staging**: 
    - Option 1: thư mục local (dễ nhất).
    - Option 2: MinIO/S3-compatible (gần với production hơn).

### 1.2. Output

- Repo có cấu trúc tối thiểu:

  ```text
  enterprise-customer-revenue-analytics/
  ├─ src/
  │  ├─ data_generation/
  │  ├─ ingestion/
  ├─ data/
  │  ├─ source/          # backup CSV từ DB (tùy chọn)
  │  └─ staging/         # staging layer
  ├─ docs/
  ├─ .env.example
  └─ README.md
  ```

- DB nguồn chạy được (Postgres container hoặc service local).
- Virtualenv Python với các thư viện cơ bản:
  - `psycopg2-binary` hoặc `sqlalchemy`
  - `pandas`
  - `faker`

### 1.3. Các bước thực hiện

**Bước 1 – Tạo repo & cấu trúc thư mục**

```bash
# Tạo thư mục dự án
mkdir enterprise-analytics
cd enterprise-analytics

# Khởi tạo Git
git init

# Tạo cấu trúc thư mục
mkdir -p src/data_generation src/ingestion src/sql
mkdir -p data/source data/staging data/processed
mkdir -p docs tests notebooks

# Tạo file .gitkeep để Git track thư mục rỗng
touch data/source/.gitkeep data/staging/.gitkeep

# Tạo README cơ bản
echo "# Enterprise Customer & Revenue Analytics Platform" > README.md
```

**Bước 2 – Chuẩn bị Python environment**

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt (Windows PowerShell)
.\venv\Scripts\activate

# Kích hoạt (Linux/macOS)
source venv/bin/activate

# Cài đặt thư viện cần thiết
pip install pandas sqlalchemy psycopg2-binary faker python-dotenv pyarrow

# Lưu dependencies
pip freeze > requirements.txt
```

**Tạo file `.env.example`** (template cho biến môi trường):

```bash
# .env.example - Copy thành .env và điền giá trị thực
# Database Source
SOURCE_DB_HOST=localhost
SOURCE_DB_PORT=5432
SOURCE_DB_NAME=ecommerce_source
SOURCE_DB_USER=postgres
SOURCE_DB_PASSWORD=your_password_here

# Staging
STAGING_PATH=./data/staging
```

**Bước 3 – Chuẩn bị database nguồn**

**Option 1: Dùng Docker (khuyến nghị)**

```bash
# Chạy PostgreSQL container
docker run -d \
  --name postgres_source \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ecommerce_source \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# Kiểm tra container đã chạy
docker ps

# Kết nối thử (từ terminal)
docker exec -it postgres_source psql -U postgres -d ecommerce_source
```

**Option 2: Dùng docker-compose (đã có sẵn trong project)**

```bash
# Từ thư mục gốc dự án
docker-compose up -d postgres-source

# Xem logs
docker-compose logs -f postgres-source
```

**Kiểm tra kết nối bằng Python:**

```python
# test_connection.py - Chạy để kiểm tra kết nối DB
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Load biến môi trường từ .env
load_dotenv()

# Tạo connection string
db_url = f"postgresql://{os.getenv('SOURCE_DB_USER')}:{os.getenv('SOURCE_DB_PASSWORD')}@{os.getenv('SOURCE_DB_HOST')}:{os.getenv('SOURCE_DB_PORT')}/{os.getenv('SOURCE_DB_NAME')}"

# Thử kết nối
try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print("✅ Kết nối thành công!")
        print(f"PostgreSQL version: {result.fetchone()[0]}")
except Exception as e:
    print(f"❌ Lỗi kết nối: {e}")
```

### 1.4. Tài liệu tự học

- **Data Warehouse & các layer (staging, core, mart):**
  - [How to Build and Implement Data Warehouse Layers – Hightouch](https://hightouch.com/blog/data-warehouse-layers)
  - [Data Warehouse Design Best Practices – Monte Carlo Data](https://www.montecarlodata.com/blog-data-warehouse-design/)
- **MinIO / Object Storage cơ bản (tuỳ chọn nếu dùng S3-compatible):**
  - [MinIO Quickstart Guide](https://charts.min.io/)
  - [minio/minio Docker Image – Docker Hub](https://hub.docker.com/r/minio/minio)
  - [Introduction to MinIO – Baeldung](https://www.baeldung.com/minio)

---

## 2. Thiết kế schema nguồn (OLTP e-commerce)

### 2.1. Input

- Yêu cầu nghiệp vụ:
  - Một khách hàng có thể đặt nhiều đơn hàng.
  - Một đơn hàng có nhiều dòng hàng (order items).
  - Mỗi đơn hàng được thanh toán qua cổng thanh toán (payment).
  - Hệ thống kế toán/ERP lưu invoice hoặc bút toán doanh thu.

### 2.2. Output

- **ERD** (hình hoặc file từ tool) cho các bảng chính:
  - `customers`, `products`, `orders`, `order_items`, `payments`, `invoices`/`gl_entries`.
- **Script DDL** để tạo bảng trên PostgreSQL, lưu ở `src/sql/01_create_source_schema.sql`.
- Tài liệu `docs/source_schema.md` mô tả từng bảng, cột, khóa, mô tả nghiệp vụ.

### 2.3. Các bước thực hiện

**Bước 1 – Xác định entity & quan hệ**

- Liệt kê entity chính theo mô hình e-commerce chuẩn:
  - **Customer**, **Product**, **Order**, **Order Item**, **Payment**, (tùy chọn) **Shipment**, **Invoice/GL**.  
- Xác định quan hệ:
  - 1 Customer → N Orders.
  - 1 Order → N Order Items.
  - 1 Order Item ↔ 1 Product.
  - 1 Order ↔ 1..N Payments (tùy business).

**Bước 2 – Vẽ ERD**

- Dùng tool miễn phí: Draw.io, dbdiagram.io, Lucidchart, Vertabelo (trial), Creately, Moqups, v.v.
- Vẽ đầy đủ:
  - Tên bảng.
  - Các cột chính (id, code, name, amount, date, status, …).
  - Primary key, foreign key.

**Bước 3 – Chuẩn hóa & rà lại**

- Đảm bảo không có cột lặp hoặc dữ liệu “dính” (ví dụ: không lưu cả họ tên + địa chỉ + email trong 1 cột).
- Đảm bảo mỗi bảng có:
  - PK rõ ràng (id tự tăng hoặc UUID).
  - Các cột `created_at`, `updated_at` (giúp incremental load sau này).
- Kiểm tra kiểu dữ liệu (numeric, date, text) hợp lý.

**Bước 4 – Viết DDL & tạo schema**

- Từ ERD → viết câu lệnh `CREATE TABLE` cho từng bảng.
- Lưu vào `src/sql/01_create_source_schema.sql`.
- Chạy script lên PostgreSQL, tạo schema `public` (hoặc `source`).

**Bước 5 – QC/QA kiểm tra schema**

- Kiểm tra:
  - Tồn tại PK cho mọi bảng.
  - FK trỏ đúng bảng cha.
  - Các cột bắt buộc (NOT NULL) đã set hợp lý.
- Ghi lại test case & kết quả vào `docs/testcases_sprint1.md`.

### 2.4. Tài liệu tự học

- **Thiết kế ERD cho e-commerce:**
  - [How to Design ER Diagrams for E-commerce Website – GeeksforGeeks](https://www.geeksforgeeks.org/dbms/how-to-design-er-diagrams-for-e-commerce-website/)
  - [ER Diagram Sample for Ecommerce Project – dev.to](https://dev.to/fpaghar/er-diagram-sample-for-ecommerce-project-1o2h)
  - [E-commerce Database ER Diagram – Creately Template](https://creately.com/diagram/example/he7cxejx1/e-commerce-database-er-diagram)
  - [Ecommerce Database Diagram Template – Moqups](https://moqups.com/templates/mapping-and-diagramming/erd/ecommerce-database-diagram/)
- **Ví dụ database e-commerce hoàn chỉnh:**
  - [Ecommerce-Database-Design-and-Analysis – GitHub](https://github.com/pranitjaiswal/Ecommerce-Database-Design-and-Analysis)

---

## 3. Sinh dữ liệu giả (synthetic data)

### 3.1. Input

- Database nguồn đã có schema nhưng chưa có dữ liệu.
- Yêu cầu về quy mô:
  - ~5k–20k khách hàng.
  - ~1k–5k sản phẩm.
  - ~50k–200k đơn hàng trong 6–12 tháng.
  - Số payment & invoice tương ứng.

### 3.2. Output

- Các bảng nguồn trong DB được populate dữ liệu.
- (Tuỳ chọn) file CSV backup dữ liệu tại `data/source/*.csv`.
- Script sinh dữ liệu nằm ở `src/data_generation/`:
  - `generate_customers.py`
  - `generate_products.py`
  - `generate_orders.py`
  - v.v.

### 3.3. Các bước thực hiện

**Bước 1 – Quyết định kịch bản & quy mô**

- Quyết định khoảng thời gian dữ liệu: ví dụ từ `2024-01-01` đến `2024-12-31`.
- Quyết định phân bố:
  - Mùa cao điểm (Tết, Black Friday…) có nhiều đơn.
  - Một số sản phẩm bán chạy hơn (Zipf distribution đơn giản).
- Ghi các quyết định này vào `docs/data_generation_design.md`.

**Bước 2 – Cài & làm quen Faker**

- Cài Faker (nếu chưa): `pip install Faker`.  
- Tạo instance `Faker()` để generate:
  - Tên, email, địa chỉ, số điện thoại cho customers.
  - Tên sản phẩm, mã SKU, mô tả.
  - Ngày tháng order, số tiền, trạng thái.

**Bước 3 – Viết script cho từng bảng**

- `generate_customers.py`:
  - Sinh các thông tin: name, email, phone, address, created_at, segment sơ bộ, v.v.
  - Insert trực tiếp vào DB hoặc ghi CSV rồi dùng `COPY` để import.
- `generate_products.py`:
  - Định nghĩa category, price range, status.
- `generate_orders.py`:
  - Chọn random customer, product; generate order_date; tính total_amount.
  - Sinh nhiều **order_items** cho mỗi order.
- `generate_payments.py`:
  - Tạo payment tương ứng cho phần lớn orders.
  - Một số order cho case test: chưa thanh toán / thanh toán thiếu / thanh toán thừa (phục vụ reconciliation sau này).
- (Tuỳ chọn) `generate_invoices.py`/`gl_entries`:
  - Mô phỏng dữ liệu kế toán (có thể lệch nhẹ với order/payment).

**Bước 4 – QC/QA kiểm tra dữ liệu giả**

- Kiểm tra row count vs kỳ vọng (ví dụ: 10k customers, 100k order).
- Kiểm tra phân phối đơn hàng theo thời gian (không phải tất cả chỉ trong 1 ngày).
- Kiểm tra:
  - Không có order không có customer.
  - Không có order_item trỏ tới product không tồn tại.
- Ghi lại test case và defect (nếu có) vào `docs/testcases_sprint1.md`.

### 3.4. Tài liệu tự học

- **Faker Python:**
  - [Faker Documentation – Read the Docs](https://faker.readthedocs.io/)
  - [Faker – PyPI](https://pypi.org/project/Faker/)
  - [Python Faker Library – GeeksforGeeks](https://www.geeksforgeeks.org/python/python-faker-library/)
  - [Using Faker to Generate Data in Python – python-refs](https://python-refs.readthedocs.io/en/latest/recipes/using-faker-to-generate-data-python.html)

---

## 4. Thiết kế Data Lake / Staging Layer

### 4.1. Input

- DB nguồn đã có dữ liệu.
- Quyết định nơi lưu staging:
  - Thư mục local `data/staging`.
  - Hoặc bucket trên MinIO (`enterprise-staging/…`).

### 4.2. Output

- Thư mục/bucket staging với cấu trúc rõ ràng, ví dụ:

  ```text
  data/
    staging/
      snapshot_date=2024-10-01/
        customers.csv
        products.csv
        orders.csv
        order_items.csv
        payments.csv
      snapshot_date=2024-10-02/
        ...
  ```

- Tài liệu `docs/staging_design.md` mô tả:
  - Mục đích staging.
  - Cấu trúc thư mục.
  - Naming convention.

### 4.3. Các bước thực hiện

**Bước 1 – Hiểu khái niệm staging**

- Staging là vùng lưu **dữ liệu raw hoặc gần-raw** trước khi transform vào DWH:
  - Giúp tách biệt xử lý khỏi hệ thống nguồn.
  - Hỗ trợ recover dễ hơn.
  - Là nơi lý tưởng để đặt data quality rule.

**Bước 2 – Thiết kế cấu trúc thư mục/bucket**

- Chọn kiểu partition:
  - Theo **snapshot_date** (ngày chạy pipeline).
  - Hoặc theo **business_date** (ngày data phát sinh).
- Định nghĩa quy tắc đặt tên file:
  - `table_name.format` (vd: `orders.parquet`).
  - Nếu incremental: thêm suffix `part_001`, `part_002` nếu cần.

**Bước 3 – Nếu dùng MinIO (tùy chọn)**

- Cài & chạy MinIO local (Docker hoặc binary).
- Tạo bucket `enterprise-staging`.
- Quy ước path tương tự như thư mục local (chỉ khác là trên object storage).

**Bước 4 – QC/QA review thiết kế staging**

- Kiểm tra:
  - Cấu trúc có dễ hiểu với người mới?  
  - Có đảm bảo **không trực tiếp transform phá dữ liệu staging** (raw luôn giữ nguyên)?
- Góp ý về naming convention, bảo mật (phân quyền đọc/ghi).

### 4.4. Tài liệu tự học

- **Khái niệm & best practice Data Staging:**
  - [Data Staging – Actian](https://www.actian.com/data-staging/)
  - [Complete Guide to Data Staging – Zuar](https://www.zuar.com/blog/complete-guide-to-data-staging/)
  - [What is a Data Staging Area? – HevoData](https://hevodata.com/learn/data-staging-area/)
  - [Data Staging Area in Data Warehouse – GeeksforGeeks](https://www.geeksforgeeks.org/software-testing/data-staging-area-in-data-warehouse/)
- **Staging layer & Data Warehouse layers:**
  - [How to Build and Implement Data Warehouse Layers – Hightouch](https://hightouch.com/blog/data-warehouse-layers)
  - [Top 10 Best Practices in Data Warehousing – Streamkap](https://streamkap.com/resources-and-guides/best-practices-in-data-warehousing)
  - [Enterprise Data Warehouse Guide – Polestar](https://www.polestarllp.com/blog/guide-enterprise-data-warehouse-edw)
- **MinIO:**
  - [MinIO Quickstart Guide](https://charts.min.io/)
  - [minio/minio – Docker Hub](https://hub.docker.com/r/minio/minio)
  - [MinIO Client Quickstart – mc](https://minio.github.io/mc/)

---

## 5. Xây pipeline ingest từ DB nguồn vào staging

### 5.1. Input

- DB nguồn (Postgres) chứa dữ liệu giả.
- Staging storage (thư mục hoặc MinIO).
- Thông tin kết nối (host, port, db, user, password) lưu trong `.env`.

### 5.2. Output

- Script ingest, ví dụ:
  - `src/ingestion/export_to_staging.py`
- Một lần chạy script sẽ:
  - Kết nối DB.
  - Đọc dữ liệu từng bảng.
  - Ghi CSV/Parquet vào đúng thư mục/bucket staging (theo `snapshot_date`).
- Log đơn giản (in ra console hoặc file) về:
  - Bảng nào đã export, row count, thời gian.

### 5.3. Các bước thực hiện

**Bước 1 – Liệt kê bảng & chiến lược load**

- Danh sách bảng cần export: `customers`, `products`, `orders`, `order_items`, `payments`, `invoices`.
- Sprint 1: dùng **full load** cả bảng mỗi lần (incremental sẽ xử lý sprint sau).
- Ghi chiến lược này vào `docs/ingestion_design.md`.

**Bước 2 – Viết script export**

- Logic cơ bản:
  1. Đọc biến môi trường từ `.env` (connection string).
  2. Tạo `snapshot_date = today()` (ví dụ `2024-10-01`).
  3. Với từng bảng:
     - Thực thi `SELECT * FROM table`.
     - Load vào pandas DataFrame.
     - Ghi ra `data/staging/snapshot_date=YYYY-MM-DD/table.csv` (hoặc `.parquet`).
  4. Log row count & path file.

- Nếu dùng MinIO:
  - Sau khi ghi file tạm local → upload lên bucket (sử dụng Python client như `minio` hoặc `boto3`).

**Bước 3 – QC/QA kiểm thử pipeline ingest**

- So sánh **row count**:
  - `SELECT COUNT(*) FROM table` (DB nguồn) vs số dòng trong file staging.
- Lấy sample vài dòng:
  - So sánh giá trị giữa DB & file (ID, amount, date,…).
- Kiểm tra:
  - File được đặt đúng `snapshot_date`.
  - Không có bảng quan trọng nào bị bỏ quên.
- Ghi test case & kết quả vào `docs/testcases_sprint1.md`.

### 5.4. Tài liệu tự học

- **Staging & ingest trong pipeline ETL/ELT:**
  - [Data Staging – Actian](https://www.actian.com/data-staging/)
  - [Complete Guide to Data Staging – Zuar](https://www.zuar.com/blog/complete-guide-to-data-staging/)
  - [What is a Data Staging Area? – HevoData](https://hevodata.com/learn/data-staging-area/)
- **dbt staging models (ý tưởng đặt tên & tách layer, dù bạn không dùng dbt):**
  - [Staging: Preparing our atomic building blocks – dbt Docs](https://docs.getdbt.com/best-practices/how-we-structure/2-staging)
  - [dbt Staging Models – HevoData](https://hevodata.com/data-transformation/dbt-how-to-setup-staging/)
  - [How to Build Effective dbt Staging Models – pmunhoz blog](https://blog.pmunhoz.com/dbt/dbt-staging-models-best-practices)
- **MinIO & client:**
  - [minio/minio – Docker Hub](https://hub.docker.com/r/minio/minio)
  - [MinIO Client Quickstart – mc](https://minio.github.io/mc/)

---

## 6. Thiết kế Test Strategy & Test Case cho Sprint 1

*(Phần này chủ yếu cho QC/QA nhưng DE cũng nên đọc để hiểu cách bị “soi” 😄)*

### 6.1. Input

- Schema nguồn đã thiết kế & triển khai.
- Script sinh dữ liệu giả.
- Script ingest vào staging.
- Yêu cầu nghiệp vụ high-level.

### 6.2. Output

- File `docs/test_strategy_sprint1.md`:
  - Phạm vi test (schema, dữ liệu giả, ingest & staging).
  - Loại test sử dụng (schema test, data sanity check, row count & mapping).
- File `docs/testcases_sprint1.md`:
  - Danh sách test case chi tiết.
  - Kết quả thực tế & defect log.

### 6.3. Các bước thực hiện

**Bước 1 – Xác định phạm vi test**

- Gồm 3 nhóm:
  1. **Schema Testing**: PK, FK, NOT NULL, kiểu dữ liệu.
  2. **Data Testing (synthetic data)**: phân phối ngày, giá trị amount, tỉ lệ null, logic đơn giản (order phải có customer).
  3. **Ingestion & Staging Testing**: row count, integrity khi export, đúng cấu trúc staging.

**Bước 2 – Viết Test Strategy**

- Xác định:
  - Môi trường test (local).
  - Tool: psql/pgAdmin, Python (pandas), có thể dùng notebook để chạy query test.
  - Tiêu chí pass/fail (ví dụ: row count staging = row count source; không có null cho PK/FK).

**Bước 3 – Viết test case cụ thể**

- Ví dụ:
  - **TC-001**: `customers` phải có PK unique, không null.
  - **TC-010**: mọi `order_items.order_id` phải tồn tại trong `orders.id`.
  - **TC-020**: row count `orders` trong DB và file staging khớp nhau.
  - **TC-030**: ngày `order_date` nằm trong khoảng đã thiết kế (không vượt quá `max(order_date)` nhập).
- Mỗi test case ghi:
  - ID, mục tiêu, pre-condition, step, expected result, actual result.

**Bước 4 – Thực thi test & log kết quả**

- Chạy các query/schema check.
- Ghi lại lỗi (ví dụ: script sinh data tạo 1 vài order không có payment → mark là “known case” hay bug?).

### 6.4. Tài liệu tự học

- **Data staging & data quality ở staging layer:**
  - [Data Staging – Actian](https://www.actian.com/data-staging/)
  - [Complete Guide to Data Staging – Zuar](https://www.zuar.com/blog/complete-guide-to-data-staging/)
  - [Data Staging Area in Data Warehouse – GeeksforGeeks](https://www.geeksforgeeks.org/software-testing/data-staging-area-in-data-warehouse/)
  - [Enterprise Data Warehouse Guide – Polestar (mục data quality ở staging)](https://www.polestarllp.com/blog/guide-enterprise-data-warehouse-edw)
- **Best practices Data Warehouse & monitoring:**
  - [Top 10 Best Practices in Data Warehousing – Streamkap](https://streamkap.com/resources-and-guides/best-practices-in-data-warehousing)

---

## 7. Checklist hoàn thành Sprint 1

### 7.1. Data Engineer

- [ ] Repo, virtualenv, DB nguồn đã sẵn sàng.  
- [ ] `docs/business_requirements.md` hoàn thành.  
- [ ] ERD & script `01_create_source_schema.sql` chạy OK.  
- [ ] Dữ liệu giả lập đã populate đủ số lượng & hợp lý.  
- [ ] Thiết kế staging layer (`docs/staging_design.md`).  
- [ ] Script ingest `export_to_staging.py` chạy được, tạo file staging đúng cấu trúc.  

### 7.2. QC/QA Engineer

- [ ] `docs/test_strategy_sprint1.md` mô tả rõ phạm vi test.  
- [ ] `docs/testcases_sprint1.md` có test case cho schema, synthetic data & ingest.  
- [ ] Đã chạy test schema & ingest, có log kết quả.  
- [ ] Các defect quan trọng đã được DE sửa hoặc ghi rõ “known issue” + lý do.  

---

## 8. Danh sách tài liệu gợi ý (tổng hợp)

Bạn có thể chia thời gian: mỗi task làm 30–60 phút, xen kẽ đọc 1–2 bài sau để hiểu sâu hơn:

### 8.1. Thiết kế ERD & schema e-commerce

- [How to Design ER Diagrams for E-commerce Website – GeeksforGeeks](https://www.geeksforgeeks.org/dbms/how-to-design-er-diagrams-for-e-commerce-website/)
- [ER Diagram Sample for Ecommerce Project – dev.to](https://dev.to/fpaghar/er-diagram-sample-for-ecommerce-project-1o2h)
- [E-commerce Database ER Diagram – Creately](https://creately.com/diagram/example/he7cxejx1/e-commerce-database-er-diagram)
- [Ecommerce Database Diagram Template – Moqups](https://moqups.com/templates/mapping-and-diagramming/erd/ecommerce-database-diagram/)
- [Ecommerce-Database-Design-and-Analysis – GitHub](https://github.com/pranitjaiswal/Ecommerce-Database-Design-and-Analysis)

### 8.2. Khái niệm Data Warehouse, Staging Layer & Data Quality

- [Data Staging – Actian](https://www.actian.com/data-staging/)
- [Complete Guide to Data Staging – Zuar](https://www.zuar.com/blog/complete-guide-to-data-staging/)
- [What is a Data Staging Area? – HevoData](https://hevodata.com/learn/data-staging-area/)
- [Data Staging Area in Data Warehouse – GeeksforGeeks](https://www.geeksforgeeks.org/software-testing/data-staging-area-in-data-warehouse/)
- [How to Build and Implement Data Warehouse Layers – Hightouch](https://hightouch.com/blog/data-warehouse-layers)
- [Data Warehouse Design Best Practices – Monte Carlo Data](https://www.montecarlodata.com/blog-data-warehouse-design/)
- [Top 10 Best Practices in Data Warehousing – Streamkap](https://streamkap.com/resources-and-guides/best-practices-in-data-warehousing)
- [Enterprise Data Warehouse Guide – Polestar (mục staging & data quality)](https://www.polestarllp.com/blog/guide-enterprise-data-warehouse-edw)

### 8.3. dbt Staging Models (tham khảo concept)

- [Staging: Preparing our atomic building blocks – dbt Docs](https://docs.getdbt.com/best-practices/how-we-structure/2-staging)
- [Staging Models Best Practices and Limiting View Runs – dbt Blog](https://www.getdbt.com/blog/staging-models-best-practices-and-limiting-view-runs)
- [dbt Staging Models – HevoData](https://hevodata.com/data-transformation/dbt-how-to-setup-staging/)
- [How to Build Effective dbt Staging Models – pmunhoz blog](https://blog.pmunhoz.com/dbt/dbt-staging-models-best-practices)
- [Best Practices for Managing Staging Models – dbt Discourse](https://discourse.getdbt.com/t/best-practices-for-managing-staging-models-in-large-scale-dbt-projects/19661)

### 8.4. Faker & sinh dữ liệu giả

- [Faker Documentation – Read the Docs](https://faker.readthedocs.io/)
- [Faker – PyPI](https://pypi.org/project/Faker/)
- [Python Faker Library – GeeksforGeeks](https://www.geeksforgeeks.org/python/python-faker-library/)
- [Using Faker to Generate Data in Python – python-refs](https://python-refs.readthedocs.io/en/latest/recipes/using-faker-to-generate-data-python.html)

### 8.5. MinIO & Object Storage

- [MinIO Quickstart Guide](https://charts.min.io/)
- [minio/minio – Docker Hub](https://hub.docker.com/r/minio/minio)
- [Introduction to MinIO – Baeldung](https://www.baeldung.com/minio)
- [MinIO Client Quickstart – mc](https://minio.github.io/mc/)
