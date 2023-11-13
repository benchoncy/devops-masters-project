from src.pipelines.workloads.captioning.workload import step_1_load
import argparse

args = argparse.ArgumentParser()
args.add_argument("--run-id", type=int, default=0)
args = args.parse_args()

step_1_load(tool="sagemaker", run_id=args.run_id)
