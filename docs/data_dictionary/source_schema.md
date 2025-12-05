# 📊 Source Schema Documentation

> **Document Version**: 1.0  
> **Last Updated**: December 2024  
> **Database**: PostgreSQL 15  
> **Schema**: `ecommerce`

---

## 1. ERD Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              E-COMMERCE ERD                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────┐        ┌──────────────┐        ┌──────────────┐             │
│   │  CATEGORIES  │        │   PRODUCTS   │        │   CUSTOMERS  │             │
│   │──────────────│        │──────────────│        │──────────────│             │
│   │ PK: id       │◄──┐    │ PK: id       │        │ PK: id       │             │
│   │ name         │   │    │ FK: cat_id   │        │ customer_code│             │
│   │ description  │   │    │ sku          │        │ email        │             │
│   │ parent_id    │   │    │ name         │        │ first_name   │             │
│   │ is_active    │   │    │ unit_price   │        │ last_name    │             │
│   │ created_at   │   │    │ cost_price   │        │ phone        │             │
│   │ updated_at   │   │    │ stock_qty    │        │ segment      │             │
│   └──────────────┘   │    │ is_active    │        │ city         │             │
│                      │    │ created_at   │        │ created_at   │             │
│                      │    │ updated_at   │        │ updated_at   │             │
│                      │    └──────────────┘        └──────────────┘             │
│                      │           │                       │                      │
│                      └───────────┤                       │                      │
│                                  │                       │                      │
│                                  │                       │                      │
│   ┌──────────────┐               │      ┌────────────────┘                      │
│   │   PAYMENTS   │               │      │                                       │
│   │──────────────│               │      │       ┌──────────────┐                │
│   │ PK: id       │               │      │       │    ORDERS    │                │
│   │ payment_code │               │      │       │──────────────│                │
│   │ FK: order_id │◄──────────────┼──────┼──────►│ PK: id       │                │
│   │ amount       │               │      │       │ order_number │                │
│   │ method       │               │      └──────►│ FK: cust_id  │                │
│   │ gateway      │               │              │ order_date   │                │
│   │ status       │               │              │ status       │                │
│   │ paid_at      │               │              │ total_amount │                │
│   │ trans_ref    │               │              │ channel      │                │
│   │ created_at   │               │              │ created_at   │                │
│   │ updated_at   │               │              │ updated_at   │                │
│   └──────────────┘               │              └──────────────┘                │
│                                  │                     │                        │
│                                  │                     │                        │
│                                  │                     ▼                        │
│                                  │              ┌──────────────┐                │
│                                  │              │ ORDER_ITEMS  │                │
│                                  │              │──────────────│                │
│                                  │              │ PK: id       │                │
│                                  └─────────────►│ FK: order_id │                │
│                                                 │ FK: prod_id  │                │
│                                                 │ quantity     │                │
│                                                 │ unit_price   │                │
│                                                 │ discount_%   │                │
│                                                 │ line_total   │                │
│                                                 │ created_at   │                │
│                                                 └──────────────┘                │
│                                                                                 │
│   ┌──────────────┐               ┌──────────────┐                              │
│   │   INVOICES   │               │INVOICE_ITEMS │                              │
│   │──────────────│               │──────────────│                              │
│   │ PK: id       │◄──────────────│ FK: inv_id   │                              │
│   │ invoice_no   │               │ FK: prod_id  │                              │
│   │ FK: order_id │               │ quantity     │                              │
│   │ FK: cust_id  │               │ unit_price   │                              │
│   │ invoice_date │               │ tax_rate     │                              │
│   │ total_amount │               │ line_total   │                              │
│   │ status       │               │ created_at   │                              │
│   │ acc_period   │               └──────────────┘                              │
│   │ created_at   │                                                             │
│   │ updated_at   │                                                             │
│   └──────────────┘                                                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

LEGEND:
  PK = Primary Key
  FK = Foreign Key
  ─── = Relationship (many-to-one toward arrow)
