-- ============================================================================
-- FILE: 01_create_source_schema.sql
-- PURPOSE: Tạo schema nguồn OLTP cho hệ thống E-commerce
-- AUTHOR: Data Engineering Team
-- VERSION: 1.0
-- ============================================================================

-- ============================================================================
-- PHẦN 1: KHỞI TẠO
-- ============================================================================

-- Bật extension cho UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tạo schema riêng cho e-commerce
DROP SCHEMA IF EXISTS ecommerce CASCADE;
CREATE SCHEMA ecommerce;

-- Set search path
SET search_path TO ecommerce, public;

-- ============================================================================
-- PHẦN 2: TẠO BẢNG DIMENSION (Lookup tables)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2.1 BẢNG CATEGORIES - Danh mục sản phẩm
-- Mục đích: Phân loại sản phẩm theo nhóm
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER REFERENCES ecommerce.categories(id),  -- Hỗ trợ category lồng nhau
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 💡 GIẢI THÍCH:
-- • SERIAL: Auto-increment integer, tự động tăng khi insert
-- • parent_id: Cho phép tạo cây danh mục (Electronics > Phones > Smartphones)
-- • is_active: Soft delete - không xóa thật mà chỉ đánh dấu inactive

COMMENT ON TABLE ecommerce.categories IS 'Bảng danh mục sản phẩm, hỗ trợ phân cấp';
COMMENT ON COLUMN ecommerce.categories.parent_id IS 'ID của danh mục cha, NULL nếu là danh mục gốc';

-- ----------------------------------------------------------------------------
-- 2.2 BẢNG PRODUCTS - Sản phẩm
-- Mục đích: Lưu thông tin sản phẩm bán
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,          -- Stock Keeping Unit - mã sản phẩm
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INTEGER NOT NULL REFERENCES ecommerce.categories(id),
    unit_price DECIMAL(15, 2) NOT NULL,       -- Giá bán
    cost_price DECIMAL(15, 2),                -- Giá vốn (để tính lợi nhuận)
    stock_quantity INTEGER DEFAULT 0,          -- Số lượng tồn kho
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint: giá phải > 0
    CONSTRAINT chk_positive_price CHECK (unit_price > 0),
    CONSTRAINT chk_positive_cost CHECK (cost_price IS NULL OR cost_price >= 0)
);

-- 💡 GIẢI THÍCH:
-- • DECIMAL(15, 2): 15 chữ số tổng, 2 chữ số thập phân -> max 9,999,999,999,999.99
-- • SKU: Mã duy nhất cho mỗi sản phẩm, dùng để quản lý kho
-- • CHECK constraint: Đảm bảo data integrity ở DB level

-- Index cho tìm kiếm nhanh
CREATE INDEX idx_products_category ON ecommerce.products(category_id);
CREATE INDEX idx_products_sku ON ecommerce.products(sku);
CREATE INDEX idx_products_name ON ecommerce.products USING gin(to_tsvector('simple', name));

COMMENT ON TABLE ecommerce.products IS 'Bảng sản phẩm với thông tin giá, kho';
COMMENT ON COLUMN ecommerce.products.sku IS 'Stock Keeping Unit - Mã sản phẩm duy nhất';
COMMENT ON COLUMN ecommerce.products.cost_price IS 'Giá vốn để tính gross margin';

-- ----------------------------------------------------------------------------
-- 2.3 BẢNG CUSTOMERS - Khách hàng
-- Mục đích: Lưu thông tin khách hàng
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.customers (
    id SERIAL PRIMARY KEY,
    customer_code VARCHAR(20) NOT NULL UNIQUE, -- Mã khách hàng: CUST-00001
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(10),                        -- Male, Female, Other
    
    -- Địa chỉ
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'Vietnam',
    
    -- Phân khúc khách hàng (sẽ được tính toán trong DW)
    segment VARCHAR(50) DEFAULT 'New',         -- VIP, Regular, Occasional, New
    
    -- Metadata
    registration_date DATE DEFAULT CURRENT_DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraint
    CONSTRAINT chk_gender CHECK (gender IN ('Male', 'Female', 'Other') OR gender IS NULL)
);

-- 💡 GIẢI THÍCH:
-- • customer_code: Dễ đọc hơn ID số, dùng cho giao tiếp với khách
-- • segment: Được update bởi batch job hoặc trigger dựa trên hành vi mua
-- • registration_date: Ngày đăng ký (khác created_at là timestamp chính xác)

-- Index cho search
CREATE INDEX idx_customers_email ON ecommerce.customers(email);
CREATE INDEX idx_customers_segment ON ecommerce.customers(segment);
CREATE INDEX idx_customers_registration ON ecommerce.customers(registration_date);

