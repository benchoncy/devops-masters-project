from src.pipelines.utils import S3Iterator
import json
import pandas as pd
import logging
from collections import defaultdict
import matplotlib.pyplot as plt
import os
from tqdm import tqdm
from scipy.stats import f_oneway, kstest, kruskal, ttest_ind


S3_BUCKET_NAME = 'bstuart-masters-project-logs'

EXPERIMENTS = {
    "captioning": {
        "steps": ["load", "inference"],
        "exclusions": [],
    }
}
TOOLS = [
    {'id': 'metaflow', 'name': 'Metaflow (K8s)'},
    {'id': 'metaflow_batch', 'name': 'Metaflow (Batch)'},
    {'id': 'airflow', 'name': 'Airflow (K8s)'},
    {'id': 'sagemaker', 'name': 'SageMaker'},
]
TOOL_IDS = [tool['id'] for tool in TOOLS]
TOOL_NAMES = [tool['name'] for tool in TOOLS]
VALUE_TO_DISPLAY = {
    'percent': 'Percent (%)',
    'duration': 'Duration (s)',
    'count': 'Count',
    'iops': 'IOPS',
    'bytes': 'Bytes',
}
METRICS = [
    'cpu_percent',
    'memory_percent',
    'disk_percent',
    'network_iops'
]

TMP_FILE = '/tmp/exp_data.json'
OUTPUT_DIR = 'paper/images/generated/'

os.makedirs(OUTPUT_DIR, exist_ok=True)

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

    summary, raw = summarise_data(data)
    generate_plots(summary, data)
    generate_stats(raw)


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
    data = {id: make_defaultdict() for id in TOOL_IDS}
    files = S3Iterator(
        bucket_name=S3_BUCKET_NAME,
        key_prefix=f'{experiment}/'
    )
    for key, file in files:
        try:
            _, tool, run_id, name = key.split('/')
        except ValueError as e:
            if e.args[0].startswith('not enough values to unpack'):
                continue
            raise e
        if name.endswith('_metrics.csv'):
            step = name.split('_')[0]
            data[tool][run_id]['metrics'][step] = read_csv_data(file)
            # Convert time to from nanoseconds to seconds
            for metric in data[tool][run_id]['metrics'][step]:
                metric['time'] = metric['time'] / 1000000000
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
    raw_data = {}
    for experiment, experiment_data in data.items():
        logging.info(f'Summarising data for experiment {experiment}...')
        summary[experiment], raw_data[experiment] = summarise_experiment_data(
            experiment_data,
            config=EXPERIMENTS[experiment]
        )
    return summary, raw_data


def summarise_experiment_data(data, config):
    steps = config['steps']
    result = {}
    raw_data = {
        tool: {
            step: {
                'cpu_percent': [],
                'memory_percent': [],
                'disk_percent': [],
                'network_iops': [],
                'duration': [],
            } for step in steps
        } for tool in TOOL_IDS
    }
    for tool in raw_data.keys():
        raw_data[tool]['times'] = {
            'time_to_first_span': [],
            'last_span_to_end': [],
            'total_duration': [],
            'time_between_spans': [],
        }
    for tool, tool_data in data.items():
        logging.info(f'Summarising data for tool {tool}...')
        result[tool] = {}
        first_span = steps[0]
        last_span = steps[-1]
        summarised_metrics = []
        summarised_times = []
        summarised_span_durations = defaultdict(list)
        for run_id, run_data in tqdm(tool_data.items()):
            try:
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
                    for metric in METRICS:
                        raw_data[tool][step][metric] += metrics_df[metric].tolist()
                    raw_data[tool][step]['duration'].append(duration)
                    # Replace time with relative time
                    metrics_df['time_rel'] = \
                        metrics_df['time'] - span_df['start_time'][0]
                    metrics_df = metrics_df.drop(columns=['time'])
                    metrics_df['time_bucket'] = \
                        metrics_df['time_rel'].apply(lambda x: get_bucket(x, 5))
                    summarised_span_durations[step].append(duration)
                    summarised_metrics.append(metrics_df)
            except Exception as e:
                print(f"Error in {tool} run_id: {run_id}")
                print(e)
                continue

            raw_data[tool]['times']['time_to_first_span'].append(time_to_first_span)
            raw_data[tool]['times']['last_span_to_end'].append(last_span_to_end)
            raw_data[tool]['times']['total_duration'].append(total_duration)
            raw_data[tool]['times']['time_between_spans'].append(*time_between_spans)
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
    return result, raw_data


