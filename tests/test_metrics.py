from unittest.mock import patch

import pytest
from prometheus_client import CollectorRegistry

from grillgauge.metrics import MetricsCollector


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
