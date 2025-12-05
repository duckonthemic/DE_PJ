# 📋 Business Requirements - Enterprise Customer & Revenue Analytics Platform

> **Document Version**: 1.0  
> **Last Updated**: December 2024  
> **Author**: Data Engineering Team

---

## 1. Tổng Quan Dự Án

### 1.1 Mục Tiêu Dự Án

Xây dựng một nền tảng phân tích dữ liệu khách hàng và doanh thu ở cấp độ doanh nghiệp, giải quyết 3 bài toán chính:

| # | Bài Toán | Mô Tả | Stakeholder |
|---|----------|-------|-------------|
| 1 | **Data Warehouse Modernization** | Chuyển từ báo cáo Excel sang DW chuẩn | Finance, Operations |
| 2 | **Customer 360 & Marketing Analytics** | Phân tích hành vi khách hàng, RFM, LTV | Marketing, Sales |
| 3 | **Payment Reconciliation** | Đối soát giao dịch giữa các hệ thống | Finance, Accounting |

### 1.2 Phạm Vi Hệ Thống

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM SCOPE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   IN SCOPE:                              OUT OF SCOPE:                      │
│   ─────────                              ────────────                       │
│   ✅ E-commerce Order System             ❌ Real-time streaming             │
│   ✅ Payment Gateway Integration         ❌ Mobile app analytics             │
│   ✅ Basic ERP/Accounting                ❌ Predictive ML models             │
│   ✅ Customer Analytics                  ❌ Multi-currency                   │
│   ✅ Revenue Reconciliation              ❌ Multi-warehouse                  │
│   ✅ Batch Processing (Daily)            ❌ B2B/Wholesale                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Business Context

### 2.1 Mô Tả Doanh Nghiệp

**Công ty ABC E-commerce** là một công ty bán lẻ trực tuyến với đặc điểm:

- **Quy mô**: Trung bình 10,000+ khách hàng, 100,000+ đơn hàng/năm
- **Kênh bán**: Website, Mobile App, Marketplace (Shopee, Lazada), Cửa hàng
- **Sản phẩm**: 20 danh mục, 1,000+ SKU
- **Thị trường**: Việt Nam

### 2.2 Hiện Trạng (As-Is)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CURRENT STATE (AS-IS)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   PROBLEMS:                                                                 │
│   ──────────                                                                │
│   ⚠️ Dữ liệu nằm rải rác nhiều hệ thống (Excel, MySQL, API logs)           │
│   ⚠️ Báo cáo thủ công, mất 2-3 ngày để ra số liệu tháng                    │
│   ⚠️ Không có cái nhìn 360° về khách hàng                                   │
│   ⚠️ Đối soát payment thủ công, sai sót cao                                 │
│   ⚠️ Không track được ROI marketing campaigns                               │
│   ⚠️ Finance và Sales có số liệu khác nhau                                  │
│                                                                             │
│   IMPACT:                                                                   │
│   ─────────                                                                 │
│   💰 Thất thoát ước tính 2-3% doanh thu do đối soát sai                    │
│   ⏰ 40+ giờ/tháng cho báo cáo thủ công                                     │
│   📉 Quyết định marketing dựa trên cảm tính                                 │
│   😤 Khách hàng VIP không được chăm sóc đúng mức                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Mục Tiêu Tương Lai (To-Be)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TARGET STATE (TO-BE)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   GOALS:                                                                    │
│   ───────                                                                   │
│   ✅ Single Source of Truth cho toàn bộ data                                │
│   ✅ Báo cáo tự động T+1 (có số ngày hôm qua vào sáng hôm sau)             │
│   ✅ Dashboard real-time* cho KPI quan trọng                                │
│   ✅ Customer 360 view với RFM segmentation                                 │
│   ✅ Tự động phát hiện chênh lệch reconciliation                            │
│   ✅ Data quality được monitor và alert                                     │
│                                                                             │
│   SUCCESS METRICS:                                                          │
│   ─────────────────                                                         │
│   📊 Giảm 90% thời gian làm báo cáo                                         │
│   💰 Phát hiện 100% chênh lệch payment > 100k VND                          │
│   🎯 Tăng 20% conversion từ targeted marketing                              │
│   ⚡ Dashboard load < 5 seconds                                             │
│                                                                             │
│   * real-time = refresh mỗi 15-30 phút trong MVP                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stakeholders & Users

### 3.1 Stakeholder Matrix

| Role | Department | Needs | Priority |
|------|------------|-------|----------|
| **CFO** | Finance | Báo cáo doanh thu chính xác, đối soát | High |
| **Marketing Manager** | Marketing | Customer segmentation, campaign ROI | High |
| **Sales Director** | Sales | Customer 360, top customers | High |
| **Accountant** | Accounting | Reconciliation reports | High |
| **Product Manager** | Product | Product performance analytics | Medium |
| **Data Analyst** | BI | Self-service analytics | Medium |

### 3.2 User Stories

#### Finance & Accounting

```
US-F01: As a CFO, I want to see daily revenue dashboard 
        so that I can track business performance.
        
US-F02: As an Accountant, I want to see orders with payment mismatch
        so that I can investigate and resolve discrepancies.
        
US-F03: As a CFO, I want monthly revenue by channel
        so that I can evaluate channel effectiveness.
```

