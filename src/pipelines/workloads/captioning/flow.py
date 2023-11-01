from metaflow import FlowSpec, step, Parameter, resources
from src.pipelines.instrumentation import TelemetryManager
from src.pipelines.workloads.captioning.workload import load_models, generate_captions, save_captions
from src.pipelines.utils import S3ImageLoader


class ExperimentFlow(FlowSpec):

    inf = Parameter('inf', help='Number of inferences to run', default=10)
    run_id = Parameter('run_id', help='Run ID')
    tm = TelemetryManager(tool="metaflow", experiment_id="image-captioning")

    @resources(cpu=2, memory=8000)
    @step
    def start(self):
        self.tm.setup(run_id=self.run_id, step_id="start")
        with self.tm.tracer.start_as_current_span("start"):
            print("Starting experiment")
            print("Loading models")
            self.model, self.image_processor, self.tokenizer \
                = load_models()
        self.tm.shutdown()
        self.next(self.inference)

    @resources(cpu=2, memory=8000)
    @step
    def inference(self):
        self.tm.setup(run_id=self.run_id, step_id="inference")
        with self.tm.tracer.start_as_current_span("inference"):
            image_loader = S3ImageLoader(
                bucket_name="bstuart-masters-project-dataset",
                key_prefix='images/objects-in-the-lab/images/',
                max_keys=10
            )
            self.captions = generate_captions(
                image_loader,
                self.model,
                self.image_processor,
                self.tokenizer)
        self.tm.shutdown()
        self.next(self.end)

    @resources(cpu=2, memory=8000)
    @step
    def end(self):
        self.tm.setup(run_id=self.run_id, step_id="end")
        with self.tm.tracer.start_as_current_span("end"):
            save_captions(self.captions)
        self.tm.shutdown()


if __name__ == "__main__":
    ExperimentFlow()
