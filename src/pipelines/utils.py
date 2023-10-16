# Based on https://michael-franke.github.io/npNLG/08-grounded-LMs/08c-NIC-pretrained.html

from PIL import Image
import os
import boto3


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
    def __init__(self, bucket_name, key_prefix, max_keys=None):
        self.bucket_name = bucket_name
        self.key_prefix = key_prefix
        self.s3 = boto3.client('s3')
        self.max_keys = max_keys

    def iter_images(self):
        paginator = self.s3.get_paginator('list_objects')
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=self.key_prefix,
            PaginationConfig={'MaxItems': self.max_keys}
        )
        for page in page_iterator:
            for item in page['Contents']:
                key = item['Key']
                if key.endswith('.jpg'):
                    response = self.s3.get_object(Bucket=self.bucket_name,
                                                  Key=key)
                    image = Image.open(response['Body'])
                    yield key, image
