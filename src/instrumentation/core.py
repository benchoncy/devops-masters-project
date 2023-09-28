
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)

metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
provider = MeterProvider(metric_readers=[metric_reader])

# Sets the global default meter provider
metrics.set_meter_provider(provider)

# Gets or creates a named meter
meter = metrics.get_meter(__name__)

steps_counter = meter.create_counter(
    name="steps.counter",
    description="Counts number of steps in workflow",
    unit="1",
)