COMMENT ON TABLE ecommerce.customers IS 'Bảng khách hàng với thông tin liên hệ và phân khúc';
COMMENT ON COLUMN ecommerce.customers.segment IS 'Phân khúc KH: VIP, Regular, Occasional, New, Churned';

-- ============================================================================
-- PHẦN 3: TẠO BẢNG TRANSACTION (Giao dịch)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 3.1 BẢNG ORDERS - Đơn hàng
-- Mục đích: Lưu thông tin header của đơn hàng
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(20) NOT NULL UNIQUE,  -- ORD-2024-00001
    customer_id INTEGER NOT NULL REFERENCES ecommerce.customers(id),
    
    -- Thời gian
    order_date DATE NOT NULL,
    order_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Trạng thái đơn hàng
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    -- Pending -> Processing -> Shipped -> Delivered -> Completed
    -- Pending -> Cancelled
    
    -- Giá trị đơn hàng
    subtotal DECIMAL(15, 2) NOT NULL DEFAULT 0,      -- Tổng giá sản phẩm
    discount_amount DECIMAL(15, 2) DEFAULT 0,         -- Giảm giá
    tax_amount DECIMAL(15, 2) DEFAULT 0,              -- Thuế
    shipping_fee DECIMAL(15, 2) DEFAULT 0,            -- Phí ship
    total_amount DECIMAL(15, 2) NOT NULL DEFAULT 0,   -- Tổng cộng
    
    -- Kênh bán hàng
    channel VARCHAR(50) DEFAULT 'Website',    -- Website, Mobile App, Store, Marketplace
    
    -- Địa chỉ giao hàng
    shipping_address TEXT,
    shipping_city VARCHAR(100),
    shipping_phone VARCHAR(20),
    
    -- Notes
    customer_note TEXT,
    internal_note TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_order_status CHECK (status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Completed', 'Cancelled', 'Refunded')),
    CONSTRAINT chk_positive_total CHECK (total_amount >= 0)
);

-- 💡 GIẢI THÍCH:
-- • Tách order_date (DATE) và order_timestamp (TIMESTAMP) để:
--   - order_date: Dễ dàng GROUP BY theo ngày
--   - order_timestamp: Giữ thời gian chính xác
-- • subtotal + discount + tax + shipping = total (business rule)
-- • channel: Quan trọng cho phân tích multi-channel

-- Index
CREATE INDEX idx_orders_customer ON ecommerce.orders(customer_id);
CREATE INDEX idx_orders_date ON ecommerce.orders(order_date);
CREATE INDEX idx_orders_status ON ecommerce.orders(status);
CREATE INDEX idx_orders_channel ON ecommerce.orders(channel);
CREATE INDEX idx_orders_timestamp ON ecommerce.orders(order_timestamp);

COMMENT ON TABLE ecommerce.orders IS 'Bảng đơn hàng - header chứa thông tin tổng quan';
COMMENT ON COLUMN ecommerce.orders.channel IS 'Kênh bán: Website, Mobile App, Store, Marketplace';

-- ----------------------------------------------------------------------------
-- 3.2 BẢNG ORDER_ITEMS - Chi tiết đơn hàng
-- Mục đích: Lưu từng sản phẩm trong đơn hàng
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES ecommerce.orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES ecommerce.products(id),
    
    -- Số lượng và giá
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(15, 2) NOT NULL,        -- Giá tại thời điểm mua (có thể khác giá hiện tại)
    discount_percent DECIMAL(5, 2) DEFAULT 0,   -- % giảm giá
    line_total DECIMAL(15, 2) NOT NULL,         -- = quantity * unit_price * (1 - discount_percent/100)
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_positive_quantity CHECK (quantity > 0),
    CONSTRAINT chk_positive_unit_price CHECK (unit_price > 0),
    CONSTRAINT chk_discount_range CHECK (discount_percent >= 0 AND discount_percent <= 100)
);

-- 💡 GIẢI THÍCH:
-- • unit_price được lưu lại vì giá sản phẩm có thể thay đổi theo thời gian
-- • ON DELETE CASCADE: Khi xóa order, tự động xóa order_items
-- • line_total = pre-calculated để tránh tính toán lặp lại

-- Index
CREATE INDEX idx_order_items_order ON ecommerce.order_items(order_id);
CREATE INDEX idx_order_items_product ON ecommerce.order_items(product_id);

COMMENT ON TABLE ecommerce.order_items IS 'Chi tiết đơn hàng - từng sản phẩm trong order';
COMMENT ON COLUMN ecommerce.order_items.unit_price IS 'Giá tại thời điểm mua, không đổi khi sản phẩm thay giá';