def get_bucket(x, bucket_size):
    return int(x // bucket_size)*bucket_size


def generate_plots(summary, _):
    logging.info('Generating plots...')
    global_time_data = {
        'total_duration': {
            'config': ('Total duration - global',
                       'Duration (s)', 'global_total_duration'),
            'data': [[] for _ in range(len(TOOLS))],
        },
        'time_to_first_span': {
            'config': ('Startup time - global',
                       'Duration (s)', 'global_startup_time'),
            'data': [[] for _ in range(len(TOOLS))],
        },
        'last_span_to_end': {
            'config': ('Cleanup time - global',
                       'Duration (s)', 'global_cleanup_time'),
            'data': [[] for _ in range(len(TOOLS))],
        },
        'time_between_spans': {
            'config': ('Time between steps - global',
                       'Duration (s)', 'global_time_between_steps'),
            'data': [[] for _ in range(len(TOOLS))],
        },
    }

    for experiment, experiment_data in summary.items():
        experiment_steps = EXPERIMENTS[experiment]['steps']

        # Clean data for plotting
        time_data, metrics_data, duration_data = \
            clean_plot_data(experiment, experiment_data, experiment_steps)

        # Generate time plots
        for (key, title, y_label, output_file), plot_data in time_data.items():
            generate_box_plot(plot_data, title, y_label, output_file)
            box_plot_data = [data.median() for data in plot_data]
            for index, data in enumerate(plot_data):
                global_time_data[key]['data'][index].append(data)
            generate_bar_plot(box_plot_data, title, y_label, output_file)

        for step in experiment_steps:
            generate_step_plots(step, experiment, metrics_data, duration_data)

    # Generate global time plots
    for metric in global_time_data:
        config = global_time_data[metric]['config']
        plot_data = global_time_data[metric]['data']
        plot_data = plot_data
        plot_data = [pd.concat(data, ignore_index=True) for data in plot_data]
        generate_box_plot(
            plot_data,
            f'{config[0]}',
            f'{config[1]}',
            f'{config[2]}_box.png'
        )
        box_plot_data = [data.median() for data in plot_data]
        generate_bar_plot(
            box_plot_data,
            f'{config[0]}',
            f'{config[1]}',
            f'{config[2]}_bar.png'
        )


def clean_plot_data(experiment, experiment_data, experiment_steps):
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
    duration_data = {step: {tool: [] for tool in TOOL_IDS}
                     for step in experiment_steps}

    # Collect data into frames to more easily generate plots
    for tool in TOOL_IDS:
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
            metrics_data[step][tool] = metrics

    return time_data, metrics_data, duration_data


def generate_step_plots(step, experiment, metrics_data, duration_data):
    # Generate metric plots
    box_plot_metrics_data = defaultdict(list)
    line_plot_metrics_data = defaultdict(list)
    bar_diff_metrics_data = defaultdict(list)
    for tool in TOOL_IDS:
        metrics = metrics_data[step].get(tool, pd.DataFrame())
        if metrics.empty:
            continue
        for column in metrics.columns:
            if column in ['step', 'time_rel', 'time_bucket']:
                continue
            box_plot_metrics_data[column].append(metrics[column])
            line_plot_metrics_data[column].append(
                metrics.groupby('time_bucket')[column].mean()
            )
            bar_diff_metrics_data[column].append(
                metrics[column].median()
            )

    for column in box_plot_metrics_data.keys():
        name, value = column.split('_')
        box_data = box_plot_metrics_data[column]
        line_data = line_plot_metrics_data[column]
        bar_diff_data = bar_diff_metrics_data[column]
        generate_box_plot(
            box_data,
            f'Metric: {name} - {experiment} / {step}',
            VALUE_TO_DISPLAY[value],
            f'{experiment}_{step}_metrics_{column}_box.png'
        )
        generate_line_plot(
            line_data,
            f'Metric: {name} - {experiment} / {step}',
            VALUE_TO_DISPLAY[value],
            'Time (s)',
            f'{experiment}_{step}_metrics_{column}_line.png'
        )
        generate_bar_plot(
            bar_diff_data,
            f'Metric: {name} - {experiment} / {step}',
            VALUE_TO_DISPLAY[value],
            f'{experiment}_{step}_metrics_{column}_bar.png'
        )

    # Generate duration plots
    plot_duration_data = []
    for tool in TOOL_IDS:
        if duration_data[step][tool] == []:
            continue
        plot_duration_data.append(
            pd.concat(duration_data[step][tool], ignore_index=True)
        )
    generate_box_plot(
        plot_duration_data,
        f'Step duration - {experiment} / {step}',
        VALUE_TO_DISPLAY['duration'],
        f'{experiment}_{step}_duration_box.png'
    )
    plot_duration_data = [data.median() for data in plot_duration_data]
    generate_bar_plot(
        plot_duration_data,
        f'Step duration - {experiment} / {step}',
        VALUE_TO_DISPLAY['duration'],
        f'{experiment}_{step}_duration_bar.png'
    )


def generate_box_plot(data, title, y_axis_label, output_file):
    plt.boxplot(
        data,
        meanline=True,
        showmeans=True,
        showfliers=False,
        whis=(5, 95),
    )
    plt.xticks(range(1, len(TOOLS) + 1), TOOL_NAMES)
    plt.title(title)
    plt.ylabel(y_axis_label)
    plt.savefig(f'{OUTPUT_DIR}{output_file}')
    plt.clf()


def generate_line_plot(data, title, y_axis_label, x_axis_label, output_file):
    for plot_data in data:
        plt.plot(plot_data)
    plt.title(title)
    plt.ylabel(y_axis_label)
    plt.xlabel(x_axis_label)
    plt.legend(TOOL_NAMES)
    plt.savefig(f'{OUTPUT_DIR}{output_file}')
    plt.clf()


def generate_bar_plot(data, title, y_axis_label, output_file):
    plt.bar(TOOL_NAMES, data, color=['blue', 'orange', 'green', 'red'])
    plt.title(title)
    plt.ylabel(y_axis_label)
    plt.xticks(rotation=0)
    plt.savefig(f'{OUTPUT_DIR}{output_file}')
    plt.clf()


def generate_stats(data):
    logging.info('Generating stats...')
    for experiment, experiment_data in data.items():
        experiment_steps = EXPERIMENTS[experiment]['steps']
        for step in experiment_steps:
            generate_step_stats(step, experiment, experiment_data)
        for time in ['time_to_first_span', 'last_span_to_end', 'total_duration', 'time_between_spans']:
            print('---------------------')
            print(f'{experiment} / {time}')
            print('---------------------')
            data = [experiment_data[tool]['times'][time] for tool in TOOL_IDS]
            calculate_stats(data)


def calculate_stats(tool_values):
    _, pval = f_oneway(*tool_values)
    _, pval = kruskal(*tool_values)  # Non-parametric
    print(f'f_oneway: p-value: {pval}')
    print(f'kruskal: p-value: {pval}')
    for index, tool in enumerate(TOOL_NAMES):
        _, pval = kstest(tool_values[index], 'norm')
        print(f'kstest: {tool} - p-value: {pval}')
        for jndex, other_tool in enumerate(TOOL_NAMES):
            if jndex <= index:
                continue
            max_len = min(len(tool_values[index]), len(tool_values[jndex]))
            _, pval = ttest_ind(tool_values[index][:max_len], tool_values[jndex][:max_len])
            print(f'ttest_ind: {tool} vs {other_tool} - p-value: {pval}')
            _, pval = kruskal(tool_values[index], tool_values[jndex])
            print(f'kruskal: {tool} vs {other_tool} - p-value: {pval}')


def generate_step_stats(step, experiment, data):
    print('---------------------')
    print(f'Generating stats for {experiment} / {step}...')
    for metric in METRICS + ['duration']:
        metric_values = []
        for tool in TOOL_IDS:
            metric_values.append(data[tool][step][metric])
        print('---------------------')
        print(f'{experiment} / {step} / {metric}')
        print('---------------------')
        calculate_stats(metric_values)


if __name__ == '__main__':
    main()
