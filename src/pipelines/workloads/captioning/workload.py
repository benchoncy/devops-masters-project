# Based on https://michael-franke.github.io/npNLG/08-grounded-LMs/08c-NIC-pretrained.html

from transformers import \
    GPT2TokenizerFast, ViTImageProcessor, VisionEncoderDecoderModel
from tqdm import tqdm
from src.pipelines.utils import S3ImageLoader


def load_models():
    model_raw = VisionEncoderDecoderModel \
        .from_pretrained("nlpconnect/vit-gpt2-image-captioning")
    image_processor = ViTImageProcessor \
        .from_pretrained("nlpconnect/vit-gpt2-image-captioning")
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


def save_captions(captions):
    # Save the captions as a csv
    with open('captions.csv', 'w') as f:
        for name, caption in captions.items():
            f.write(f'{name},{caption}\n')


if __name__ == '__main__':
    S3_BUCKET_NAME = 'bstuart-masters-project-dataset'

    # Load the model
    model, image_processor, tokenizer = load_models()

    # Load the images
    image_loader = S3ImageLoader(
        bucket_name=S3_BUCKET_NAME,
        key_prefix='images/objects-in-the-lab/images/',
        max_keys=10
    )

    # Generate captions
    captions = generate_captions(image_loader.iter_images(),
                                 model,
                                 image_processor,
                                 tokenizer)

    # Save the captions
    save_captions(captions)
