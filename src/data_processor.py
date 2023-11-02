from src.pipelines.utils import S3Iterator
import json
import pandas as pd
import logging
from collections import defaultdict
import os


S3_BUCKET_NAME = 'bstuart-masters-project-logs'

EXPERIMENTS = {
    "image-captioning": {
        "steps": ["start", "inference", "end"],
        "exclusions": [18, 56],
    }
}

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

    summary = summarise_data(data)
    generate_plots(summary, data)


def collect_data():
    logging.info('Starting data collection...')
    data = {}
    for experiment in EXPERIMENTS.keys():
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
            # Convert start_time and end_time to from nanoseconds to seconds
            for span in data[tool][run_id]['spans'][step]:
                span['start_time'] = span['start_time'] / 1000000000
                span['end_time'] = span['end_time'] / 1000000000
        if name.endswith('.txt'):
            marker = name.split('.')[0]
            time = file.read().decode('utf-8')
            data[tool][run_id]['marker'][marker] = int(time)

    return data


def read_csv_data(file):
    df = pd.read_csv(file)
    return df.to_dict(orient='records')


def summarise_data(data):
    logging.info('Summarising data...')
    summary = {}
    for experiment, experiment_data in data.items():
        logging.info(f'Summarising data for experiment {experiment}...')
        summary[experiment] = summarise_experiment_data(
            experiment_data,
            config=EXPERIMENTS[experiment]
        )
    return summary


def summarise_experiment_data(data, config):
    steps = config['steps']
    result = {}
    for tool, tool_data in data.items():
        logging.info(f'Summarising data for tool {tool}...')
        result[tool] = {}
        first_span = steps[0]
        last_span = steps[-1]

        summarised_metrics = []
        summarised_times = []
        for run_id, run_data in tool_data.items():
            if int(run_id) in config['exclusions']:
                continue
            logging.info(f'Summarising data for run {run_id}...')
            time_to_first_span = run_data['spans'][first_span][0]['start_time'] \
                - run_data['marker']['start']
            last_span_to_end = run_data['marker']['end'] \
                - run_data['spans'][last_span][0]['end_time']
            total_duration = run_data['marker']['end'] \
                - run_data['marker']['start']
            time_between_spans = []
            for index, step in enumerate(steps):
                if index != 0:
                    # Calculate time between spans
                    time_since_last_span = \
                        run_data['spans'][step][0]['start_time'] \
                        - run_data['spans'][steps[index - 1]][0]['end_time']
                    time_between_spans.append(time_since_last_span)
                # Summarise metrics and spans by step
                metrics_data = run_data['metrics'][step]
                metrics_df = pd.DataFrame(metrics_data)
                metrics_df.drop(columns=['time'], inplace=True)
                step_runs = []
                for column in metrics_df.columns:
                    summary = summarise_metrics(metrics_df, column)
                    step_runs.append(summary)
                step_run_metrics = pd.DataFrame(step_runs).mean()
                # Add duration from spans
                span_data = run_data['spans'][step]
                span_df = pd.DataFrame(span_data)
                span_df.drop(columns=['parent', 'name'], inplace=True)
                span_df['duration'] = \
                    span_df['end_time'] - span_df['start_time']
                step_run_metrics['step'] = step
                step_run_metrics['duration'] = span_df['duration']
                summarised_metrics.append(step_run_metrics)

            # Summarise times
            time_between_spans = pd.Series(time_between_spans)
            time_between_spans = time_between_spans.mean()
            summarised_times.append({
                'time_to_first_span': time_to_first_span,
                'last_span_to_end': last_span_to_end,
                'total_duration': total_duration,
                'time_between_spans': time_between_spans,
            })

        if len(summarised_metrics) == 0:
            continue
        summarised_metrics = pd.DataFrame(summarised_metrics)
        summarised_metrics = summarised_metrics.groupby('step').mean()
        result[tool]['metrics'] = summarised_metrics

        summarised_times = pd.DataFrame(summarised_times)
        for column in summarised_times.columns:
            result[tool][column] = summarise_metrics(summarised_times, column)
    return result


def summarise_metrics(df, column):
    grouped = df[column].agg(
        min='min',
        max='max',
        mean='mean',
        std='std',
        p5=lambda x: x.quantile(0.05),
        p95=lambda x: x.quantile(0.95),
        p99=lambda x: x.quantile(0.99),
    )
    grouped = grouped.add_prefix(f'{column}_')
    return grouped


def generate_plots(summary, raw_data):
    print(summary)


if __name__ == '__main__':
    main()
