"""
DW ETL DAG - Data Warehouse ETL Pipeline
Orchestrates the full ETL flow: Dimensions -> Facts -> Reconciliation -> Customer 360
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator


default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def load_dimensions():
    """Load all dimension tables."""
    import sys
    sys.path.insert(0, '/app')
    from src.transform.load_dimensions import DimensionLoader, get_source_engine, get_dw_engine
    
    loader = DimensionLoader(get_source_engine(), get_dw_engine())
    loader.run()


def load_facts():
    """Load all fact tables."""
    import sys
    sys.path.insert(0, '/app')
    from src.transform.load_facts import FactLoader, get_source_engine, get_dw_engine
    
    loader = FactLoader(get_source_engine(), get_dw_engine())
    loader.run()


def load_reconciliation():
    """Build reconciliation table."""
    import sys
    sys.path.insert(0, '/app')
    from src.transform.load_reconciliation import ReconciliationLoader, get_source_engine, get_dw_engine
    
    loader = ReconciliationLoader(get_source_engine(), get_dw_engine())
    loader.run()


def build_customer360():
    """Build Customer 360 mart."""
    import sys
    sys.path.insert(0, '/app')
    from src.transform.load_customer360 import Customer360Loader, get_dw_engine
    
    loader = Customer360Loader(get_dw_engine())
    loader.run()


with DAG(
    'dw_etl_pipeline',
    default_args=default_args,
    description='Data Warehouse ETL Pipeline',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['etl', 'dw', 'production'],
) as dag:
    
    # Task 1: Load Dimensions
    task_load_dims = PythonOperator(
        task_id='load_dimensions',
        python_callable=load_dimensions,
    )
    
    # Task 2: Load Facts (depends on dimensions)
    task_load_facts = PythonOperator(
        task_id='load_facts',
        python_callable=load_facts,
    )
    
    # Task 3: Build Reconciliation (depends on facts)
    task_reconcile = PythonOperator(
        task_id='load_reconciliation',
        python_callable=load_reconciliation,
    )
    
    # Task 4: Build Customer 360 (depends on facts)
    task_customer360 = PythonOperator(
        task_id='build_customer360',
        python_callable=build_customer360,
    )
    
    # Define task dependencies
    # Dimensions -> Facts -> [Reconciliation, Customer360] (parallel)
    task_load_dims >> task_load_facts >> [task_reconcile, task_customer360]
