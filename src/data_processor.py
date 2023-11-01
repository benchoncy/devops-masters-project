from src.pipelines.utils import S3Iterator
import json
import pandas as pd
import logging
from collections import defaultdict
import os


S3_BUCKET_NAME = 'bstuart-masters-project-logs'

EXPERIMENTS = [
    "image-captioning",
]

TMP_FILE = '/tmp/exp_data.json'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(levelname)s] %(message)s'
)


def main():
    # Check if data has already been collected
    if os.path.exists(TMP_FILE):
        logging.info('Data already collected')
        data = json.load(open(TMP_FILE))
    else:
        data = collect_data()
        # Save data to tmp file
        with open(TMP_FILE, 'w') as f:
            json.dump(data, f)

    summary = summarize_data(data)
    generate_plots(summary, data)


def collect_data():
    logging.info('Starting data collection...')
    data = {}
    for experiment in EXPERIMENTS:
        data[experiment] = collect_experiment_data(experiment)
    return data


def collect_experiment_data(experiment):
    logging.info(f'Collecting data for experiment {experiment}...')

    def make_defaultdict():
        return defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    data = {
        'metaflow': make_defaultdict(),
        'airflow': make_defaultdict(),
        'sagemaker': make_defaultdict(),
    }
    files = S3Iterator(
        bucket_name=S3_BUCKET_NAME,
        key_prefix=f'{experiment}/'
    )
    for key, file in files:
        logging.debug(f'Processing {key}...')
        _, tool, run_id, name = key.split('/')
        if name.endswith('_metrics.csv'):
            step = name.split('_')[0]
            data[tool][run_id]['metrics'][step] = read_csv_data(file)
        if name.endswith('_span.csv'):
            step = name.split('_')[0]
            data[tool][run_id]['spans'][step] = read_csv_data(file)
        if name.endswith('.txt'):
            marker = name.split('.')[0]
            time = file.read().decode('utf-8')
            data[tool][run_id]['marker'][marker] = time

    return data


def read_csv_data(file):
    df = pd.read_csv(file)
    return df.to_dict(orient='records')


def summarize_data(data):
    pass


def generate_plots(summary, raw_data):
    pass


if __name__ == '__main__':
    main()