-- ----------------------------------------------------------------------------
-- 3.3 BẢNG PAYMENTS - Thanh toán
-- Mục đích: Lưu thông tin thanh toán cho đơn hàng
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.payments (
    id SERIAL PRIMARY KEY,
    payment_code VARCHAR(30) NOT NULL UNIQUE,   -- PAY-2024-00001
    order_id INTEGER NOT NULL REFERENCES ecommerce.orders(id),
    
    -- Thông tin thanh toán
    amount DECIMAL(15, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,        -- Credit Card, Bank Transfer, COD, E-Wallet
    payment_gateway VARCHAR(50),                -- VNPay, Momo, ZaloPay, Stripe
    
    -- Trạng thái
    status VARCHAR(30) NOT NULL DEFAULT 'Pending',
    -- Pending -> Processing -> Completed
    -- Pending -> Failed
    -- Completed -> Refunded
    
    -- Thời gian
    payment_date DATE,
    paid_at TIMESTAMP,                          -- Thời điểm thanh toán thành công
    
    -- Reference từ payment gateway
    transaction_ref VARCHAR(100),               -- Mã giao dịch từ cổng thanh toán
    gateway_response TEXT,                      -- Response JSON từ gateway
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_payment_status CHECK (status IN ('Pending', 'Processing', 'Completed', 'Failed', 'Refunded')),
    CONSTRAINT chk_payment_method CHECK (payment_method IN ('Credit Card', 'Bank Transfer', 'COD', 'E-Wallet', 'Cash'))
);

-- 💡 GIẢI THÍCH:
-- • Một order có thể có nhiều payments (trả góp, thanh toán bổ sung)
-- • transaction_ref: Để đối soát với ngân hàng/gateway
-- • gateway_response: Lưu response để debug khi có issue

-- Index
CREATE INDEX idx_payments_order ON ecommerce.payments(order_id);
CREATE INDEX idx_payments_status ON ecommerce.payments(status);
CREATE INDEX idx_payments_date ON ecommerce.payments(payment_date);
CREATE INDEX idx_payments_method ON ecommerce.payments(payment_method);

COMMENT ON TABLE ecommerce.payments IS 'Bảng thanh toán - track payment cho mỗi order';
COMMENT ON COLUMN ecommerce.payments.transaction_ref IS 'Mã tham chiếu từ cổng thanh toán để đối soát';

-- ============================================================================
-- PHẦN 4: TẠO BẢNG ACCOUNTING/ERP (Kế toán)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4.1 BẢNG INVOICES - Hóa đơn
-- Mục đích: Lưu hóa đơn kế toán
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(30) NOT NULL UNIQUE, -- INV-2024-00001
    order_id INTEGER NOT NULL REFERENCES ecommerce.orders(id),
    customer_id INTEGER NOT NULL REFERENCES ecommerce.customers(id),
    
    -- Thời gian
    invoice_date DATE NOT NULL,
    due_date DATE,                              -- Hạn thanh toán
    
    -- Giá trị
    subtotal DECIMAL(15, 2) NOT NULL,
    tax_amount DECIMAL(15, 2) DEFAULT 0,
    total_amount DECIMAL(15, 2) NOT NULL,
    
    -- Trạng thái
    status VARCHAR(30) NOT NULL DEFAULT 'Issued',
    -- Issued -> Paid -> Closed
    -- Issued -> Overdue -> Paid
    -- Issued -> Cancelled
    
    -- Accounting period
    accounting_period VARCHAR(7),               -- 2024-01 (YYYY-MM)
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_invoice_status CHECK (status IN ('Draft', 'Issued', 'Paid', 'Overdue', 'Cancelled', 'Closed'))
);

-- 💡 GIẢI THÍCH:
-- • Invoice tách riêng vì có thể khác với Order (chiết khấu hậu mãi, điều chỉnh...)
-- • accounting_period: Dùng cho báo cáo theo kỳ kế toán
-- • Có thể có invoice không có order (dịch vụ, adjust)

-- Index
CREATE INDEX idx_invoices_order ON ecommerce.invoices(order_id);
CREATE INDEX idx_invoices_customer ON ecommerce.invoices(customer_id);
CREATE INDEX idx_invoices_date ON ecommerce.invoices(invoice_date);
CREATE INDEX idx_invoices_period ON ecommerce.invoices(accounting_period);

COMMENT ON TABLE ecommerce.invoices IS 'Bảng hóa đơn kế toán';
COMMENT ON COLUMN ecommerce.invoices.accounting_period IS 'Kỳ kế toán format YYYY-MM';

