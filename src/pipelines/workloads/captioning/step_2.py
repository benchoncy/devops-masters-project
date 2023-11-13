from src.pipelines.workloads.captioning.workload import step_2_inference
import argparse

args = argparse.ArgumentParser()
args.add_argument("--run-id", type=int, default=0)
args = args.parse_args()

step_2_inference(tool="sagemaker", run_id=args.run_id)
