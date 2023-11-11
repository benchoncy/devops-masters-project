# Based on https://michael-franke.github.io/npNLG/08-grounded-LMs/08c-NIC-pretrained.html

from transformers import \
    GPT2TokenizerFast, ViTImageProcessor, VisionEncoderDecoderModel
from tqdm import tqdm
from src.pipelines.utils import S3ImageLoader, to_s3, from_s3
from src.pipelines.instrumentation import profiler

experiment_id = "captioning"


def load_models():
    print('Loading raw model')
    model_raw = VisionEncoderDecoderModel \
        .from_pretrained("nlpconnect/vit-gpt2-image-captioning")
    print('Loading image processor')
    image_processor = ViTImageProcessor \
        .from_pretrained("nlpconnect/vit-gpt2-image-captioning")
    print('Loading tokenizer')
    tokenizer = GPT2TokenizerFast \
        .from_pretrained("nlpconnect/vit-gpt2-image-captioning")
    return model_raw, image_processor, tokenizer


def generate_caption(image, model, image_processor, tokenizer):
    # Preprocess image
    pixel_values = image_processor(images=image,
                                   return_tensors="pt").pixel_values
    # Generate caption
    caption_ids = model.generate(
        pixel_values,
        do_sample=True,
        max_new_tokens=200,
        top_k=50,
    )
    # Decode and return the caption
    caption = tokenizer.batch_decode(caption_ids, skip_special_tokens=True)
    return caption


def generate_captions(images, model, image_processor, tokenizer):
    captions = {}
    for name, image in tqdm(images):
        caption = generate_caption(image, model, image_processor, tokenizer)
        captions[name] = caption
    return captions


# Steps
def step_1_load(tool, run_id):
    @profiler(tool=tool, experiment_id=experiment_id,
              run_id=run_id, step_id="load_models")
    def load():
        print("Starting experiment")
        print("Loading models")
        model, image_processor, tokenizer \
            = load_models()
        to_s3(model, f"experiment/{experiment_id}/{tool}/model")
        to_s3(image_processor, f"experiment/{experiment_id}/{tool}/image_processor")
        to_s3(tokenizer, f"experiment/{experiment_id}/{tool}/tokenizer")
    load()


def step_2_inference(tool, run_id):
    @profiler(tool=tool, experiment_id=experiment_id,
              run_id=run_id, step_id="inference")
    def inference():
        model = from_s3(f"experiment/{experiment_id}/{tool}/model")
        image_processor = from_s3(f"experiment/{experiment_id}/{tool}/image_processor")
        tokenizer = from_s3(f"experiment/{experiment_id}/{tool}/tokenizer")
        image_loader = S3ImageLoader(
            bucket_name="bstuart-masters-project-dataset",
            key_prefix='images/objects-in-the-lab/images_small/',
            max_keys=100
        )
        captions = generate_captions(
            image_loader,
            model,
            image_processor,
            tokenizer)
        to_s3(captions, f"experiment/{experiment_id}/{tool}/captions")
    inference()
