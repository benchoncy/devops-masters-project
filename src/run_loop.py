import fire
import os
from src.pipelines.instrumentation import create_marker


class Runner:
    def metaflow(self, iterations, command, experiment, start=0):
        for run_id in range(start, (start+iterations)):
            create_marker("start", f"{experiment}/metaflow/{run_id}")
            os.system(command+" --run_id "+str(run_id))
            create_marker("end", f"{experiment}/metaflow/{run_id}")


if __name__ == '__main__':
    fire.Fire(Runner)
