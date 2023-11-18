from airflow import DAG
from datetime import datetime
from airflow.operators.python_operator import PythonOperator
from src.pipelines.workloads.training.workload import step_1_train, step_2_validate


def end_marker(context):
    from src.pipelines.instrumentation import create_marker
    create_marker("end", f"training/airflow/{context['run_id']}")


with DAG(
    dag_id="training",
    start_date=datetime(2021, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
        ) as dag:
    train = PythonOperator(
        task_id="train",
        python_callable=step_1_train,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tool": "airflow",
        },
    )
    validate = PythonOperator(
        task_id="validate",
        python_callable=step_2_validate,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tool": "airflow",
        },
        on_success_callback=[end_marker],
    )
    train >> validate
