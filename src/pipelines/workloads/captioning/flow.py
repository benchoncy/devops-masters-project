from metaflow import FlowSpec, step, Parameter
from src.pipelines.instrumentation import TelemetryManager
from src.pipelines.workloads.captioning.workload import load_models, generate_captions, save_captions
from src.pipelines.utils import S3ImageLoader
import os


class ExperimentFlow(FlowSpec):

    inf = Parameter('inf', help='Number of inferences to run', default=10)
    tm = TelemetryManager(tool="metaflow", experiment_id="image_captioning",
                          run_id=os.getenv("RUN_ID"))

    @step
    def start(self):
        tracer = self.tm.setup(step_id="start")
        with tracer.start_as_current_span("1--load-models"):
            print("Starting experiment")
            print("Loading models")
            self.model, self.image_processor, self.tokenizer \
                = load_models()
        self.tm.shutdown()
        self.next(self.inference)

    @step
    def inference(self):
        meter_provider = self.tm.setup_metrics(
            step_id="inference",
        )
        image_loader = S3ImageLoader(
            bucket_name="bstuart-masters-project-dataset",
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

    @step
    def end(self):
        meter_provider = self.tm.setup_metrics(
            step_id="end",
        )
        save_captions(self.captions)
        meter_provider.shutdown()


if __name__ == "__main__":
    ExperimentFlow()
