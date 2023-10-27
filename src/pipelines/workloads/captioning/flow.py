from metaflow import FlowSpec, step, Parameter
from .instrumentation import setup_traces
from .workload import load_models, generate_captions, save_captions
from src.pipelines.utils import S3ImageLoader
import os

TOOL = "metaflow"
EXPERIMENT_ID = "image-captioning"
RUN_ID = os.getenv("RUN_ID")
S3_BUCKET_NAME = ""

tracer, trace_provider = setup_traces(
    tool=TOOL,
    experiment_id=EXPERIMENT_ID,
    run_id=RUN_ID,
)


@tracer.start_as_current_span("0--main")
class ExperimentFlow(FlowSpec):

    inf = Parameter('inf', help='Number of inferences to run', default=10)

    @tracer.start_as_current_span("1--start")
    @step
    def start(self):
        from instrumentation import setup_metrics
        meter_provider = setup_metrics(
            tool=TOOL,
            experiment_id=EXPERIMENT_ID,
            run_id=RUN_ID,
            step_id="start",
        )
        self.model, self.image_processor, self.tokenizer \
            = load_models()
        meter_provider.shutdown()
        self.next(self.inference)

    @tracer.start_as_current_span("3--inference")
    @step
    def inference(self):
        from instrumentation import setup_metrics
        meter_provider = setup_metrics(
            tool=TOOL,
            experiment_id=EXPERIMENT_ID,
            run_id=RUN_ID,
            step_id="inference",
        )
        image_loader = S3ImageLoader(
            bucket_name=S3_BUCKET_NAME,
            key_prefix='images/objects-in-the-lab/images/',
            max_keys=10
        )
        self.captions = generate_captions(
            image_loader.iter_images(),
            self.model,
            self.image_processor,
            self.tokenizer)
        meter_provider.shutdown()
        self.next(self.end)

    @tracer.start_as_current_span("4--end")
    @step
    def end(self):
        from instrumentation import setup_metrics
        meter_provider = setup_metrics(
            tool=TOOL,
            experiment_id=EXPERIMENT_ID,
            run_id=RUN_ID,
            step_id="end",
        )
        save_captions(self.captions)
        meter_provider.shutdown()


if __name__ == "__main__":
    ExperimentFlow()
    trace_provider.shutdown()
