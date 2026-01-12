from prometheus_client import REGISTRY, CollectorRegistry, Gauge
from slugify import slugify

from .config import (
    GRILL_TEMPERATURE_METRIC_NAME,
    MEAT_TEMPERATURE_METRIC_NAME,
    PROBE_STATUS_METRIC_NAME,
    logger,
)
from .env import EnvManager


class MetricsCollector:
    """Collects and manages Prometheus metrics for grillprobeE devices."""

    def __init__(self, registry: CollectorRegistry | None = None):
        if registry is None:
            self.registry = REGISTRY
        else:
            self.registry = registry

        # Initialize Prometheus gauges with labels
        # Handle case where metrics already exist (development/testing)
        try:
            self.meat_temp_gauge = Gauge(
                MEAT_TEMPERATURE_METRIC_NAME,
                "Meat probe temperature in Celsius",
                ["device_address", "probe_name"],
                registry=self.registry,
            )
        except ValueError:
            # Metric already exists, reuse it
            self.meat_temp_gauge = self.registry._names_to_collectors[
                MEAT_TEMPERATURE_METRIC_NAME
            ]

        try:
            self.grill_temp_gauge = Gauge(
                GRILL_TEMPERATURE_METRIC_NAME,
                "Grill temperature in Celsius",
                ["device_address", "probe_name"],
                registry=self.registry,
            )
        except ValueError:
            self.grill_temp_gauge = self.registry._names_to_collectors[
                GRILL_TEMPERATURE_METRIC_NAME
            ]

        try:
            self.probe_status_gauge = Gauge(
                PROBE_STATUS_METRIC_NAME,
                "Probe connectivity status (1=online, 0=offline)",
                ["device_address", "probe_name"],
                registry=self.registry,
            )
        except ValueError:
            self.probe_status_gauge = self.registry._names_to_collectors[
                PROBE_STATUS_METRIC_NAME
            ]

        # Store last known good values for fault tolerance
        self.last_values: dict[str, dict[str, float | int]] = {}

        # Probe name mapping (device_address -> slugified_name)
        self.probe_names: dict[str, str] = {}
        self._load_probe_names()

    def _load_probe_names(self):
        """Load and slugify probe names from .env configuration."""

        env_manager = EnvManager()
        probes = env_manager.list_probes()

        logger.debug(
            f"MetricsCollector: Loading {len(probes)} probes from configuration"
        )
        for probe in probes:
            device_address = probe["mac"]
            display_name = probe["name"]
            # Slugify the display name for Prometheus labels
            slugified_name = slugify(display_name, separator="-", lowercase=True)
            self.probe_names[device_address] = slugified_name

            # Initialize metrics for this probe (will be updated with real values)
            logger.debug(
                f"MetricsCollector: Initializing metrics for {slugified_name} ({device_address})"
            )
            self.probe_status_gauge.labels(
                device_address=device_address, probe_name=slugified_name
            ).set(0)  # Start offline

    def update_probe_metrics(
        self,
        device_address: str,
        meat_temp: float | None,
        grill_temp: float | None,
        status: int,
    ):
        """Update Prometheus metrics for a probe."""
        probe_name = self.probe_names.get(device_address, "unknown-probe")

        # Update status (always current)
        self.probe_status_gauge.labels(
            device_address=device_address, probe_name=probe_name
        ).set(status)

        # Update temperatures (use last known good values if None provided)
        if meat_temp is not None:
            self.meat_temp_gauge.labels(
                device_address=device_address, probe_name=probe_name
            ).set(meat_temp)
            # Store last known good value
            if device_address not in self.last_values:
                self.last_values[device_address] = {}
            self.last_values[device_address]["meat_temp"] = meat_temp
        elif (
            device_address in self.last_values
            and "meat_temp" in self.last_values[device_address]
        ):
            # Keep existing value (fault tolerance)
            pass
        else:
            # No previous value, set to 0
            self.meat_temp_gauge.labels(
                device_address=device_address, probe_name=probe_name
            ).set(0)

        if grill_temp is not None:
            self.grill_temp_gauge.labels(
                device_address=device_address, probe_name=probe_name
            ).set(grill_temp)
            # Store last known good value
            if device_address not in self.last_values:
                self.last_values[device_address] = {}
            self.last_values[device_address]["grill_temp"] = grill_temp
        elif (
            device_address in self.last_values
            and "grill_temp" in self.last_values[device_address]
        ):
            # Keep existing value (fault tolerance)
            pass
        else:
            # No previous value, set to 0
            self.grill_temp_gauge.labels(
                device_address=device_address, probe_name=probe_name
            ).set(0)

        logger.debug(
            f"Updated metrics for {device_address} ({probe_name}): "
            f"meat={meat_temp}°C, grill={grill_temp}°C, status={status}"
        )
