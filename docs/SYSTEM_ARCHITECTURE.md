# Tài Liệu Kiến Trúc & Hướng Dẫn Kỹ Thuật Hệ Thống

**Enterprise Customer & Revenue Analytics Platform**

---

## 1. Tổng Quan Hệ Thống

Dự án là một nền tảng dữ liệu toàn diện (End-to-End Data Platform) mô phỏng quy trình xử lý dữ liệu thực tế tại các công ty E-commerce/Retail. Hệ thống giúp chuyển đổi dữ liệu thô từ giao dịch hàng ngày thành thông tin chi tiết về khách hàng và doanh thu.

### Kiến Trúc High-Level

```mermaid
graph LR
    subgraph Source["Nguồn Dữ Liệu (OLTP)"]
        DB[(PostgreSQL Source)]
        MinIO[(MinIO S3)]
    end
    
    subgraph DW["Data Warehouse (PostgreSQL)"]
        Staging[SCHEMA: Staging]
        Core[SCHEMA: DW (Star Schema)]
        Mart[SCHEMA: Mart (Analytics)]
        Recon[SCHEMA: Reconcile]
    end
    
    subgraph BI["Hiển Thị"]
        Metabase[Metabase Dashboard]
    end
    
    DB --> |ETL Python| Core
    Core --> |Transform| Mart
    Core --> |Reconcile Logic| Recon
    Mart --> Metabase
    Recon --> Metabase
```

---

## 2. Nguồn Dữ Liệu (Source System)

Hệ thống nguồn đóng vai trò là cơ sở dữ liệu giao dịch (OLTP), lưu trữ trạng thái hiện tại của ứng dụng bán hàng.

**Database:** `ecommerce_source` (PostgreSQL)  
**Schema:** `ecommerce`

Các bảng chính:
- **`customers`** (10,000 dòng): Thông tin khách hàng, địa chỉ, phân khúc.
- **`products`** (1,000 dòng): Danh mục sản phẩm, giá bán, giá vốn.
- **`orders`** (100,000 dòng): Đơn đặt hàng (Header), trạng thái đặt hàng.
- **`order_items`**: Chi tiết từng dòng sản phẩm trong đơn hàng.
- **`payments`**: Giao dịch thanh toán (tỉ lệ 97% có payment, mô phỏng lỗi thực tế).

---

## 3. Data Warehouse Core (Star Schema)

Tầng trung tâm của hệ thống, nơi dữ liệu được làm sạch, chuẩn hóa và tổ chức lại để phục vụ phân tích. Sử dụng mô hình **Star Schema**.

**Database:** `data_warehouse`  
**Schema:** `dw`

### Dimension Tables (Các góc nhìn phân tích)
1.  **`dim_date`**: Dimension thời gian (2020-2030), hỗ trợ phân tích theo ngày, tuần, tháng, quý, năm, ngày lễ/tết.
2.  **`dim_customer`**: Dimension khách hàng. Hỗ trợ **SCD Type 2** (Slowly Changing Dimension) để theo dõi lịch sử thay đổi thông tin khách hàng (ví dụ: chuyển nhà, đổi email).
3.  **`dim_product`**: Dimension sản phẩm, đã được **denormalized** (gộp) với Category để truy vấn nhanh hơn.
4.  **`dim_channel`**: Kênh bán hàng (Website, App, Store, Marketplace).
5.  **`dim_payment_method`**: Phương thức thanh toán (COD, Credit Card, E-Wallet).

### Fact Tables (Dữ liệu sự kiện/giao dịch)
1.  **`fact_sales`** (184,332 dòng):
    - **Grain**: Một dòng tương ứng với một sản phẩm trong đơn hàng (Order Line Item).
    - **Metrics**: Quantity, Line Total, Discount Amount, Profit, Cost.
    - **Kết nối**: Foreign Keys tới tất cả các dimension trên.
2.  **`fact_payment`** (96,984 dòng):
    - **Grain**: Một giao dịch thanh toán.
    - **Mục đích**: Theo dõi dòng tiền thực tế, trạng thái thanh toán.

---

## 4. Customer 360 & Analytics Mart

Tầng ứng dụng dữ liệu, nơi dữ liệu được tổng hợp sẵn sàng cho báo cáo và Dashboard.

**Schema:** `mart`

