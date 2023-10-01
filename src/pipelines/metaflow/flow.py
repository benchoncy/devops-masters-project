from metaflow import FlowSpec, step
from instrumentation import setup_traces

EXPERIMENT_ID = "image-captioning"
tracer = setup_traces(experiment_id=EXPERIMENT_ID)


@tracer.start_as_current_span("main")
class ExperimentFlow(FlowSpec):
    @tracer.start_as_current_span("start")
    @step
    def start(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="start",
        )
        self.next(self.dataset_perperation)

    @tracer.start_as_current_span("dataset_perperation")
    @step
    def dataset_perperation(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="dataset_perperation",
        )
        self.next(self.inference)

    @tracer.start_as_current_span("inference")
    @step
    def inference(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="inference",
        )
        self.next(self.end)

    @tracer.start_as_current_span("end")
    @step
    def end(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="end",
        )


if __name__ == "__main__":
    ExperimentFlow()