```

---

## 2. Table Specifications

### 2.1 categories

**Purpose**: Phân loại sản phẩm, hỗ trợ phân cấp (cây danh mục)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `name` | VARCHAR(100) | NO | - | Tên danh mục (unique) |
| `description` | TEXT | YES | - | Mô tả danh mục |
| `parent_id` | INTEGER | YES | NULL | FK → categories.id (self-ref) |
| `is_active` | BOOLEAN | YES | TRUE | Soft delete flag |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |
| `updated_at` | TIMESTAMP | YES | NOW() | Thời điểm cập nhật |

**Constraints**:
- PK: `id`
- UNIQUE: `name`
- FK: `parent_id` → `categories(id)`

**Sample Data**:
```
id | name                  | parent_id | is_active
---|-----------------------|-----------|----------
1  | Điện thoại & Phụ kiện | NULL      | true
2  | Laptop & Máy tính     | NULL      | true
3  | Thời trang Nam        | NULL      | true
```

---

### 2.2 products

**Purpose**: Danh mục sản phẩm bán

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `sku` | VARCHAR(50) | NO | - | Stock Keeping Unit (unique) |
| `name` | VARCHAR(255) | NO | - | Tên sản phẩm |
| `description` | TEXT | YES | - | Mô tả chi tiết |
| `category_id` | INTEGER | NO | - | FK → categories.id |
| `unit_price` | DECIMAL(15,2) | NO | - | Giá bán (VND) |
| `cost_price` | DECIMAL(15,2) | YES | - | Giá vốn |
| `stock_quantity` | INTEGER | YES | 0 | Số lượng tồn kho |
| `is_active` | BOOLEAN | YES | TRUE | Còn kinh doanh không |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |
| `updated_at` | TIMESTAMP | YES | NOW() | Thời điểm cập nhật |

**Constraints**:
- PK: `id`
- UNIQUE: `sku`
- FK: `category_id` → `categories(id)`
- CHECK: `unit_price > 0`
- CHECK: `cost_price IS NULL OR cost_price >= 0`

**Indexes**:
- `idx_products_category` ON `category_id`
- `idx_products_sku` ON `sku`
- `idx_products_name` (GIN full-text)

---

### 2.3 customers

**Purpose**: Thông tin khách hàng

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `customer_code` | VARCHAR(20) | NO | - | Mã KH: CUST-YYYY-000001 |
| `email` | VARCHAR(255) | NO | - | Email (unique) |
| `first_name` | VARCHAR(100) | NO | - | Tên |
| `last_name` | VARCHAR(100) | NO | - | Họ |
| `phone` | VARCHAR(20) | YES | - | Số điện thoại |
| `date_of_birth` | DATE | YES | - | Ngày sinh |
| `gender` | VARCHAR(10) | YES | - | Male/Female/Other |
| `address_line1` | VARCHAR(255) | YES | - | Địa chỉ dòng 1 |
| `address_line2` | VARCHAR(255) | YES | - | Địa chỉ dòng 2 |
| `city` | VARCHAR(100) | YES | - | Thành phố |
| `state` | VARCHAR(100) | YES | - | Tỉnh/Bang |
| `postal_code` | VARCHAR(20) | YES | - | Mã bưu chính |
| `country` | VARCHAR(100) | YES | 'Vietnam' | Quốc gia |
| `segment` | VARCHAR(50) | YES | 'New' | Phân khúc KH |
| `registration_date` | DATE | YES | TODAY | Ngày đăng ký |
| `is_active` | BOOLEAN | YES | TRUE | Còn hoạt động |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |
| `updated_at` | TIMESTAMP | YES | NOW() | Thời điểm cập nhật |

**Constraints**:
- PK: `id`
- UNIQUE: `customer_code`, `email`
- CHECK: `gender IN ('Male', 'Female', 'Other') OR gender IS NULL`

**Segment Values**: `VIP`, `Regular`, `Occasional`, `New`, `Churned`

---

### 2.4 orders

**Purpose**: Đơn hàng (header)

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `order_number` | VARCHAR(20) | NO | - | Mã đơn: ORD-YYYY-000001 |
| `customer_id` | INTEGER | NO | - | FK → customers.id |
| `order_date` | DATE | NO | - | Ngày đặt hàng |
| `order_timestamp` | TIMESTAMP | NO | NOW() | Thời điểm chính xác |
| `status` | VARCHAR(30) | NO | 'Pending' | Trạng thái đơn |
| `subtotal` | DECIMAL(15,2) | NO | 0 | Tổng giá sản phẩm |
| `discount_amount` | DECIMAL(15,2) | YES | 0 | Số tiền giảm giá |
| `tax_amount` | DECIMAL(15,2) | YES | 0 | Thuế VAT |
| `shipping_fee` | DECIMAL(15,2) | YES | 0 | Phí vận chuyển |
| `total_amount` | DECIMAL(15,2) | NO | 0 | Tổng thanh toán |
| `channel` | VARCHAR(50) | YES | 'Website' | Kênh bán hàng |
| `shipping_address` | TEXT | YES | - | Địa chỉ giao |
| `shipping_city` | VARCHAR(100) | YES | - | Thành phố giao |
| `shipping_phone` | VARCHAR(20) | YES | - | SĐT nhận hàng |
| `customer_note` | TEXT | YES | - | Ghi chú KH |
| `internal_note` | TEXT | YES | - | Ghi chú nội bộ |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |
| `updated_at` | TIMESTAMP | YES | NOW() | Thời điểm cập nhật |

**Status Flow**:
```
Pending → Processing → Shipped → Delivered → Completed
    │                                 
    └──────────────────────────────→ Cancelled
                                          │
