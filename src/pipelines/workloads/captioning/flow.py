from metaflow import FlowSpec, step
from instrumentation import setup_traces
from .workload import load_models, generate_captions, save_captions
from src.pipelines.utils import S3ImageLoader

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
        self.model, self.image_processor, self.tokenizer \
            = load_models()
        self.next(self.inference)

    @tracer.start_as_current_span("3--inference")
    @step
    def inference(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="inference",
        )
        image_loader = S3ImageLoader(
            bucket_name=S3_BUCKET_NAME,
            key_prefix='/'
        )
        self.captions = generate_captions(
            image_loader.iter_images(),
            self.model,
            self.image_processor,
            self.tokenizer)
        self.next(self.end)

    @tracer.start_as_current_span("4--end")
    @step
    def end(self):
        from instrumentation import setup_metrics
        setup_metrics(
            experiment_id=EXPERIMENT_ID,
            step_id="end",
        )
        save_captions(self.captions)


if __name__ == "__main__":
    ExperimentFlow()