#### Marketing & Sales

```
US-M01: As a Marketing Manager, I want to segment customers by RFM
        so that I can create targeted campaigns.
        
US-M02: As a Sales Director, I want to see Customer 360 view
        so that I can understand customer behavior.
        
US-M03: As a Marketing Manager, I want to identify churning customers
        so that I can run retention campaigns.
```

#### Operations

```
US-O01: As an Operations Manager, I want to see order status distribution
        so that I can identify fulfillment issues.
        
US-O02: As a Product Manager, I want to see top-selling products
        so that I can optimize inventory.
```

---

## 4. Analytical Questions (Câu Hỏi Phân Tích)

### 4.1 Revenue Analytics

| ID | Question | Metric | Frequency |
|----|----------|--------|-----------|
| R01 | Tổng doanh thu hôm nay/tuần/tháng là bao nhiêu? | Total Revenue | Daily |
| R02 | Doanh thu theo từng kênh bán hàng? | Revenue by Channel | Weekly |
| R03 | Tỷ lệ tăng trưởng doanh thu MoM, YoY? | Revenue Growth % | Monthly |
| R04 | Average Order Value (AOV) là bao nhiêu? | AOV | Daily |
| R05 | Gross Margin theo category? | Margin % | Monthly |

### 4.2 Customer Analytics

| ID | Question | Metric | Frequency |
|----|----------|--------|-----------|
| C01 | Có bao nhiêu khách hàng mới trong tháng? | New Customer Count | Monthly |
| C02 | Tỷ lệ khách quay lại mua hàng? | Repeat Purchase Rate | Monthly |
| C03 | Phân bố khách hàng theo segment (VIP, Regular...)? | Segment Distribution | Monthly |
| C04 | Top 100 khách hàng theo doanh thu? | Top Customers | Monthly |
| C05 | Customer Lifetime Value trung bình? | Avg CLV | Quarterly |
| C06 | Khách hàng nào có dấu hiệu churn? | Churn Risk Score | Weekly |

### 4.3 RFM Analysis

| ID | Question | Metric |
|----|----------|--------|
| RFM01 | Recency: Khách hàng mua lần cuối cách đây bao lâu? | Days since last purchase |
| RFM02 | Frequency: Khách hàng mua bao nhiêu lần trong 12 tháng? | Purchase count |
| RFM03 | Monetary: Tổng chi tiêu của khách hàng? | Total spend |
| RFM04 | Phân loại khách hàng theo RFM score? | RFM Segment |

### 4.4 Reconciliation

| ID | Question | Metric | Frequency |
|----|----------|--------|-----------|
| RC01 | Có bao nhiêu đơn hàng chưa được thanh toán? | Unpaid Orders Count | Daily |
| RC02 | Tổng giá trị chênh lệch Order vs Payment? | Discrepancy Amount | Daily |
| RC03 | Có bao nhiêu payment không match với order? | Unmatched Payments | Daily |
| RC04 | Invoice nào chưa khớp với Order? | Mismatched Invoices | Daily |

---

## 5. Data Requirements

### 5.1 Data Sources

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   1. E-COMMERCE DATABASE (PostgreSQL)                                       │
│      ├── customers          # Thông tin khách hàng                          │
│      ├── products           # Danh mục sản phẩm                             │
│      ├── categories         # Phân loại sản phẩm                            │
│      ├── orders             # Đơn hàng                                      │
│      └── order_items        # Chi tiết đơn hàng                             │
│                                                                             │
│   2. PAYMENT GATEWAY                                                        │
│      └── payments           # Giao dịch thanh toán                          │
│                                                                             │
│   3. ERP/ACCOUNTING                                                         │
│      ├── invoices           # Hóa đơn                                       │
│      └── invoice_items      # Chi tiết hóa đơn                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Data Volume Estimates

| Table | Est. Rows/Year | Growth Rate | Retention |
|-------|----------------|-------------|-----------|
| customers | 10,000 | 20%/year | Forever |
| products | 1,000 | 10%/year | Forever |
| orders | 100,000 | 30%/year | 5 years |
| order_items | 250,000 | 30%/year | 5 years |
| payments | 100,000 | 30%/year | 7 years |
| invoices | 80,000 | 30%/year | 10 years |

### 5.3 Data Quality Requirements

| Dimension | Requirement | Priority |
|-----------|-------------|----------|
| **Completeness** | Không có NULL cho các trường bắt buộc | High |
| **Uniqueness** | PK unique, không duplicate | High |
| **Accuracy** | Order total = sum(order_items) | High |
| **Timeliness** | Data có trong DW trước 8am T+1 | High |
| **Consistency** | Cùng customer_id giữa các bảng | High |
| **Validity** | Status chỉ có các giá trị cho phép | Medium |

---

## 6. KPIs & Metrics Definition

### 6.1 Revenue KPIs