Completed ────────────────────────────→ Refunded
```

**Channel Values**: `Website`, `Mobile App`, `Marketplace`, `Store`

---

### 2.5 order_items

**Purpose**: Chi tiết từng sản phẩm trong đơn hàng

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `order_id` | INTEGER | NO | - | FK → orders.id |
| `product_id` | INTEGER | NO | - | FK → products.id |
| `quantity` | INTEGER | NO | 1 | Số lượng |
| `unit_price` | DECIMAL(15,2) | NO | - | Giá tại thời điểm mua |
| `discount_percent` | DECIMAL(5,2) | YES | 0 | % giảm giá |
| `line_total` | DECIMAL(15,2) | NO | - | Thành tiền |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |

**Constraints**:
- PK: `id`
- FK: `order_id` → `orders(id)` ON DELETE CASCADE
- FK: `product_id` → `products(id)`
- CHECK: `quantity > 0`
- CHECK: `unit_price > 0`
- CHECK: `discount_percent BETWEEN 0 AND 100`

**Formula**: `line_total = quantity * unit_price * (1 - discount_percent/100)`

---

### 2.6 payments

**Purpose**: Giao dịch thanh toán

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `payment_code` | VARCHAR(30) | NO | - | Mã: PAY-YYYY-000001 |
| `order_id` | INTEGER | NO | - | FK → orders.id |
| `amount` | DECIMAL(15,2) | NO | - | Số tiền thanh toán |
| `payment_method` | VARCHAR(50) | NO | - | Phương thức TT |
| `payment_gateway` | VARCHAR(50) | YES | - | Cổng thanh toán |
| `status` | VARCHAR(30) | NO | 'Pending' | Trạng thái |
| `payment_date` | DATE | YES | - | Ngày thanh toán |
| `paid_at` | TIMESTAMP | YES | - | Thời điểm TT thành công |
| `transaction_ref` | VARCHAR(100) | YES | - | Mã giao dịch gateway |
| `gateway_response` | TEXT | YES | - | Response từ gateway |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |
| `updated_at` | TIMESTAMP | YES | NOW() | Thời điểm cập nhật |

**Payment Methods**: `Credit Card`, `Bank Transfer`, `COD`, `E-Wallet`, `Cash`

**Payment Gateways**: `VNPay`, `Momo`, `ZaloPay`, `OnePay`, `Stripe`

**Status Values**: `Pending`, `Processing`, `Completed`, `Failed`, `Refunded`

---

### 2.7 invoices

**Purpose**: Hóa đơn kế toán

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `invoice_number` | VARCHAR(30) | NO | - | Số hóa đơn |
| `order_id` | INTEGER | NO | - | FK → orders.id |
| `customer_id` | INTEGER | NO | - | FK → customers.id |
| `invoice_date` | DATE | NO | - | Ngày xuất HĐ |
| `due_date` | DATE | YES | - | Hạn thanh toán |
| `subtotal` | DECIMAL(15,2) | NO | - | Tiền hàng |
| `tax_amount` | DECIMAL(15,2) | YES | 0 | Thuế |
| `total_amount` | DECIMAL(15,2) | NO | - | Tổng cộng |
| `status` | VARCHAR(30) | NO | 'Issued' | Trạng thái |
| `accounting_period` | VARCHAR(7) | YES | - | Kỳ kế toán (YYYY-MM) |
| `notes` | TEXT | YES | - | Ghi chú |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |
| `updated_at` | TIMESTAMP | YES | NOW() | Thời điểm cập nhật |

**Status Values**: `Draft`, `Issued`, `Paid`, `Overdue`, `Cancelled`, `Closed`

---

### 2.8 invoice_items

**Purpose**: Chi tiết hóa đơn

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | SERIAL | NO | auto | Primary Key |
| `invoice_id` | INTEGER | NO | - | FK → invoices.id |
| `product_id` | INTEGER | YES | - | FK → products.id |
| `description` | VARCHAR(255) | NO | - | Mô tả dòng |
| `quantity` | DECIMAL(15,2) | NO | 1 | Số lượng |
| `unit_price` | DECIMAL(15,2) | NO | - | Đơn giá |
| `tax_rate` | DECIMAL(5,2) | YES | 10 | % thuế |
| `line_total` | DECIMAL(15,2) | NO | - | Thành tiền |
| `created_at` | TIMESTAMP | YES | NOW() | Thời điểm tạo |

---

## 3. Views

### 3.1 v_order_summary

**Purpose**: Tổng hợp thông tin order + customer + payment

```sql
SELECT 
    o.id AS order_id,
    o.order_number,
    o.order_date,
    o.status AS order_status,
    o.total_amount AS order_total,
    o.channel,
    c.customer_code,
    c.email AS customer_email,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.segment AS customer_segment,
    COALESCE(p.paid_amount, 0) AS paid_amount,
    o.total_amount - COALESCE(p.paid_amount, 0) AS balance_due