### Bảng Chính: `mart_customer_360`
Đây là bảng **One Big Table (OBT)** giúp Marketing & Sales có cái nhìn toàn diện về khách hàng.

**Các nhóm chỉ số:**
1.  **RFM Score**:
    - **Recency (R)**: Khách mua gần nhất khi nào? (Điểm 1-5)
    - **Frequency (F)**: Khách mua thường xuyên không? (Điểm 1-5)
    - **Monetary (M)**: Khách chi bao nhiêu tiền? (Điểm 1-5)
2.  **Phân Khúc (Segment)**:
    - **Champions**: Khách VIP (R=5, F=5, M=5).
    - **Loyal**: Khách trung thành.
    - **At Risk**: Khách từng mua nhiều nhưng đã lâu không quay lại.
    - **Lost**: Khách đã rời bỏ.
3.  **Hành vi & Sở thích**:
    - Kênh mua sắm ưa thích (Preferred Channel).
    - Phương thức thanh toán sở trường.
    - LTV (Lifetime Value) ước tính.

---

## 5. Đối Soát Dữ Liệu (Reconciliation)

Module quan trọng để đảm bảo tính chính xác về tài chính.

**Schema:** `reconcile`
**Bảng:** `fact_reconciliation`

**Business Logic:**
Hệ thống tự động so khớp 3 chân: **Order** (Đơn hàng) ↔ **Payment** (Thanh toán) ↔ **Invoice** (Hóa đơn).

Quy tắc so khớp:
- **MATCHED**: `Payment Amount` khớp với `Order Amount` (sai số < 1 đơn vị tiền tệ).
- **UNDERPAID**: Khách trả thiếu tiền.
- **OVERPAID**: Khách trả thừa tiền.
- **NO_PAYMENT**: Đơn hàng chưa có dữ liệu thanh toán.

---

## 6. ETL Pipeline Workflow

Quy trình xử lý dữ liệu được tự động hóa bằng Python (`src/transform/`).

1.  **Load Dimensions**:
    - Load `dim_date` (Generate 1 lần).
    - Load `dim_product`, `dim_channel` (Full refresh).
    - Load `dim_customer` (Xử lý SCD tracking).
2.  **Load Facts**:
    - Load `fact_sales`: Join Order + Order Items + Products, lookup dimension keys.
    - Load `fact_payment`: Transform từ bảng payment nguồn.
3.  **Reconciliation**:
    - Tổng hợp dữ liệu từ Order và Payment.
    - Chạy logic so sánh và ghi vào `fact_reconciliation`.
4.  **Build Marts**:
    - Tổng hợp Customer 360 từ `dw.fact_sales` và `dw.dim_customer`.
    - Tính toán RFM và gán nhãn phân khúc.

---

## 7. Hướng Dẫn Vận Hành Nhanh

### Khởi động hệ thống
```bash
docker-compose up -d
```

### Chạy lại toàn bộ ETL pipeline
```bash
# Chạy script Python trong Docker container
docker run --rm -v "${PWD}:/app" -w /app \
    --network enterperise_de_analytics-network \
    -e SOURCE_DB_HOST=postgres-source \
    -e DW_DB_HOST=postgres-dw \
    -e SOURCE_DB_PORT=5432 \
    -e DW_DB_PORT=5432 \
    python:3.10-slim bash -c "pip install -q pandas sqlalchemy psycopg2-binary python-dotenv numpy && python -m src.transform.run_dw_etl && python -c 'from src.transform.load_customer360 import Customer360Loader, get_dw_engine; loader = Customer360Loader(get_dw_engine()); loader.run()'"
```

### Chạy Tests
```bash
# Chạy test suite cho Sprint 2 & 3
docker run --rm -v "${PWD}:/app" -w /app \
    --network enterperise_de_analytics-network \
    -e DW_DB_HOST=postgres-dw \
    python:3.10-slim bash -c "pip install -q pytest pandas sqlalchemy psycopg2-binary python-dotenv numpy && pytest tests/ -v"
```

### Truy cập Database
- **Source DB**: `localhost:5432` (User: `postgres`, Pass: `postgres`, DB: `ecommerce_source`)
- **Data Warehouse**: `localhost:5433` (User: `postgres`, Pass: `postgres`, DB: `data_warehouse`)
- **Metabase UI**: `http://localhost:3000`
