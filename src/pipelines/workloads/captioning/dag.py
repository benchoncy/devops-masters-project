from airflow import DAG
from datetime import datetime
from airflow.operators.python_operator import PythonOperator
from src.pipelines.workloads.captioning.workload import step_1_load, step_2_inference


with DAG(
    dag_id="image-captioning",
    start_date=datetime(2021, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
        ) as dag:
    start = PythonOperator(
        task_id="start",
        python_callable=step_1_load,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tool": "airflow",
        },
    )
    inference = PythonOperator(
        task_id="inference",
        python_callable=step_2_inference,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tool": "airflow",
        },
    )
    start >> inference
