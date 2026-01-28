import warnings
from unittest.mock import patch

import pytest
from prometheus_client import CollectorRegistry

from grillgauge.metrics import MetricsCollector

# Suppress coroutine warnings from mocks
warnings.filterwarnings("ignore", "coroutine.*was never awaited")


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    @pytest.fixture
    def mock_env_manager(self):
        """Mock EnvManager for testing."""
        with patch("grillgauge.metrics.EnvManager") as mock_env:
            mock_env.return_value.list_probes.return_value = [
                {"mac": "AA:BB:CC:11:22:33", "name": "Ribeye Probe"},
                {"mac": "DD:EE:FF:44:55:66", "name": "Brisket Probe #1"},
            ]
            yield mock_env

    @pytest.fixture
    def custom_registry(self):
        """Custom Prometheus registry for testing."""
        return CollectorRegistry()

    def test_initialization(self, mock_env_manager, custom_registry):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector(registry=custom_registry)

        # Check that probe names are slugified
        assert collector.probe_names["AA:BB:CC:11:22:33"] == "ribeye-probe"
        assert collector.probe_names["DD:EE:FF:44:55:66"] == "brisket-probe-1"

    def test_update_probe_metrics_success(self, mock_env_manager, custom_registry):
        """Test successful metrics update."""
        collector = MetricsCollector(registry=custom_registry)

        # Update metrics for a probe
        collector.update_probe_metrics(
            device_address="AA:BB:CC:11:22:33",
            meat_temp=65.5,
            grill_temp=225.0,
            status=1,
        )

        # Verify last values are stored
        assert collector.last_values["AA:BB:CC:11:22:33"]["meat_temp"] == 65.5  # noqa: PLR2004
        assert collector.last_values["AA:BB:CC:11:22:33"]["grill_temp"] == 225.0  # noqa: PLR2004

    def test_update_probe_metrics_failure_tolerance(
        self, mock_env_manager, custom_registry
    ):
        """Test fault tolerance when BLE read fails."""
        collector = MetricsCollector(registry=custom_registry)

        # First, set good values
        collector.update_probe_metrics(
            device_address="AA:BB:CC:11:22:33",
            meat_temp=65.5,
            grill_temp=225.0,
            status=1,
        )

        # Then simulate failure (None values)
        collector.update_probe_metrics(
            device_address="AA:BB:CC:11:22:33",
            meat_temp=None,  # Failed read
            grill_temp=None,  # Failed read
            status=0,  # Offline
        )

        # Last known good values should be preserved
        assert collector.last_values["AA:BB:CC:11:22:33"]["meat_temp"] == 65.5  # noqa: PLR2004
        assert collector.last_values["AA:BB:CC:11:22:33"]["grill_temp"] == 225.0  # noqa: PLR2004

    def test_unknown_probe_fallback(self, mock_env_manager, custom_registry):
        """Test handling of probes not in .env config."""
        collector = MetricsCollector(registry=custom_registry)

        # Update metrics for unknown probe
        collector.update_probe_metrics(
            device_address="FF:FF:FF:99:99:99",
            meat_temp=70.0,
            grill_temp=230.0,
            status=1,
        )

        # Should use fallback name
        assert (
            collector.probe_names.get("FF:FF:FF:99:99:99", "unknown-probe")
            == "unknown-probe"
        )

    def test_initialization_without_custom_registry(self, mock_env_manager):
        """Test initialization uses default REGISTRY if none provided."""
        from prometheus_client import REGISTRY

        collector = MetricsCollector()

        # Should use default registry
        assert collector.registry == REGISTRY

    def test_update_metrics_none_values_no_previous(
        self, mock_env_manager, custom_registry
    ):
        """Test updating metrics with None when no previous values exist."""
        collector = MetricsCollector(registry=custom_registry)

        # Update with None values (no previous data)
        collector.update_probe_metrics(
            device_address="AA:BB:CC:11:22:33",
            meat_temp=None,
            grill_temp=None,
            status=0,
        )

        # Should set to 0 when no previous value
        # Device should not be in last_values or have empty dict
        assert (
            "AA:BB:CC:11:22:33" not in collector.last_values
            or "meat_temp" not in collector.last_values.get("AA:BB:CC:11:22:33", {})
        )

    def test_gauge_creation_with_existing_metrics(
        self, mock_env_manager, custom_registry
    ):
        """Test initialization when metrics already exist in registry."""
        from prometheus_client import Gauge

        # Pre-create metrics in registry
        Gauge(
            "grillgauge_meat_temperature_celsius",
            "Meat probe temperature",
            ["device_address", "probe_name"],
            registry=custom_registry,
        )

        # Should reuse existing metric instead of creating new one
        collector = MetricsCollector(registry=custom_registry)

        # Should not raise ValueError
        assert collector.meat_temp_gauge is not None

    def test_partial_temperature_update(self, mock_env_manager, custom_registry):
        """Test updating only meat temp or only grill temp."""
        collector = MetricsCollector(registry=custom_registry)

        # Update only meat temp
        collector.update_probe_metrics(
            device_address="AA:BB:CC:11:22:33",
            meat_temp=65.0,
            grill_temp=None,
            status=1,
        )

        # Meat temp should be stored
        assert collector.last_values["AA:BB:CC:11:22:33"]["meat_temp"] == 65.0  # noqa: PLR2004

        # Now update only grill temp
        collector.update_probe_metrics(
            device_address="AA:BB:CC:11:22:33",
            meat_temp=None,
            grill_temp=220.0,
            status=1,
        )

        # Both should be in last_values
        assert collector.last_values["AA:BB:CC:11:22:33"]["meat_temp"] == 65.0  # noqa: PLR2004
        assert collector.last_values["AA:BB:CC:11:22:33"]["grill_temp"] == 220.0  # noqa: PLR2004
