from airflow import DAG
from datetime import datetime
from airflow.operators.python_operator import PythonOperator


def task():
    print("Hello World!")


with DAG(
    dag_id="test-dag",
    start_date=datetime(2021, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
        ) as dag:
    start = PythonOperator(
        task_id="test-task",
        python_callable=task,
    )
