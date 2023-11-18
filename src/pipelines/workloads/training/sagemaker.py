import sagemaker
import boto3
import argparse
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import TrainingStep
from sagemaker.pytorch.estimator import PyTorch
from src.pipelines.instrumentation import create_marker

experiment_id = "training"
account_id = boto3.client("sts").get_caller_identity()["Account"]
role = f"arn:aws:iam::{account_id}:role/sm-workflow"
region = boto3.session.Session().region_name
sagemaker_session = sagemaker.session.Session()
sagemaker_image = f"{account_id}.dkr.ecr.{region}.amazonaws.com/benchoncy-devops-masters-project/sagemaker-training:latest"


def make_step(name, step, depends_on=[], run_id=0):
    estimator = PyTorch(
        image_uri=sagemaker_image,
        entry_point=f"src/pipelines/workloads/{experiment_id}/step_{step}.py",
        role=role,
        instance_count=1,
        instance_type="ml.m5.large",  # 2 vCPU + 8 GiB
        volume_size=30,
        sagemaker_session=sagemaker_session,
        hyperparameters={
            "run-id": str(run_id),
        },
    )
    return TrainingStep(
        name=name,
        estimator=estimator,
        depends_on=depends_on,
        inputs={},  # No inputs
    )


def build_pipeline(run_id):
    step_1 = make_step("train", 1, run_id=run_id)
    step_2 = make_step("validate", 2, depends_on=[step_1], run_id=run_id)

    pipeline = Pipeline(
        name="{}-pipeline".format(experiment_id),
        steps=[step_1, step_2],
        sagemaker_session=sagemaker_session,
    )
    pipeline.upsert(
        role_arn=role,
        parallelism_config={"MaxParallelExecutionSteps": 1},
    )
    return pipeline


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--run-id", type=int, default=0)
    args = args.parse_args()
    print("RunId: {}".format(args.run_id))
    print("Uploading pipeline definition")
    pipeline = build_pipeline(args.run_id)
    print("Starting pipeline")
    create_marker("start", f"{experiment_id}/sagemaker/{args.run_id}")
    execution = pipeline.start()
    print("Waiting for pipeline to finish")
    execution.wait()
    print("Pipeline execution finished")
