-- ============================================
-- Customer 360 & Marketing Analytics Mart - Sprint 3
-- ============================================

-- ============================================
-- MART TABLES
-- ============================================

-- mart_customer_360: Comprehensive customer profile with behavior metrics
CREATE TABLE IF NOT EXISTS mart.mart_customer_360 (
    customer_key INT PRIMARY KEY,
    customer_id INT NOT NULL,
    customer_code VARCHAR(20),
    
    -- Customer Info
    email VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(200),
    phone VARCHAR(20),
    city VARCHAR(100),
    segment VARCHAR(50),
    
    -- First/Last Activity
    first_order_date DATE,
    last_order_date DATE,
    customer_tenure_days INT,
    days_since_last_order INT,
    
    -- Order Metrics
    total_orders INT DEFAULT 0,
    total_order_items INT DEFAULT 0,
    cancelled_orders INT DEFAULT 0,
    
    -- Revenue Metrics
    total_revenue DECIMAL(15,2) DEFAULT 0,
    total_discount DECIMAL(15,2) DEFAULT 0,
    net_revenue DECIMAL(15,2) DEFAULT 0,
    avg_order_value DECIMAL(15,2) DEFAULT 0,
    
    -- Product Metrics
    unique_products_purchased INT DEFAULT 0,
    unique_categories_purchased INT DEFAULT 0,
    
    -- Payment Metrics
    total_payments INT DEFAULT 0,
    total_payment_amount DECIMAL(15,2) DEFAULT 0,
    preferred_payment_method VARCHAR(50),
    
    -- Channel Metrics
    preferred_channel VARCHAR(50),
    
    -- RFM Scores (1-5, 5 is best)
    recency_score INT,
    frequency_score INT,
    monetary_score INT,
    rfm_score VARCHAR(10),         -- e.g., "555", "211"
    rfm_segment VARCHAR(50),       -- e.g., "Champions", "At Risk"
    
    -- LTV (Lifetime Value)
    estimated_ltv DECIMAL(15,2),
    
    -- Status
    customer_status VARCHAR(20),   -- Active, Inactive, Churned, New
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mart_c360_segment ON mart.mart_customer_360(segment);
CREATE INDEX IF NOT EXISTS idx_mart_c360_rfm_segment ON mart.mart_customer_360(rfm_segment);
CREATE INDEX IF NOT EXISTS idx_mart_c360_status ON mart.mart_customer_360(customer_status);

-- ============================================
-- RFM REFERENCE TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS mart.rfm_segment_mapping (
    rfm_pattern VARCHAR(10) PRIMARY KEY,
    segment_name VARCHAR(50) NOT NULL,
    description TEXT,
    recommended_action TEXT
);

-- Seed RFM segment mappings
INSERT INTO mart.rfm_segment_mapping (rfm_pattern, segment_name, description, recommended_action) VALUES
    ('555', 'Champions', 'Best customers - bought recently, buy often, spend most', 'Reward them, early access to new products'),
    ('554', 'Champions', 'Best customers - bought recently, buy often, spend most', 'Reward them, early access to new products'),
    ('545', 'Champions', 'Best customers - bought recently, buy often, spend most', 'Reward them, early access to new products'),
    ('544', 'Loyal Customers', 'Spend good money, responsive to promotions', 'Upsell higher value products'),
    ('455', 'Loyal Customers', 'Spend good money, responsive to promotions', 'Upsell higher value products'),
    ('445', 'Loyal Customers', 'Spend good money, responsive to promotions', 'Upsell higher value products'),
    ('535', 'Potential Loyalists', 'Recent customers, spent good amount, bought more than once', 'Offer membership/loyalty program'),
    ('525', 'Potential Loyalists', 'Recent customers, spent good amount, bought more than once', 'Offer membership/loyalty program'),
    ('515', 'New Customers', 'Bought recently, but not often', 'Provide onboarding support, special offers'),
    ('514', 'New Customers', 'Bought recently, but not often', 'Provide onboarding support, special offers'),
    ('513', 'New Customers', 'Bought recently, but not often', 'Provide onboarding support, special offers'),
    ('512', 'New Customers', 'Bought recently, but not often', 'Provide onboarding support, special offers'),
    ('511', 'New Customers', 'Bought recently, but not often', 'Provide onboarding support, special offers'),
    ('333', 'Need Attention', 'Average customers', 'Make limited time offers'),
    ('332', 'Need Attention', 'Average customers', 'Make limited time offers'),
    ('323', 'Need Attention', 'Average customers', 'Make limited time offers'),
    ('322', 'Need Attention', 'Average customers', 'Make limited time offers'),
    ('233', 'About To Sleep', 'Below average, will lose if not reactivated', 'Share valuable resources, recommend popular products'),
    ('232', 'About To Sleep', 'Below average, will lose if not reactivated', 'Share valuable resources, recommend popular products'),
    ('223', 'About To Sleep', 'Below average, will lose if not reactivated', 'Share valuable resources, recommend popular products'),
    ('222', 'At Risk', 'Spent big money, purchased often, but long time ago', 'Send personalized emails, offer renewals'),
    ('221', 'At Risk', 'Spent big money, purchased often, but long time ago', 'Send personalized emails, offer renewals'),
    ('212', 'At Risk', 'Spent big money, purchased often, but long time ago', 'Send personalized emails, offer renewals'),
    ('211', 'At Risk', 'Spent big money, purchased often, but long time ago', 'Send personalized emails, offer renewals'),
    ('155', 'Cannot Lose Them', 'Made big purchases but havent returned', 'Win them back via renewals or newer products'),
    ('145', 'Cannot Lose Them', 'Made big purchases but havent returned', 'Win them back via renewals or newer products'),
    ('144', 'Cannot Lose Them', 'Made big purchases but havent returned', 'Win them back via renewals or newer products'),
    ('133', 'Hibernating', 'Last purchase was long ago, low spending', 'Offer other relevant products and discounts'),
    ('132', 'Hibernating', 'Last purchase was long ago, low spending', 'Offer other relevant products and discounts'),
    ('122', 'Hibernating', 'Last purchase was long ago, low spending', 'Offer other relevant products and discounts'),
    ('111', 'Lost', 'Lowest recency, frequency and monetary scores', 'Revive interest with reach out campaign')
ON CONFLICT (rfm_pattern) DO NOTHING;

-- ============================================
-- AGGREGATE VIEWS
-- ============================================

-- View: Revenue by month
CREATE OR REPLACE VIEW mart.v_revenue_by_month AS
SELECT 
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.order_id) as order_count,
    COUNT(f.sales_key) as item_count,
    SUM(f.quantity) as total_quantity,
    SUM(f.line_total) as total_revenue,
    SUM(f.profit_amount) as total_profit,
    COUNT(DISTINCT f.customer_key) as unique_customers
