from airflow import DAG
from datetime import datetime
from airflow.operators.python_operator import PythonOperator
from src.pipelines.instrumentation import TelemetryManager
from src.pipelines.workloads.captioning.workload import load_models, generate_captions, save_captions
from src.pipelines.utils import S3ImageLoader, to_s3, from_s3


def start(run_id, tm):
    tm.setup(run_id=run_id, step_id="start")
    with tm.tracer.start_as_current_span("start"):
        print("Starting experiment")
        print("Loading models")
        model, image_processor, tokenizer \
            = load_models()
        to_s3(model, f"experiment/{tm.experiment_id}/{tm.tool}/model")
        to_s3(image_processor, f"experiment/{tm.experiment_id}/{tm.tool}/image_processor")
        to_s3(tokenizer, f"experiment/{tm.experiment_id}/{tm.tool}/tokenizer")
    tm.shutdown()


def inference(run_id, tm):
    tm.setup(run_id=run_id, step_id="inference")
    with tm.tracer.start_as_current_span("inference"):
        model = from_s3(f"experiment/{tm.experiment_id}/{tm.tool}/model")
        image_processor = from_s3(f"experiment/{tm.experiment_id}/{tm.tool}/image_processor")
        tokenizer = from_s3(f"experiment/{tm.experiment_id}/{tm.tool}/tokenizer")
        image_loader = S3ImageLoader(
            bucket_name="bstuart-masters-project-dataset",
            key_prefix='images/objects-in-the-lab/images/',
            max_keys=20
        )
        captions = generate_captions(
            image_loader,
            model,
            image_processor,
            tokenizer)
        to_s3(captions, f"experiment/{tm.experiment_id}/{tm.tool}/captions")
    tm.shutdown()


def end(run_id, tm, captions):
    tm.setup(run_id=run_id, step_id="end")
    with tm.tracer.start_as_current_span("end"):
        captions = from_s3(f"experiment/{tm.experiment_id}/{tm.tool}/captions")
        save_captions(captions)
    tm.shutdown()


tm = TelemetryManager(tool="airflow", experiment_id="image-captioning")


with DAG(
    dag_id="image-captioning",
    start_date=datetime(2021, 1, 1),
    schedule_interval=None,  # Externally triggered
        ) as dag:
    start = PythonOperator(
        task_id="start",
        python_callable=start,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tm": tm,
        },
        params={
            "run_id": "0",
        },
    )
    inference = PythonOperator(
        task_id="inference",
        python_callable=inference,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tm": tm,
            "model": "{{ model }}",
            "image_processor": "{{ image_processor }}",
            "tokenizer": "{{ tokenizer }}",
        },
    )
    end = PythonOperator(
        task_id="end",
        python_callable=end,
        op_kwargs={
            "run_id": "{{ run_id }}",
            "tm": tm,
            "captions": "{{ captions }}",
        },
    )
    start >> inference >> end