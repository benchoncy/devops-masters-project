from PIL import Image
import boto3
import pickle
from tqdm import tqdm


DUMP_BUCKET = 'bstuart-masters-project-dump'
s3 = boto3.client('s3')


def to_s3(obj, key):
    obj = pickle.dumps(obj)
    s3.put_object(
        Body=obj,
        Bucket=DUMP_BUCKET,
        Key=key,
    )


def from_s3(key):
    response = s3.get_object(
        Bucket=DUMP_BUCKET,
        Key=key,
    )
    obj = pickle.loads(response['Body'].read())
    return obj


class S3Iterator:
    def __init__(self, bucket_name, key_prefix, max_keys=None):
        self.bucket_name = bucket_name
        self.key_prefix = key_prefix
        self.s3 = boto3.client('s3')
        self.max_keys = max_keys

    def reader(self, obj):
        return obj

    def __iter__(self):
        config = {}
        total = None
        if self.max_keys:
            config['MaxItems'] = self.max_keys
            total = self.max_keys
        paginator = self.s3.get_paginator('list_objects')
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=self.key_prefix,
            PaginationConfig=config
        )
        counter = tqdm(
            total=total,
            desc='Loading files from S3',
        )
        for page in page_iterator:
            for item in page['Contents']:
                counter.update(1)
                key = item['Key']
                response = self.s3.get_object(Bucket=self.bucket_name,
                                              Key=key)
                obj = self.reader(response['Body'])
                yield key, obj
        counter.close()


class S3ImageLoader(S3Iterator):
    # Load images from an S3 bucket
    def reader(self, obj):
        return Image.open(obj)
