# Based on https://michael-franke.github.io/npNLG/08-grounded-LMs/08c-NIC-pretrained.html

from transformers import \
    GPT2TokenizerFast, ViTImageProcessor, VisionEncoderDecoderModel
from PIL import Image
import os
import boto3
from tqdm import tqdm


S3_BUCKET_NAME = 'bstuart-image-captioning-dataset'


def main():
    # Load the model
    model, image_processor, tokenizer = load_models()

    # Load the images
    image_loader = S3ImageLoader(bucket_name=S3_BUCKET_NAME,
                                 key_prefix='/')

    # Generate captions
    captions = generate_captions(image_loader.iter_images(),
                                 model,
                                 image_processor,
                                 tokenizer)

    # Save the captions as a csv
    with open('captions.csv', 'w') as f:
        for name, caption in captions.items():
            f.write(f'{name},{caption}\n')


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


class ImageLoader:
    # Load images from a directory
    def __init__(self, image_dir):
        self.image_dir = image_dir

    def iter_images(self):
        for image_file in os.listdir(self.image_dir):
            image_path = os.path.join(self.image_dir, image_file)
            image = Image.open(image_path)
            yield image_file, image


class S3ImageLoader(ImageLoader):
    # Load images from an S3 bucket
    def __init__(self, bucket_name, key_prefix):
        self.bucket_name = bucket_name
        self.key_prefix = key_prefix
        self.s3 = boto3.client('s3')

    def iter_images(self):
        paginator = self.s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=self.bucket_name,
                                           Prefix=self.key_prefix)
        for page in page_iterator:
            for item in page['Contents']:
                key = item['Key']
                if key.endswith('.jpg'):
                    response = self.s3.get_object(Bucket=self.bucket_name,
                                                  Key=key)
                    image = Image.open(response['Body'])
                    yield key, image
