from metaflow import FlowSpec, step, Parameter, resources
from src.pipelines.instrumentation import TelemetryManager
from src.pipelines.workloads.captioning.workload import load_models, generate_captions, save_captions
from src.pipelines.utils import S3ImageLoader, to_s3, from_s3


class ExperimentFlow(FlowSpec):

    run_id = Parameter('run_id', help='Run ID')
    tm = TelemetryManager(tool="metaflow", experiment_id="image-captioning")

    @resources(cpu=2, memory=8000)
    @step
    def start(self):
        self.tm.setup(run_id=self.run_id, step_id="start")
        with self.tm.tracer.start_as_current_span("start"):
            print("Starting experiment")
            print("Loading models")
            model, image_processor, tokenizer \
                = load_models()
            to_s3(model, f"experiment/{self.tm.experiment_id}/{self.tm.tool}/model")
            to_s3(image_processor, f"experiment/{self.tm.experiment_id}/{self.tm.tool}/image_processor")
            to_s3(tokenizer, f"experiment/{self.tm.experiment_id}/{self.tm.tool}/tokenizer")
        self.tm.shutdown()
        self.next(self.inference)

    @resources(cpu=2, memory=8000)
    @step
    def inference(self):
        self.tm.setup(run_id=self.run_id, step_id="inference")
        with self.tm.tracer.start_as_current_span("inference"):
            model = from_s3(f"experiment/{self.tm.experiment_id}/{self.tm.tool}/model")
            image_processor = from_s3(f"experiment/{self.tm.experiment_id}/{self.tm.tool}/image_processor")
            tokenizer = from_s3(f"experiment/{self.tm.experiment_id}/{self.tm.tool}/tokenizer")
            image_loader = S3ImageLoader(
                bucket_name="bstuart-masters-project-dataset",
                key_prefix='images/objects-in-the-lab/images_small/',
                max_keys=20
            )
            captions = generate_captions(
                image_loader,
                model,
                image_processor,
                tokenizer)
            to_s3(captions, f"experiment/{self.tm.experiment_id}/{self.tm.tool}/captions")
        self.tm.shutdown()
        self.next(self.end)

    @resources(cpu=2, memory=8000)
    @step
    def end(self):
        self.tm.setup(run_id=self.run_id, step_id="end")
        with self.tm.tracer.start_as_current_span("end"):
            captions = from_s3(f"experiment/{self.tm.experiment_id}/{self.tm.tool}/captions")
            save_captions(captions)
        self.tm.shutdown()


if __name__ == "__main__":
    ExperimentFlow()