```sql
-- Gross Revenue (Doanh thu gộp)
SUM(order_total) WHERE status NOT IN ('Cancelled', 'Refunded')

-- Net Revenue (Doanh thu thuần)
SUM(order_total - discount - refund_amount)

-- Average Order Value (AOV)
SUM(order_total) / COUNT(DISTINCT order_id)

-- Gross Margin %
(SUM(revenue) - SUM(cost)) / SUM(revenue) * 100
```

### 6.2 Customer KPIs

```sql
-- Customer Acquisition Cost (CAC)
Total Marketing Spend / New Customers

-- Customer Lifetime Value (CLV)
Avg Order Value * Purchase Frequency * Customer Lifespan

-- Repeat Purchase Rate
Customers with 2+ orders / Total Customers

-- Churn Rate
Customers không mua trong 90 ngày / Total Active Customers
```

### 6.3 RFM Scoring

```
RECENCY (R):
  5 = Mua trong 30 ngày
  4 = Mua trong 60 ngày
  3 = Mua trong 90 ngày
  2 = Mua trong 180 ngày
  1 = Mua > 180 ngày trước

FREQUENCY (F):
  5 = 10+ orders
  4 = 6-9 orders
  3 = 3-5 orders
  2 = 2 orders
  1 = 1 order

MONETARY (M):
  5 = Top 10%
  4 = Top 25%
  3 = Top 50%
  2 = Top 75%
  1 = Bottom 25%
```

### 6.4 Customer Segments

| Segment | RFM Score | Description | Action |
|---------|-----------|-------------|--------|
| **Champions** | R=5, F≥4, M≥4 | Best customers | Reward, Upsell |
| **Loyal** | R≥3, F≥3, M≥3 | Regular buyers | Loyalty program |
| **Potential** | R≥4, F=1-2, M≥3 | Recent, high value | Convert to loyal |
| **At Risk** | R=2-3, F≥3, M≥3 | Was good, slipping | Re-engage campaign |
| **Hibernating** | R=1-2, F=1-2, M=any | Long time no buy | Win-back campaign |
| **New** | R=5, F=1, M=any | Just acquired | Welcome campaign |

---

## 7. Reporting Requirements

### 7.1 Dashboard Requirements

| Dashboard | Audience | Refresh | Key Visuals |
|-----------|----------|---------|-------------|
| **Executive KPI** | C-level | Daily | Revenue trend, YoY comparison |
| **Sales Performance** | Sales | Daily | Orders by status, channel |
| **Customer 360** | Marketing | Weekly | Segment distribution, RFM |
| **Reconciliation** | Finance | Daily | Mismatch alerts, totals |
| **Data Quality** | DE/QC | Daily | Rule pass/fail, trends |

### 7.2 Report Requirements

| Report | Frequency | Recipient | Format |
|--------|-----------|-----------|--------|
| Daily Revenue Summary | Daily 8am | CFO, Sales | Email + Dashboard |
| Weekly Customer Report | Monday | Marketing | PDF |
| Monthly Business Review | 5th of month | All Directors | PPT |
| Reconciliation Alert | Real-time | Accounting | Slack/Email |

---

## 8. Non-Functional Requirements

### 8.1 Performance

| Metric | Requirement |
|--------|-------------|
| Dashboard load time | < 5 seconds |
| Daily ETL completion | Before 8am |
| Query response (simple) | < 2 seconds |
| Query response (complex) | < 30 seconds |

### 8.2 Security

- Data encryption at rest and in transit
- Role-based access control (RBAC)
- PII masking for non-authorized users
- Audit logging for sensitive data access

### 8.3 Availability

- 99.5% uptime for dashboards (business hours)
- RPO (Recovery Point Objective): 24 hours
- RTO (Recovery Time Objective): 4 hours

---

## 9. Assumptions & Constraints

### 9.1 Assumptions

1. Data source systems are stable and accessible
2. Historical data for 1 year is available
3. No real-time requirements (batch is acceptable)
4. Single currency (VND)
5. Single timezone (UTC+7)

### 9.2 Constraints

1. Limited budget - use open-source tools where possible
2. Small team (1 DE, 1 QC)
3. Timeline: 4 sprints (~8 weeks)
4. Infrastructure: Local Docker / Cloud free tier

### 9.3 Dependencies

1. Source database schema must be finalized
2. Payment gateway API documentation
3. Business sign-off on KPI definitions
4. Access to production-like sample data

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **AOV** | Average Order Value - Giá trị đơn hàng trung bình |
| **CLV/LTV** | Customer Lifetime Value - Giá trị vòng đời khách hàng |
| **RFM** | Recency, Frequency, Monetary - Phương pháp phân khúc KH |
| **Churn** | Khách hàng ngừng mua hàng |
| **Reconciliation** | Đối soát - so khớp số liệu giữa các hệ thống |
| **OLTP** | Online Transaction Processing - Hệ thống giao dịch |
| **DW** | Data Warehouse - Kho dữ liệu phân tích |
| **ETL** | Extract, Transform, Load - Quy trình xử lý dữ liệu |
| **PII** | Personally Identifiable Information - Thông tin cá nhân |

---

> 📝 **Note**: Document này cần được review và approve bởi stakeholders trước khi bắt đầu implementation.
