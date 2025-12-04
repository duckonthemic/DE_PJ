# Enterprise Customer & Revenue Analytics Platform

## 1. Ý tưởng dự án

Dự án này mô phỏng một nền tảng phân tích khách hàng và doanh thu ở cấp độ doanh nghiệp, kết hợp ba bài toán thường gặp trong thực tế:

1. **Hiện đại hóa hệ thống báo cáo (Data Warehouse Modernization)**: chuyển từ Excel/OLTP sang Data Warehouse/Lakehouse chuẩn.  
2. **Xây dựng Customer 360 & Marketing Analytics**: hợp nhất dữ liệu khách hàng, đơn hàng, kênh marketing để phân tích hành vi, RFM, LTV, phân khúc khách hàng.  
3. **Payment & Finance Reconciliation**: đối soát giao dịch giữa hệ thống Order, cổng thanh toán và hệ thống kế toán/ERP để phát hiện chênh lệch, thất thoát doanh thu.

Dự án được thiết kế để hai vai trò cùng tham gia:

- **Data Engineer**: chịu trách nhiệm kiến trúc dữ liệu, pipeline ETL/ELT, Data Warehouse/Lakehouse, data mart và tích hợp data quality.
- **QC/QA Engineer (Data & Analytics)**: thiết kế chiến lược test, viết test case & automation cho data pipeline, data quality, validation logic và báo cáo.

Mục tiêu là tạo ra một sản phẩm đủ phức tạp, sát với bối cảnh doanh nghiệp, có thể trình bày với nhà tuyển dụng như một dự án thực chiến.

---

## 2. Technical skill

### 2.1. Data Engineer

- Thiết kế mô hình dữ liệu OLTP và Data Warehouse (star schema, SCD, fact/dimension).
- Xây dựng pipeline ETL/ELT (batch & incremental) với SQL/dbt/Airflow hoặc tương đương.
- Tích hợp dữ liệu từ nhiều nguồn: database giao dịch, file CSV/Excel, API/payment gateway, ERP.
- Làm việc với Data Lake/Lakehouse (parquet, Iceberg/Delta/Hudi trên S3/MinIO).
- Tối ưu truy vấn và mô hình (partitioning, indexing, materialized view).
- Thiết kế và triển khai data mart cho Customer 360, RFM, LTV, segmentation.
- Áp dụng data quality vào pipeline (rule-based check, schema validation, test automation).
- Thiết lập CI/CD cơ bản cho data project (Git, GitHub/GitLab CI, chạy test tự động).

### 2.2. QC/QA Engineer (Data & Analytics)

- Thiết kế Test Strategy/Test Plan cho hệ thống Data Warehouse & Analytics (không chỉ web app).
- SQL testing: kiểm tra data mapping, row count, aggregation (SUM, AVG, COUNT) giữa nguồn và DW/mart.
- Thiết kế test case cho business rule: RFM, phân khúc khách hàng, reconciliation logic.
- Thiết kế và chạy data quality test: null check, range check, uniqueness, referential integrity, schema drift.
- API testing (nếu có ingestion/serving API) bằng Postman/Newman hoặc tool tương đương.
- Regression testing khi DE thay đổi logic transform, mô hình dữ liệu hoặc schema.
- Tự động hóa test: dùng pytest/dbt tests/Great Expectations hoặc framework tương đương.
- Viết Test Report/Test Summary, phân loại mức độ nghiêm trọng (severity/priority) cho lỗi liên quan đến doanh thu & báo cáo.

---

## 3. Kết quả mong muốn (Deliverables cấp dự án)

- **Kiến trúc tổng thể hệ thống (diagram)** bao gồm: nguồn dữ liệu, tầng staging, Data Warehouse/Lakehouse, mart Customer 360, reconciliation, BI/Reporting, data quality & monitoring.
- **Cơ sở dữ liệu nguồn (OLTP)** mô phỏng hệ thống e-commerce: bảng `customers`, `products`, `orders`, `order_items`; dữ liệu payment gateway; dữ liệu kế toán/ERP đơn giản.
- **Data Warehouse core** với các bảng fact/dimension chuẩn hóa (ví dụ: `dim_customer`, `dim_product`, `dim_date`, `dim_channel`, `fact_orderline`, `fact_payment`, `fact_invoice`, `fact_reconciliation`).
- **Customer 360 & Marketing Analytics mart**: bảng `mart_customer_360`, bảng RFM, bảng segmentation, bảng LTV,…
- **Bộ logic đối soát (reconciliation)** giữa order – payment – ERP với báo cáo chênh lệch.
- **Bộ dashboard** (Metabase/Power BI/Looker Studio hoặc tương đương) cho:
  - KPI doanh thu.
  - Customer 360.
  - Tình trạng reconciliation.
  - Chất lượng dữ liệu.