FROM orders o
JOIN customers c ON o.customer_id = c.id
LEFT JOIN (payment aggregation) p ON o.id = p.order_id;
```

### 3.2 v_daily_sales

**Purpose**: Doanh số theo ngày và kênh

```sql
SELECT 
    order_date,
    channel,
    COUNT(DISTINCT id) AS order_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(total_amount) AS gross_revenue,
    AVG(total_amount) AS avg_order_value
FROM orders
WHERE status NOT IN ('Cancelled', 'Refunded')
GROUP BY order_date, channel;
```

---

## 4. Triggers

### 4.1 Auto-update updated_at

**Purpose**: Tự động cập nhật `updated_at` khi có UPDATE

**Tables applied**: `categories`, `products`, `customers`, `orders`, `payments`, `invoices`

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## 5. Data Dictionary Summary

| Table | Description | Record Count (Est.) | Key Metrics |
|-------|-------------|---------------------|-------------|
| categories | Product categories | 20 | Lookup table |
| products | Product master | 1,000 | SKU, Price |
| customers | Customer master | 10,000 | Segment |
| orders | Order header | 100,000/year | Revenue |
| order_items | Order details | 250,000/year | Qty, Amount |
| payments | Payment records | 100,000/year | Amount, Status |
| invoices | Invoice header | 80,000/year | Amount |
| invoice_items | Invoice details | 200,000/year | Line items |

---

## 6. Important Relationships for Analytics

### 6.1 Customer → Orders (Revenue Analysis)

```sql
-- Total revenue by customer
SELECT customer_id, SUM(total_amount) as lifetime_value
FROM orders
WHERE status = 'Completed'
GROUP BY customer_id;
```

### 6.2 Order → Payment (Reconciliation)

```sql
-- Find orders with payment mismatch
SELECT 
    o.order_number,
    o.total_amount as order_amount,
    COALESCE(SUM(p.amount), 0) as paid_amount,
    o.total_amount - COALESCE(SUM(p.amount), 0) as discrepancy
FROM orders o
LEFT JOIN payments p ON o.id = p.order_id AND p.status = 'Completed'
GROUP BY o.id
HAVING ABS(o.total_amount - COALESCE(SUM(p.amount), 0)) > 1;
```

### 6.3 Order → Invoice (Accounting Reconciliation)

```sql
-- Find orders without invoice
SELECT o.*
FROM orders o
LEFT JOIN invoices i ON o.id = i.order_id
WHERE o.status = 'Completed'
  AND i.id IS NULL;
```

---

> 📝 **Note**: Schema này được thiết kế cho mục đích học tập và demo. Production system cần thêm các considerations về security, partitioning, và performance tuning.
