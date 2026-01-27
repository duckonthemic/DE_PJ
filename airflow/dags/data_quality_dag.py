"""
Data Quality DAG - Automated Data Quality Checks
Runs the data quality validator on a schedule.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 0,
}


def run_data_quality_checks():
    """Execute data quality validation."""
    import sys
    sys.path.insert(0, '/app')
    from src.data_quality.validator import run_validations
    
    success = run_validations()
    if not success:
        raise Exception("Data Quality Checks FAILED")


with DAG(
    'data_quality_checks',
    default_args=default_args,
    description='Automated Data Quality Validation',
    schedule_interval='0 6 * * *',  # Daily at 6 AM (after ETL)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['quality', 'validation', 'monitoring'],
) as dag:
    
    task_dq_check = PythonOperator(
        task_id='run_data_quality',
        python_callable=run_data_quality_checks,
    )