- **Bộ test (manual + automation)** cho toàn bộ pipeline và các mart quan trọng, bao gồm test case, test script, test data và test report.
- **Repository (GitHub)** có cấu trúc rõ ràng, README chi tiết, có thể gửi trực tiếp cho nhà tuyển dụng.

---

## 4. Roadmap triển khai theo Sprint

Dự án được chia thành **4 Sprint chính**. Thời lượng mỗi Sprint có thể linh hoạt (1–2 tuần), nhưng cấu trúc được thiết kế để vừa thể hiện chiều sâu kỹ thuật vừa có output hữu hình cho portfolio.

### 4.1. Tổng quan các Sprint

| Sprint    | Mục tiêu chính                                                                      | Deliverable chính                                                                                                                                                         |
|----------|--------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Sprint 1 | Thiết lập nguồn dữ liệu & tầng staging, thống nhất yêu cầu & kiến trúc.             | Schema nguồn, dữ liệu giả lập, kiến trúc high-level, data staging/bronze layer, Test Strategy v1.                                                                        |
| Sprint 2 | Xây Data Warehouse core & lớp reconciliation cơ bản.                                 | Star schema, fact/dim core, pipeline ETL/ELT, báo cáo đối soát phiên bản đầu tiên, test mapping & reconciliation.                                                       |
| Sprint 3 | Xây Customer 360 & Marketing Analytics mart + dashboard.                             | `mart_customer_360`, bảng RFM/segment, dashboard KPI & Customer 360, test logic business & dữ liệu dashboard.                                                           |
| Sprint 4 | Hoàn thiện data quality, monitoring, CI/CD & đóng gói portfolio.                    | Data quality framework, test automation & CI, monitoring căn bản, tài liệu & demo tổng thể.                                                                             |

---

### 4.2. Sprint 1 – Nguồn dữ liệu & Tầng Staging

#### Mục tiêu

- Hiểu rõ yêu cầu nghiệp vụ và kịch bản phân tích khách hàng & doanh thu.
- Thiết kế schema nguồn (OLTP) cho hệ thống e-commerce mô phỏng.
- Tạo dữ liệu giả lập đủ phong phú cho customers, products, orders, payments, accounting.
- Thiết lập pipeline ingest dữ liệu vào tầng staging/bronze.
- Xây dựng Test Strategy và bộ test case cơ bản cho ingestion & staging.

#### Output kỳ vọng

- Tài liệu mô tả bối cảnh nghiệp vụ, use case chính và câu hỏi phân tích mục tiêu (**Business Requirement & Analytics Questions**).
- **ERD hoặc schema design** cho hệ thống nguồn (`customers`, `products`, `orders`, `order_items`, `payments`, `gl/ERP`).
- Script sinh dữ liệu giả (Python, SQL, tool bất kỳ) với tối thiểu vài tháng tới 1 năm dữ liệu.
- Tầng **staging/bronze** trong Data Lake/Lakehouse chứa dữ liệu đã ingest từ nguồn (file/database).
- Tài liệu **Kiến trúc tổng thể (phiên bản 1)** ở mức high-level (diagram).
- **Test Strategy v1** cho dự án, bao gồm phạm vi test, loại test, môi trường, tool sử dụng.
- Danh sách **test case** và **kết quả test** cho Sprint 1 (Ingestion & Staging).

#### Checklist công việc – Data Engineer

- [ ] Phân tích yêu cầu nghiệp vụ cùng QC/QA và ghi lại Business Requirement & Analytics Questions.
- [ ] Thiết kế schema nguồn cho hệ thống e-commerce (bao gồm key, constraint, index cơ bản).
- [ ] Cài đặt DB nguồn (PostgreSQL/MySQL) hoặc mock service tương đương.
- [ ] Viết script sinh dữ liệu giả cho `customers`, `products`, `orders`, `order_items`, `payments`, `accounting`.
- [ ] Thiết lập Data Lake/Lakehouse (folder structure, format parquet/csv,…).
- [ ] Xây dựng pipeline ingest dữ liệu từ nguồn vào staging/bronze (ví dụ: Airflow job, Python script, dbt seed,…).
- [ ] Lưu lại cấu hình, lệnh chạy và hướng dẫn trong README (mục **Setup & Run**).

#### Checklist công việc – QC/QA Engineer

