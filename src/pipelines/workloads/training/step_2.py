from src.pipelines.workloads.training.workload import step_2_validate
import argparse

args = argparse.ArgumentParser()
args.add_argument("--run-id", type=int, default=0)
args = args.parse_args()

step_2_validate(tool="sagemaker", run_id=args.run_id)
