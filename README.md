# Enterprise Customer & Revenue Analytics Platform

## 🎯 Overview

Enterprise-grade analytics platform for customer insights and revenue reconciliation, featuring:

- **Data Warehouse Modernization**: Transform Excel/OLTP to modern DW/Lakehouse
- **Customer 360 & Marketing Analytics**: RFM, LTV, Customer Segmentation
- **Payment & Finance Reconciliation**: Order-Payment-ERP matching

## 📁 Project Structure

```
Enterperise_DE/
├── 📂 airflow/                    # Airflow DAGs & configurations
│   ├── dags/                      # DAG definitions
│   ├── plugins/                   # Custom operators & hooks
│   └── config/                    # Airflow configuration
│
├── 📂 config/                     # Global configurations
│   ├── database.yaml              # Database connections
│   ├── data_quality.yaml          # DQ rules configuration
│   └── logging.yaml               # Logging configuration
│
├── 📂 data/                       # Data storage (gitignored)
│   ├── raw/                       # Raw data from sources
│   ├── staging/                   # Staging/Bronze layer
│   ├── processed/                 # Silver/processed data
│   └── gold/                      # Gold/mart layer
│
├── 📂 dbt/                        # dbt project
│   ├── models/                    # dbt models
│   │   ├── staging/               # Staging models
│   │   ├── warehouse/             # DW core models
│   │   └── marts/                 # Data marts
│   ├── seeds/                     # Seed data
│   ├── tests/                     # dbt tests
│   └── macros/                    # Custom macros
│
├── 📂 docker/                     # Docker configurations
│   ├── postgres/                  # PostgreSQL setup
│   ├── airflow/                   # Airflow setup
│   ├── metabase/                  # Metabase setup
│   └── minio/                     # MinIO setup
│
├── 📂 docs/                       # Documentation
│   ├── architecture/              # Architecture diagrams
│   ├── business_requirements/     # Business requirements
│   ├── data_dictionary/           # Data dictionary
│   └── test_reports/              # Test reports
│
├── 📂 great_expectations/         # Great Expectations project
│   ├── expectations/              # Expectation suites
│   ├── checkpoints/               # Validation checkpoints
│   └── plugins/                   # Custom expectations
│
├── 📂 notebooks/                  # Jupyter notebooks
│   ├── exploration/               # Data exploration
│   ├── analysis/                  # Analysis notebooks
│   └── prototyping/               # Prototyping
│
├── 📂 plan/                       # Project planning
│   └── Plan_Checklist.md          # Sprint checklist
│
├── 📂 scripts/                    # Utility scripts
│   ├── data_generation/           # Data generation scripts
│   ├── database/                  # Database setup scripts
│   └── utils/                     # Helper utilities
│
├── 📂 src/                        # Main source code
│   ├── __init__.py
│   ├── config/                    # Configuration management
│   ├── connectors/                # Database/API connectors
│   ├── data_quality/              # DQ validation logic
│   ├── etl/                       # ETL pipelines
│   ├── models/                    # Data models (Pydantic)
│   ├── reconciliation/            # Reconciliation logic
│   └── utils/                     # Utilities
│
├── 📂 tests/                      # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── e2e/                       # End-to-end tests
│   └── data_quality/              # Data quality tests
│
├── 📄 .env.example                # Environment variables template
├── 📄 .gitignore                  # Git ignore rules
├── 📄 docker-compose.yml          # Docker compose
├── 📄 Makefile                    # Make commands
├── 📄 pyproject.toml              # Python project config
├── 📄 README.md                   # This file
└── 📄 requirements.txt            # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

### Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd Enterperise_DE

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
copy .env.example .env

# 5. Start infrastructure
docker-compose up -d

# 6. Initialize databases
python scripts/database/init_db.py
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Sources                                 │
├────────────┬────────────┬────────────┬────────────┬────────────────┤
│  E-commerce│  Payment   │    ERP/    │  Marketing │   External     │
│   Database │  Gateway   │ Accounting │  Channels  │     APIs       │
└─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┴───────┬────────┘
      │            │            │            │              │
      └────────────┴────────────┴────────────┴──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Ingestion Layer (Airflow)                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Bronze/Staging Layer (MinIO/S3 - Parquet)              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Transform Layer (dbt + SQL)                      │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Silver/DW Core (PostgreSQL - Star Schema)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │dim_cust  │ │dim_prod  │ │dim_date  │ │fact_order│ │fact_pay  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Gold/Mart Layer                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐          │
│  │mart_customer360│ │ mart_rfm_seg   │ │mart_reconcile  │          │
│  └────────────────┘ └────────────────┘ └────────────────┘          │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   BI / Visualization (Metabase)                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Source Database** | PostgreSQL |
| **Data Lake** | MinIO (S3-compatible) |
| **File Format** | Parquet |
| **Orchestration** | Apache Airflow |
| **Transformation** | dbt |
| **Data Quality** | Great Expectations, Soda, dbt tests |
| **BI/Dashboard** | Metabase |
| **Testing** | pytest, Great Expectations |
| **CI/CD** | GitHub Actions |
| **Containerization** | Docker, Docker Compose |

## 📅 Sprint Roadmap

- **Sprint 1**: Data Sources & Staging Layer
- **Sprint 2**: Data Warehouse Core & Reconciliation
- **Sprint 3**: Customer 360 & Marketing Analytics
- **Sprint 4**: Data Quality, Monitoring & Portfolio

## 📖 Documentation

- [Business Requirements](docs/business_requirements/)
- [Architecture Design](docs/architecture/)
- [Data Dictionary](docs/data_dictionary/)
- [Test Reports](docs/test_reports/)

## 👥 Team

- **Data Engineer**: Pipeline, DW, ETL/ELT
- **QC/QA Engineer**: Test Strategy, Data Quality, Automation

## 📝 License

MIT License