- [ ] Tham gia workshop thu thập yêu cầu, viết lại tài liệu Business Requirement & scope test.
- [ ] Soạn **Test Strategy v1** cho dự án (mục tiêu test, phạm vi, môi trường, loại test, tool, trách nhiệm).
- [ ] Thiết kế test case cho schema nguồn: kiểm tra primary key, foreign key, not null, constraint cơ bản.
- [ ] Thiết kế test case cho ingestion vào staging: so sánh row count giữa nguồn và staging, kiểm tra type/format của cột chính.
- [ ] Tìm và ghi nhận các issue dữ liệu ban đầu (null bất thường, format sai, thiếu constraint) – tạo **defect log**.
- [ ] Viết **Test Report ngắn** cuối Sprint 1 (đã test gì, phát hiện gì, risk còn lại).

---

### 4.3. Sprint 2 – Data Warehouse Core & Reconciliation cơ bản

#### Mục tiêu

- Thiết kế và triển khai **star schema** cho Data Warehouse core.
- Xây dựng pipeline ETL/ELT từ staging/bronze sang DW core (fact/dim).
- Thiết lập logic reconciliation cơ bản giữa order – payment – ERP.
- Thiết kế và chạy test cho data mapping, số liệu tổng hợp và đối soát.

#### Output kỳ vọng

- Tài liệu mô hình dữ liệu Data Warehouse (dimension & fact, sơ đồ star schema).
- Các bảng dimension: `dim_customer`, `dim_product`, `dim_date`, `dim_channel`,…
- Các bảng fact core: `fact_orderline`, `fact_payment`, `fact_invoice`,…
- Job ETL/ELT (Airflow/dbt/SQL script) load dữ liệu từ staging sang DW core (incremental hoặc full load).
- Bảng hoặc view `fact_reconciliation` với logic matching cơ bản (order vs payment vs invoice).
- Bộ test case & script kiểm tra mapping, row count, aggregation và reconciliation.
- **Test Report Sprint 2** (bao gồm kết quả test đối soát, lỗi phát hiện, đề xuất cải tiến).

#### Checklist công việc – Data Engineer

- [ ] Thiết kế star schema dựa trên yêu cầu phân tích và dữ liệu staging.
- [ ] Tạo script/migration để build các bảng dim và fact trong DW.
- [ ] Viết transform (SQL/dbt/Airflow) cho việc load dữ liệu từ staging → DW core (bao gồm incremental logic nếu có).
- [ ] Thiết kế và triển khai logic reconciliation cơ bản (join key, rule matching, xử lý unmatched record).
- [ ] Tối thiểu tạo 1–2 view/report SQL cho đối soát tổng quát (số đơn, tổng amount theo hệ thống).
- [ ] Cập nhật README và tài liệu kiến trúc với phần DW core & reconciliation.

#### Checklist công việc – QC/QA Engineer

- [ ] Review tài liệu star schema & mapping từ staging → DW core, xác nhận với DE & business (nếu có).
- [ ] Thiết kế test case cho mapping từng bảng dim/fact: kiểm tra row count, key mapping, giá trị quan trọng.
- [ ] Thiết kế test case cho reconciliation: so sánh tổng số tiền, số giao dịch giữa order – payment – ERP theo ngày/tháng.
- [ ] Viết SQL test/query để kiểm tra các trường hợp mismatch (order chưa có payment, payment không có order, invoice lệch amount,…).
- [ ] Thực thi test, ghi nhận defect và working session với DE để chỉnh sửa logic.
- [ ] Cập nhật **Test Report Sprint 2**, highlight các lỗi ảnh hưởng doanh thu/KPI và mức độ ưu tiên.

---

### 4.4. Sprint 3 – Customer 360 & Marketing Analytics

#### Mục tiêu

- Xây dựng **mart Customer 360** dựa trên DW core.
- Tính toán **RFM**, phân khúc khách hàng, **LTV** hoặc các metric marketing khác.
- Thiết kế dashboard cho KPI doanh thu & Customer 360.
- Thiết lập và kiểm thử logic business cho phân tích khách hàng.

#### Output kỳ vọng

- Bảng `mart_customer_360` với thông tin định danh + hành vi mua sắm + kênh tương tác.
- Bảng/bộ logic **RFM** (Recency, Frequency, Monetary) + phân loại segment (VIP, Churning, New, Dormant,…).
- Bảng hoặc view **LTV (Lifetime Value)** cơ bản nếu đủ thời gian & dữ liệu.
- **Dashboards** (Metabase/Power BI/Looker Studio,…) cho:
  - Doanh thu theo thời gian, kênh, sản phẩm.
  - Tổng quan khách hàng, phân khúc, RFM.
  - (Tùy chọn) Tóm tắt chênh lệch reconciliation theo ngày/tháng.
- Tài liệu mô tả **logic business** cho RFM, segmentation, LTV và cách đọc dashboard.
- **Test case & Test Report** cho việc kiểm thử mart và dashboard.

#### Checklist công việc – Data Engineer

