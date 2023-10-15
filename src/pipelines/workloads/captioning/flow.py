from metaflow import FlowSpec, step
from instrumentation import setup_traces

EXPERIMENT_ID = "image-captioning"
tracer = setup_traces(experiment_id=EXPERIMENT_ID)


@tracer.start_as_current_span("0--main")
class ExperimentFlow(FlowSpec):
    @tracer.start_as_current_span("1--start")
    @step
    def start(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="start",
        )
        self.next(self.dataset_perperation)

    @tracer.start_as_current_span("2--dataset_perperation")
    @step
    def dataset_perperation(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="dataset_perperation",
        )
        self.next(self.inference)

    @tracer.start_as_current_span("3--inference")
    @step
    def inference(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="inference",
        )
        self.next(self.end)

    @tracer.start_as_current_span("4--end")
    @step
    def end(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="end",
        )


if __name__ == "__main__":
    ExperimentFlow()
