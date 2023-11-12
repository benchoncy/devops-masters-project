import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep
from sagemaker.processing import Processor
from sagemaker.workflow.parameters import ParameterInteger
from sagemaker.workflow.parallelism_config import ParallelismConfiguration

experiment_id = "captioning"
sagemaker_session = sagemaker.session.Session()
role = sagemaker.get_execution_role()
sagemaker_image = ""


run_id = ParameterInteger(
    name="RunId",
    default_value=0,
)


def make_step(name, step, depends_on=[]):
    processor = Processor(
        image_uri=sagemaker_image,
        role=role,
        instance_count=1,
        instance_type="ml.m5.large",  # 2 vCPU + 8 GiB
        volume_size_in_gb=30,
        sagemaker_session=sagemaker_session,
    )
    return ProcessingStep(
        name=name,
        processor=processor,
        depends_on=depends_on,
        step_args=processor.run(
            code=f"src/pipelines/workloads/{experiment_id}/step_{step}.py",
            arguments=["--run-id", run_id],
        ),
    )


step_1 = make_step("load_models", 1)
step_2 = make_step("inference", 2, depends_on=[step_1])

pipeline = Pipeline(
    name="{}-pipeline".format(experiment_id),
    parameters=[run_id],
    steps=[step_1, step_2],
    sagemaker_session=sagemaker_session,
)


if __name__ == "__main__":
    pipeline.upsert(
        role_arn=role,
        parallelism_config=ParallelismConfiguration(
            max_parallel_execution_steps=1
        ),
    )
    execution = pipeline.start(
        parameters=dict(
            RunId=0,
        )
    )
    execution.wait()