- [ ] Thiết kế mô hình dữ liệu cho `mart_customer_360` (cột, key, grain).
- [ ] Viết transform (SQL/dbt/ETL job) để build `mart_customer_360` từ DW core.
- [ ] Triển khai logic tính **RFM & segment** (SQL hoặc tool analytics).
- [ ] Triển khai logic **LTV** cơ bản nếu có (ví dụ dựa trên lịch sử đơn hàng).
- [ ] Kết nối DW/mart với công cụ BI (Metabase/Power BI/…) và xây dashboard chính.
- [ ] Tối ưu truy vấn nếu dashboard chậm (index, partition, aggregate table,…).
- [ ] Cập nhật tài liệu kiến trúc & README với phần Customer 360 & dashboard.

#### Checklist công việc – QC/QA Engineer

- [ ] Thiết kế test case cho `mart_customer_360`: kiểm tra tính đầy đủ, đúng và nhất quán của thông tin khách hàng.
- [ ] Tạo bộ **test data nhỏ (golden dataset)** và tính RFM/segment bằng Excel/SQL tay để đối chiếu với kết quả tự động.
- [ ] Kiểm thử logic phân khúc (segment assignment) với các case biên (khách mua một lần, khách in-active lâu ngày, khách mua rất nhiều,…).
- [ ] Kiểm tra tính đúng đắn của dashboard: số liệu trên dashboard phải khớp với truy vấn trực tiếp trên DB.
- [ ] Test usability & performance cơ bản của dashboard (filter theo thời gian/kênh/segment, độ trễ load,…).
- [ ] Cập nhật **Test Report Sprint 3**, highlight những issue liên quan đến insight sai lệch hoặc gây nhầm lẫn cho người dùng cuối.

---

### 4.5. Sprint 4 – Data Quality, Monitoring, CI/CD & Đóng gói Portfolio

#### Mục tiêu

- Tích hợp **data quality framework** vào pipeline (vd: dbt tests, Great Expectations, Soda,…).
- Thiết lập **CI/CD cơ bản** để chạy test tự động khi có thay đổi.
- Thiết kế **monitoring & alerting** đơn giản cho chất lượng dữ liệu và pipeline.
- Hoàn thiện tài liệu, script và demo để dùng làm **portfolio** cho nhà tuyển dụng.

#### Output kỳ vọng

- Bộ **rule data quality** được định nghĩa rõ ràng theo bảng (schema, uniqueness, null %, range,…).
- **Test automation** tích hợp vào pipeline (ví dụ: dbt test/pytest/Great Expectations chạy trước khi deploy).
- **CI pipeline** (GitHub Actions/GitLab CI) chạy lint + test + (tùy chọn) build doc.
- Dashboard/hoặc log cơ bản cho **monitoring chất lượng dữ liệu** (số rule pass/fail theo thời gian).
- Tài liệu **tổng hợp dự án**: kiến trúc, luồng dữ liệu, hướng dẫn chạy, hướng dẫn demo.
- Slide hoặc note mô tả cách **trình bày dự án với nhà tuyển dụng** (talk track).

#### Checklist công việc – Data Engineer

- [ ] Chọn và tích hợp framework data quality phù hợp (dbt tests/Great Expectations/Soda/…).
- [ ] Viết rule cho các bảng quan trọng: staging, DW core, `mart_customer_360`, `fact_reconciliation`.
- [ ] Thiết lập job chạy test tự động trong pipeline ETL/ELT.
- [ ] Tạo **pipeline CI** cơ bản: chạy unit test/data test khi push code (GitHub/GitLab CI).
- [ ] Thiết lập logging/monitoring mức tối thiểu (lưu kết quả test theo thời gian, log error).
- [ ] Chuẩn hóa lại cấu trúc repo, thêm README chi tiết và ví dụ lệnh chạy.
- [ ] Chuẩn bị script/demo scenario để trình bày end-to-end luồng dữ liệu.

#### Checklist công việc – QC/QA Engineer

- [ ] Cùng DE xác định danh sách bảng & cột quan trọng cần rule data quality chi tiết.
- [ ] Phân loại rule theo mức độ nghiêm trọng (blocker, major, minor) và ghi vào tài liệu.
- [ ] Review & đề xuất bổ sung rule dựa trên kinh nghiệm test và lỗi đã gặp ở các Sprint trước.
- [ ] Thiết kế test case & scenario cho **regression test end-to-end** (từ nguồn đến dashboard).
- [ ] Chạy regression test sau khi tích hợp CI & data quality framework, ghi nhận kết quả.
- [ ] Viết **Test Summary Report tổng dự án**: phạm vi đã test, lỗi đã phát hiện & xử lý, rủi ro còn lại, đề xuất cải tiến tương lai.
- [ ] Chuẩn bị vài slide/section riêng về cách **QC/QA đảm bảo chất lượng** cho dự án data phức tạp.
