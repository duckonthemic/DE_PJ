"""
Application settings and configuration management
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Enterprise Analytics Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Database - Source (OLTP)
    source_db_host: str = "localhost"
    source_db_port: int = 5432
    source_db_name: str = "ecommerce_source"
    source_db_user: str = "postgres"
    source_db_password: str = "postgres"
    
    # Database - Data Warehouse
    dw_db_host: str = "localhost"
    dw_db_port: int = 5433
    dw_db_name: str = "data_warehouse"
    dw_db_user: str = "postgres"
    dw_db_password: str = "postgres"
    
    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_raw: str = "raw"
    minio_bucket_staging: str = "staging"
    minio_bucket_processed: str = "processed"
    
    # Airflow
    airflow_home: str = "./airflow"
    
    # Paths
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = Field(default=None)
    logs_dir: Path = Field(default=None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.data_dir is None:
            self.data_dir = self.project_root / "data"
        if self.logs_dir is None:
            self.logs_dir = self.project_root / "logs"
    
    @property
    def source_db_url(self) -> str:
        """Get source database connection URL"""
        return f"postgresql://{self.source_db_user}:{self.source_db_password}@{self.source_db_host}:{self.source_db_port}/{self.source_db_name}"
    
    @property
    def dw_db_url(self) -> str:
        """Get data warehouse connection URL"""
        return f"postgresql://{self.dw_db_user}:{self.dw_db_password}@{self.dw_db_host}:{self.dw_db_port}/{self.dw_db_name}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
