-- ============================================
-- Data Warehouse Schema - Sprint 2
-- Star Schema with Dimensions and Facts
-- ============================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS reconcile;

-- ============================================
-- DIMENSION TABLES
-- ============================================

-- dim_date: Calendar dimension (2020-2030)
CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key INT PRIMARY KEY,           -- Format: YYYYMMDD
    full_date DATE NOT NULL UNIQUE,
    day_of_week INT NOT NULL,           -- 1=Monday, 7=Sunday
    day_name VARCHAR(10) NOT NULL,
    day_of_month INT NOT NULL,
    day_of_year INT NOT NULL,
    week_of_year INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE
);

-- dim_customer: Customer dimension with SCD Type 2 support
CREATE TABLE IF NOT EXISTS dw.dim_customer (
    customer_key SERIAL PRIMARY KEY,
    customer_id INT NOT NULL,           -- Natural key from source
    customer_code VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    city VARCHAR(100),
    province VARCHAR(100),
    segment VARCHAR(50),
    
    -- SCD Type 2 tracking
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,                      -- NULL = current record
    is_current BOOLEAN DEFAULT TRUE,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_lookup 
    ON dw.dim_customer(customer_id, is_current);

-- dim_product: Product dimension with category denormalized
CREATE TABLE IF NOT EXISTS dw.dim_product (
    product_key SERIAL PRIMARY KEY,
    product_id INT NOT NULL UNIQUE,     -- Natural key
    sku VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category_id INT,
    category_name VARCHAR(100),
    unit_price DECIMAL(15,2),
    cost_price DECIMAL(15,2),
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- dim_channel: Sales channel lookup
CREATE TABLE IF NOT EXISTS dw.dim_channel (
    channel_key SERIAL PRIMARY KEY,
    channel_code VARCHAR(50) NOT NULL UNIQUE,
    channel_name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50)
);

-- Seed channel dimension
INSERT INTO dw.dim_channel (channel_code, channel_name, channel_type) VALUES
    ('Website', 'Website', 'Online'),
    ('Mobile App', 'Mobile App', 'Online'),
    ('Marketplace', 'Marketplace', 'Online'),
    ('Store', 'Physical Store', 'Offline')
ON CONFLICT (channel_code) DO NOTHING;

-- dim_payment_method: Payment method lookup
CREATE TABLE IF NOT EXISTS dw.dim_payment_method (
    payment_method_key SERIAL PRIMARY KEY,
    method_code VARCHAR(50) NOT NULL UNIQUE,
    method_name VARCHAR(100) NOT NULL,
    method_type VARCHAR(50)
);

-- Seed payment method dimension
INSERT INTO dw.dim_payment_method (method_code, method_name, method_type) VALUES
    ('Bank Transfer', 'Bank Transfer', 'Electronic'),
    ('Credit Card', 'Credit Card', 'Card'),
    ('COD', 'Cash on Delivery', 'Cash'),
    ('E-Wallet', 'E-Wallet', 'Electronic')
ON CONFLICT (method_code) DO NOTHING;

-- ============================================
-- FACT TABLES
-- ============================================

-- fact_sales: Order line level sales fact
CREATE TABLE IF NOT EXISTS dw.fact_sales (
    sales_key SERIAL PRIMARY KEY,
    
    -- Dimension foreign keys
    date_key INT NOT NULL REFERENCES dw.dim_date(date_key),
    customer_key INT REFERENCES dw.dim_customer(customer_key),
    product_key INT REFERENCES dw.dim_product(product_key),
    channel_key INT REFERENCES dw.dim_channel(channel_key),
    
    -- Degenerate dimensions
    order_id INT NOT NULL,
    order_number VARCHAR(50),
    order_item_id INT NOT NULL,
    order_status VARCHAR(20),
    
    -- Measures
    quantity INT NOT NULL,
    unit_price DECIMAL(15,2),
    discount_amount DECIMAL(15,2) DEFAULT 0,
    line_total DECIMAL(15,2) NOT NULL,
    cost_amount DECIMAL(15,2),
    profit_amount DECIMAL(15,2),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON dw.fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON dw.fact_sales(customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON dw.fact_sales(product_key);

-- fact_payment: Payment transactions fact
CREATE TABLE IF NOT EXISTS dw.fact_payment (
    payment_key SERIAL PRIMARY KEY,
    
    -- Dimension foreign keys
    date_key INT NOT NULL REFERENCES dw.dim_date(date_key),
    customer_key INT REFERENCES dw.dim_customer(customer_key),
    payment_method_key INT REFERENCES dw.dim_payment_method(payment_method_key),
    
    -- Degenerate dimensions
    order_id INT NOT NULL,
    payment_id INT NOT NULL,
    payment_code VARCHAR(50),
    
    -- Measures
    amount DECIMAL(15,2) NOT NULL,
    
    -- Attributes
    payment_status VARCHAR(20),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_payment_date ON dw.fact_payment(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_payment_order ON dw.fact_payment(order_id);

-- ============================================
-- RECONCILIATION TABLES
-- ============================================

-- fact_reconciliation: Order vs Payment vs Invoice matching
CREATE TABLE IF NOT EXISTS reconcile.fact_reconciliation (
    recon_key SERIAL PRIMARY KEY,
    recon_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Keys
    order_id INT NOT NULL,
    order_number VARCHAR(50),
    customer_id INT,
    date_key INT,
    
    -- Order metrics
    order_amount DECIMAL(15,2),
    order_status VARCHAR(20),
    order_date DATE,
    
    -- Payment metrics
    payment_count INT DEFAULT 0,
    payment_amount DECIMAL(15,2) DEFAULT 0,
    last_payment_date DATE,
    
    -- Invoice metrics
    invoice_count INT DEFAULT 0,
    invoice_amount DECIMAL(15,2) DEFAULT 0,
    
    -- Reconciliation status
    order_payment_status VARCHAR(20),  -- MATCHED, UNDERPAID, OVERPAID, NO_PAYMENT
    payment_invoice_status VARCHAR(20),
    overall_status VARCHAR(20),
    
    -- Variances
    order_payment_variance DECIMAL(15,2) DEFAULT 0,
    payment_invoice_variance DECIMAL(15,2) DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recon_order ON reconcile.fact_reconciliation(order_id);
CREATE INDEX IF NOT EXISTS idx_recon_date ON reconcile.fact_reconciliation(recon_date);
CREATE INDEX IF NOT EXISTS idx_recon_status ON reconcile.fact_reconciliation(overall_status);

-- ============================================
-- RECONCILIATION VIEWS
-- ============================================

-- View: Monthly reconciliation summary
CREATE OR REPLACE VIEW reconcile.v_monthly_summary AS
SELECT 
    DATE_TRUNC('month', recon_date) as month,
    COUNT(*) as total_orders,
    COUNT(*) FILTER (WHERE overall_status = 'MATCHED') as matched_orders,
    COUNT(*) FILTER (WHERE overall_status != 'MATCHED') as unmatched_orders,
    ROUND(100.0 * COUNT(*) FILTER (WHERE overall_status = 'MATCHED') / NULLIF(COUNT(*), 0), 2) as match_rate_pct,
    SUM(order_amount) as total_order_amount,
    SUM(payment_amount) as total_payment_amount,
    SUM(order_payment_variance) as total_variance,
    COUNT(*) FILTER (WHERE order_payment_status = 'NO_PAYMENT') as no_payment_count,
    COUNT(*) FILTER (WHERE order_payment_status = 'UNDERPAID') as underpaid_count,
    COUNT(*) FILTER (WHERE order_payment_status = 'OVERPAID') as overpaid_count
FROM reconcile.fact_reconciliation
GROUP BY 1
ORDER BY 1 DESC;
