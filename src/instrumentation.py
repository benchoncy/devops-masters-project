from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import psutil
import cpuinfo


# Define constants
KB = float(1024)
MB = float(KB ** 2)
GB = float(KB ** 3)


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


def setup_metrics(experiment_id: str,
                  step_id: str,
                  exporter=ConsoleMetricExporter(),
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
                "experiment.id": experiment_id,
                "experiment.step.id": step_id,
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


def setup_traces(experiment_id: str, exporter=ConsoleSpanExporter()):
    processor = BatchSpanProcessor(
        span_exporter=exporter,
    )
    # Create trace provider
    trace_provider = TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: "system-traces",
                "experiment.id": experiment_id,
            }
        )
    )
    trace_provider.add_span_processor(processor)
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(experiment_id)
    return tracer


if __name__ == "__main__":
    # Export metrics to console
    tracer = setup_traces(experiment_id="test")

    @tracer.start_as_current_span(name="run")
    def run():
        import time
        setup_metrics(experiment_id="test",
                      step_id="run",
                      export_interval_seconds=1)
        # Wait 10 seconds
        time.sleep(10)

    run()
