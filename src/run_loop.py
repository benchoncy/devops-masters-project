import fire
import os
from src.pipelines.instrumentation import create_marker


def kube_exec_airflow(command):
    web_pod = os.popen("kubectl get pods -n airflow | grep web | awk '{print $1}'").read().strip()
    output = os.popen(f"kubectl exec -n airflow {web_pod} -- {command}").read()
    return output


class Runner:
    def metaflow(self, experiment, start=0, iterations=None):
        index = start
        while index < (start+iterations) if iterations else True:
            run_id = index
            command = f"python -m src.pipelines.workloads.{experiment}.flow " \
                      f"run --with kubernetes --run_id {run_id}"
            create_marker("start", f"{experiment}/metaflow/{run_id}")
            os.system(command)
            create_marker("end", f"{experiment}/metaflow/{run_id}")
            index += 1

    def airflow(self, experiment, start=0, iterations=None):
        kube_exec_airflow(f"airflow dags unpause {experiment}")
        index = start
        while index < (start+iterations) if iterations else True:
            run_id = index
            create_marker("start", f"{experiment}/airflow/{run_id}")
            kube_exec_airflow(f"airflow dags trigger {experiment} --run-id {run_id}")
            running = True
            state = "queued"
            while running:
                output = kube_exec_airflow(f"airflow dags list-runs --dag-id {experiment} --state {state}").strip()
                if output == "No data found":
                    if state == "queued":
                        state = "running"
                    else:
                        running = False
            index += 1

    def sagemaker(self, experiment, start=0, iterations=None):
        index = start
        while index < (start+iterations) if iterations else True:
            run_id = index
            command = f"python -m src.pipelines.workloads.{experiment}.sagemaker --run-id {run_id}"
            create_marker("start", f"{experiment}/sagemaker/{run_id}")
            os.system(command)
            create_marker("end", f"{experiment}/sagemaker/{run_id}")
            index += 1


if __name__ == '__main__':
    fire.Fire(Runner)
