from src.pipelines.utils import S3Iterator
import json
import pandas as pd
import logging
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from tqdm import tqdm


S3_BUCKET_NAME = 'bstuart-masters-project-logs'

EXPERIMENTS = {
    "image-captioning": {
        "steps": ["start", "inference", "end"],
        "exclusions": [18, 56],
    }
}
TOOLS = ['metaflow', 'airflow', 'sagemaker']
VALUE_TO_DISPLAY = {
    'percent': 'Percent (%)',
    'duration': 'Duration (s)',
    'count': 'Count',
    'iops': 'IOPS',
    'bytes': 'Bytes',
}

TMP_FILE = '/tmp/exp_data.json'
OUTPUT_DIR = 'paper/images/generated/'

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
        summarised_span_durations = defaultdict(list)
        for run_id, run_data in tqdm(tool_data.items()):
            if int(run_id) in config['exclusions']:
                logging.info(
                    f'Skipping run {run_id} due to explicit exclusion'
                )
                continue
            time_to_first_span = \
                run_data['spans'][first_span][0]['start_time'] \
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
                # Add duration from spans
                span_data = run_data['spans'][step]
                span_df = pd.DataFrame(span_data)
                span_df['duration'] = \
                    span_df['end_time'] - span_df['start_time']
                duration = span_df['duration'][0]
                # Summarise metrics and spans by step
                metrics_data = run_data['metrics'][step]
                metrics_df = pd.DataFrame(metrics_data)
                metrics_df['step'] = step
                summarised_span_durations[step].append(duration)
                summarised_metrics.append(metrics_df)

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
        summarised_metrics = pd.concat(summarised_metrics, ignore_index=True)
        result[tool]['metrics'] = summarised_metrics

        summarised_times = pd.DataFrame(summarised_times)
        result[tool]['times'] = summarised_times

        summarised_span_durations = pd.DataFrame(summarised_span_durations)
        result[tool]['span_durations'] = summarised_span_durations
    return result


def generate_plots(summary, _):
    logging.info('Generating plots...')
    for experiment, experiment_data in summary.items():
        experiment_steps = EXPERIMENTS[experiment]['steps']
        time_data = {
            ('total_duration', f'Total duration - {experiment}',
             'Duration (s)', f'{experiment}_total_duration.png'): [],
            ('time_to_first_span', f'Startup time - {experiment}',
             'Duration (s)', f'{experiment}_startup_time.png'): [],
            ('last_span_to_end', f'Cleanup time - {experiment}',
             'Duration (s)', f'{experiment}_cleanup_time.png'): [],
            ('time_between_spans', f'Time between steps - {experiment}',
             'Duration (s)', f'{experiment}_time_between_steps.png'): [],
        }
        metrics_data = {step: {} for step in experiment_steps}
        duration_data = {step: {tool: [] for tool in TOOLS}
                         for step in experiment_steps}

        # Collect data into frames to more easily generate plots
        for tool in TOOLS:
            tool_data = experiment_data.get(tool, {})
            if tool_data == {}:
                continue
            raw_times = tool_data['times']
            for key in time_data.keys():
                time_data[key].append(raw_times[key[0]])
            for step in experiment_steps:
                duration_data[step][tool].append(
                    tool_data['span_durations'][step])
                metrics = tool_data['metrics']
                metrics = metrics[metrics['step'] == step]
                metrics = metrics.drop(columns=['step', 'time'])
                metrics_data[step][tool] = metrics

        # Generate time plots
        for (key, title, y_label, output_file), plot_data in time_data.items():
            generate_box_plot(plot_data, title, y_label, output_file)

        # Generate metrics plots
        for step in experiment_steps:
            plot_metrics_data = {}
            for tool in TOOLS:
                metrics = metrics_data[step].get(tool, pd.DataFrame())
                if metrics.empty:
                    continue
                for column in metrics.columns:
                    plot_metrics_data[column] = metrics[column]
            for column, data in plot_metrics_data.items():
                name, value = column.split('_')
                generate_box_plot(
                    data,
                    f'Metric {name} - {experiment} / {step}',
                    VALUE_TO_DISPLAY[value],
                    f'{experiment}_{step}_metrics_{column}.png'
                )

        # Generate duration plots
        for step in experiment_steps:
            plot_duration_data = []
            for tool in TOOLS:
                if duration_data[step][tool] == []:
                    continue
                plot_duration_data.append(
                    pd.concat(duration_data[step][tool], ignore_index=True)
                )
            generate_box_plot(
                plot_duration_data,
                f'Step duration - {experiment} / {step}',
                VALUE_TO_DISPLAY['duration'],
                f'{experiment}_{step}_duration.png'
            )


def generate_box_plot(data, title, y_axis_label, output_file):
    plt.boxplot(
        data,
        meanline=True,
        showmeans=True,
        showfliers=False,
        whis=(5, 95),
    )
    plt.xticks(range(1, len(TOOLS) + 1), TOOLS)
    plt.title(title)
    plt.ylabel(y_axis_label)
    plt.savefig(f'{OUTPUT_DIR}{output_file}')
    plt.clf()


if __name__ == '__main__':
    main()