FROM dw.fact_sales f
JOIN dw.dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- View: Revenue by product category
CREATE OR REPLACE VIEW mart.v_revenue_by_category AS
SELECT 
    p.category_name,
    COUNT(DISTINCT f.order_id) as order_count,
    COUNT(f.sales_key) as item_count,
    SUM(f.quantity) as total_quantity,
    SUM(f.line_total) as total_revenue,
    SUM(f.profit_amount) as total_profit,
    COUNT(DISTINCT f.customer_key) as unique_customers
FROM dw.fact_sales f
JOIN dw.dim_product p ON f.product_key = p.product_key
GROUP BY p.category_name
ORDER BY total_revenue DESC;

-- View: Revenue by channel
CREATE OR REPLACE VIEW mart.v_revenue_by_channel AS
SELECT 
    c.channel_name,
    c.channel_type,
    COUNT(DISTINCT f.order_id) as order_count,
    SUM(f.line_total) as total_revenue,
    COUNT(DISTINCT f.customer_key) as unique_customers,
    AVG(f.line_total) as avg_order_value
FROM dw.fact_sales f
JOIN dw.dim_channel c ON f.channel_key = c.channel_key
GROUP BY c.channel_name, c.channel_type
ORDER BY total_revenue DESC;

-- View: Customer segment summary
CREATE OR REPLACE VIEW mart.v_customer_segment_summary AS
SELECT 
    rfm_segment,
    COUNT(*) as customer_count,
    AVG(total_revenue) as avg_revenue,
    AVG(total_orders) as avg_orders,
    AVG(estimated_ltv) as avg_ltv
FROM mart.mart_customer_360
WHERE rfm_segment IS NOT NULL
GROUP BY rfm_segment
ORDER BY avg_revenue DESC;