-- ----------------------------------------------------------------------------
-- 4.2 BẢNG INVOICE_ITEMS - Chi tiết hóa đơn
-- Mục đích: Lưu từng dòng trong hóa đơn
-- ----------------------------------------------------------------------------
CREATE TABLE ecommerce.invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES ecommerce.invoices(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES ecommerce.products(id),
    
    description VARCHAR(255) NOT NULL,
    quantity DECIMAL(15, 2) NOT NULL DEFAULT 1,
    unit_price DECIMAL(15, 2) NOT NULL,
    tax_rate DECIMAL(5, 2) DEFAULT 10,          -- VAT 10%
    line_total DECIMAL(15, 2) NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_invoice_items_invoice ON ecommerce.invoice_items(invoice_id);

-- ============================================================================
-- PHẦN 5: TẠO FUNCTIONS VÀ TRIGGERS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 5.1 Function: Auto update updated_at timestamp
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ecommerce.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 💡 GIẢI THÍCH:
-- Trigger function tự động cập nhật updated_at khi có UPDATE
-- Giúp track được thời điểm record được sửa đổi gần nhất

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON ecommerce.categories
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON ecommerce.products
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON ecommerce.customers
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON ecommerce.orders
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

CREATE TRIGGER trg_payments_updated_at
    BEFORE UPDATE ON ecommerce.payments
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

CREATE TRIGGER trg_invoices_updated_at
    BEFORE UPDATE ON ecommerce.invoices
    FOR EACH ROW EXECUTE FUNCTION ecommerce.update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 5.2 Function: Generate sequential codes
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ecommerce.generate_code(prefix VARCHAR, seq_name VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    seq_val INTEGER;
    year_part VARCHAR;
BEGIN
    year_part := to_char(CURRENT_DATE, 'YYYY');
    EXECUTE format('SELECT nextval(''%s'')', seq_name) INTO seq_val;
    RETURN prefix || '-' || year_part || '-' || lpad(seq_val::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

-- 💡 GIẢI THÍCH:
-- Tạo mã code đẹp cho order, payment, invoice
-- Format: PREFIX-YYYY-000001 (e.g., ORD-2024-000001)

-- Create sequences for code generation
CREATE SEQUENCE IF NOT EXISTS ecommerce.customer_code_seq START 1;
CREATE SEQUENCE IF NOT EXISTS ecommerce.order_code_seq START 1;
CREATE SEQUENCE IF NOT EXISTS ecommerce.payment_code_seq START 1;
CREATE SEQUENCE IF NOT EXISTS ecommerce.invoice_code_seq START 1;

-- ============================================================================
-- PHẦN 6: TẠO VIEWS HỮU ÍCH
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6.1 View: Order Summary
-- Mục đích: Tổng hợp thông tin order với customer và payment
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW ecommerce.v_order_summary AS
SELECT 
    o.id AS order_id,
    o.order_number,
    o.order_date,
    o.status AS order_status,
    o.total_amount AS order_total,
    o.channel,
    c.id AS customer_id,
    c.customer_code,
    c.email AS customer_email,
    c.first_name || ' ' || c.last_name AS customer_name,
    c.segment AS customer_segment,
    COALESCE(p.paid_amount, 0) AS paid_amount,
    o.total_amount - COALESCE(p.paid_amount, 0) AS balance_due,
    p.payment_status
FROM ecommerce.orders o
JOIN ecommerce.customers c ON o.customer_id = c.id
LEFT JOIN (
    SELECT 
        order_id,
        SUM(amount) AS paid_amount,
        STRING_AGG(DISTINCT status, ', ') AS payment_status
    FROM ecommerce.payments
    WHERE status = 'Completed'
    GROUP BY order_id
) p ON o.id = p.order_id;

-- 💡 GIẢI THÍCH:
-- View này join sẵn các bảng hay dùng chung
-- balance_due: Số tiền còn nợ = total - paid

COMMENT ON VIEW ecommerce.v_order_summary IS 'View tổng hợp order với customer và payment';

-- ----------------------------------------------------------------------------
-- 6.2 View: Daily Sales Summary
-- Mục đích: Báo cáo doanh số theo ngày
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW ecommerce.v_daily_sales AS
SELECT 
    order_date,
    channel,
    COUNT(DISTINCT id) AS order_count,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(total_amount) AS gross_revenue,
    SUM(discount_amount) AS total_discount,
    SUM(total_amount) - SUM(discount_amount) AS net_revenue,
    AVG(total_amount) AS avg_order_value
FROM ecommerce.orders
WHERE status NOT IN ('Cancelled', 'Refunded')
GROUP BY order_date, channel
ORDER BY order_date DESC, channel;

COMMENT ON VIEW ecommerce.v_daily_sales IS 'View doanh số bán hàng theo ngày và kênh';

-- ============================================================================
-- HOÀN TẤT
-- ============================================================================

-- Verify tables created
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'ecommerce'
ORDER BY table_name;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE '✅ Schema ecommerce created successfully with % tables', 
        (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'ecommerce');
END $$;
