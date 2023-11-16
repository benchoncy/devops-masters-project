from metaflow import FlowSpec, step, Parameter, resources


class ExperimentFlow(FlowSpec):

    run_id = Parameter('run_id', help='Run ID')

    @resources(cpu=2, memory=8000)
    @step
    def start(self):
        from src.pipelines.workloads.captioning.workload import step_1_load
        step_1_load(tool="metaflow_batch", run_id=self.run_id)
        self.next(self.end)

    @resources(cpu=2, memory=8000)
    @step
    def end(self):
        from src.pipelines.workloads.captioning.workload import step_2_inference
        step_2_inference(tool="metaflow_batch", run_id=self.run_id)


if __name__ == "__main__":
    ExperimentFlow()
