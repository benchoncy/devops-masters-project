from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    MetricExporter
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import psutil
import cpuinfo
import boto3
import json
import csv


S3_BUCKET_NAME = "bstuart-masters-project-logs"


# Define constants
KB = float(1024)
MB = float(KB ** 2)
GB = float(KB ** 3)


def to_csv(data, path):
    keys = data[0].keys()
    with open(path, 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)


def to_s3(path, bucket_name, key):
    s3 = boto3.client("s3")
    s3.upload_file(path, bucket_name, key)


class S3MetricExporter(MetricExporter):
    def __init__(
            self, bucket_name=S3_BUCKET_NAME, **kwargs):
        self.bucket_name = bucket_name
        self.metrics_data = []
        self.system_profile = None
        super().__init__(**kwargs)

    def export(self, metrics_data, **_):
        json_data = json.loads(metrics_data.to_json())
        if self.system_profile is None:
            attributes = json_data["resource_metrics"][0]["resource"]["attributes"]
            self.system_profile = attributes
        metrics = json_data["resource_metrics"][0]["scope_metrics"][0]["metrics"]
        for metric in metrics:
            name = metric["name"]
            data = metric["data"]["data_points"][0]
            time = data["time_unix_nano"]
            value = data["value"]
            self.metrics_data.append({
                "name": name,
                "time": time,
                "value": value,
            })

    def force_flush(self, timeout_millis=None):
        pass

    def shutdown(self, **_):
        tool = self.system_profile["experiment.tool"]
        experiment_id = self.system_profile["experiment.id"]
        step_id = self.system_profile["experiment.step.id"]
        run_id = self.system_profile["experiment.run.id"]
        path = "/tmp/metrics.csv"
        key = f"{experiment_id}/{tool}/{run_id}/{step_id}_metrics.csv"
        to_csv(self.metrics_data, path)
        to_s3(path, self.bucket_name, key)


class S3SpanExporter(SpanExporter):
    def __init__(self, bucket_name=S3_BUCKET_NAME, **kwargs):
        self.bucket_name = bucket_name
        self.span_data = []
        self.system_profile = None
        super().__init__(**kwargs)

    def export(self, span_data, **_):
        for span in span_data:
            if self.system_profile is None:
                asstributes = span.resource.attributes
                self.system_profile = asstributes
            self.span_data.append({
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "parent": span.parent,
            })

    def force_flush(self, timeout_millis=None):
        pass

    def shutdown(self, **_):
        tool = self.system_profile["experiment.tool"]
        experiment_id = self.system_profile["experiment.id"]
        run_id = self.system_profile["experiment.run.id"]
        path = "/tmp/spans.csv"
        key = f"{experiment_id}/{tool}/{run_id}/spans.csv"
        to_csv(self.span_data, path)
        to_s3(path, self.bucket_name, key)


# Metric callbacks
def get_cpu_usage_callback(_: CallbackOptions):
    yield Observation(
        value=psutil.cpu_percent(),
    )


def get_memory_usage_callback(_: CallbackOptions):
    yield Observation(
        value=psutil.virtual_memory().percent,
    )


def get_disk_usage_callback(_: CallbackOptions):
    yield Observation(
        value=psutil.disk_usage('/').percent,
    )


def get_disk_iops_callback(_: CallbackOptions):
    io = psutil.disk_io_counters()
    yield Observation(
        value=io.read_count + io.write_count,
    )


def get_network_iops_callback(_: CallbackOptions):
    net_io = psutil.net_io_counters()
    yield Observation(
        value=net_io.packets_sent + net_io.packets_recv,
    )


def setup_metrics(tool: str,
                  experiment_id: str,
                  step_id: str,
                  run_id: int,
                  exporter=S3MetricExporter(),
                  export_interval_seconds=15):
    reader = PeriodicExportingMetricReader(
        exporter=exporter,
        export_interval_millis=export_interval_seconds * 1000,
    )
    # Create meter provider
    meter_provider = MeterProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: "system-metrics",
                "experiment.tool": tool,
                "experiment.id": experiment_id,
                "experiment.step.id": step_id,
                "experiment.run.id": run_id,
                "system.cpu.brand": cpuinfo.get_cpu_info()['brand_raw'],
                "system.cpu.cores": psutil.cpu_count(),
                "system.memory.total": psutil.virtual_memory().total / GB,
                "system.disk.total": psutil.disk_usage('/').total / GB,
            }
        ),
        metric_readers=[reader]
    )
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter(f"{experiment_id}.{step_id}")

    # Create systen metric gauges
    cpu_usage = meter.create_observable_gauge(
        callbacks=[get_cpu_usage_callback],
        name="cpu_percent",
        description="CPU usage in percent",
        unit="1"
    )

    memory_usage = meter.create_observable_gauge(
        callbacks=[get_memory_usage_callback],
        name="memory_percent",
        description="Memory usage in percent",
        unit="1"
    )

    disk_usage = meter.create_observable_gauge(
        callbacks=[get_disk_usage_callback],
        name="disk_percent",
        description="Disk usage in percent",
        unit="1"
    )

    disk_iops = meter.create_observable_gauge(
        callbacks=[get_disk_iops_callback],
        name="disk_iops",
        description="Disk IOPS",
        unit="IOPS"
    )

    network_iops = meter.create_observable_gauge(
        callbacks=[get_network_iops_callback],
        name="network_iops",
        description="Network IOPS",
        unit="IOPS"
    )

    return meter_provider


def setup_traces(tool: str, experiment_id: str, run_id: int, exporter=S3SpanExporter()):
    processor = BatchSpanProcessor(
        span_exporter=exporter,
    )
    # Create trace provider
    trace_provider = TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: "system-traces",
                "experiment.tool": tool,
                "experiment.id": experiment_id,
                "experiment.run.id": run_id,
            }
        ),
    )
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(experiment_id)
    return tracer, trace_provider


if __name__ == "__main__":
    # Export metrics to console
    tracer, trace_provider = setup_traces(tool="test", experiment_id="test", run_id=1)

    @tracer.start_as_current_span(name="run")
    def run():
        import time
        meter_provider = setup_metrics(tool="test",
                      experiment_id="test",
                      step_id="run",
                      run_id=1,
                      export_interval_seconds=1)
        time.sleep(3)
        meter_provider.shutdown()
    run()
    trace_provider.shutdown()
