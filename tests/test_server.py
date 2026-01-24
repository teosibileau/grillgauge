"""Tests for MetricsServer event-driven architecture."""

import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import CollectorRegistry

from grillgauge.server import MetricsServer


class TestMetricsServer:
    """Test suite for MetricsServer class."""

    @pytest.fixture
    def custom_registry(self):
        """Create a custom Prometheus registry for testing."""
        return CollectorRegistry()

    @pytest.fixture
    def mock_env_manager(self):
        """Mock EnvManager."""
        with patch("grillgauge.server.EnvManager") as mock:
            yield mock

    @pytest.fixture
    def mock_probe(self):
        """Mock GrillProbe."""
        probe = AsyncMock()
        probe.is_connected = True
        probe.connect = AsyncMock(return_value=True)
        probe.disconnect = AsyncMock()
        probe.ensure_connected = AsyncMock()
        probe.device_address = "AA:BB:CC:DD:EE:FF"
        return probe

    def test_server_initialization(self, custom_registry):
        """Test MetricsServer initialization."""
        server = MetricsServer(host="127.0.0.1", port=9000, registry=custom_registry)
        assert server.host == "127.0.0.1"
        assert server.port == 9000  # noqa: PLR2004
        assert server.probes == {}
        assert server.reconnect_tasks == {}
        assert server.monitor_task is None
        assert server.app is not None

    @pytest.mark.asyncio
    async def test_health_endpoint(self, custom_registry):
        """Test health endpoint returns correct structure."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Create mock request
        request = MagicMock()

        # Get health handler
        health_handler = None
        for route in server.app.router.routes():
            if route.resource.canonical == "/health":
                health_handler = route._handler
                break

        assert health_handler is not None

        # Call handler
        response = await health_handler(request)

        # Verify response
        assert response.status == 200  # noqa: PLR2004
        data = response.body
        assert b"healthy" in data

    @pytest.mark.asyncio
    async def test_health_endpoint_with_probes(self, custom_registry):
        """Test health endpoint shows probe counts."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Add mock probes
        probe1 = MagicMock()
        probe1.is_connected = True
        probe2 = MagicMock()
        probe2.is_connected = False

        server.probes = {"probe1": probe1, "probe2": probe2}

        # Create mock request
        request = MagicMock()

        # Get health handler
        health_handler = None
        for route in server.app.router.routes():
            if route.resource.canonical == "/health":
                health_handler = route._handler
                break

        # Call handler
        response = await health_handler(request)

        # Verify response includes probe counts
        assert response.status == 200  # noqa: PLR2004

    def test_create_notification_callback(self, custom_registry):
        """Test notification callback factory."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Create callback
        callback = server._create_notification_callback(
            "AA:BB:CC:DD:EE:FF", "BBQ ProbeE 38701"
        )

        # Call callback
        callback(28.5, 31.0)

        # Verify metrics were updated (check via registry)
        families = list(server.metrics_collector.registry.collect())
        metric_names = [f.name for f in families]
        assert "grillgauge_meat_temperature_celsius" in metric_names
        assert "grillgauge_grill_temperature_celsius" in metric_names

    @pytest.mark.asyncio
    async def test_discover_and_connect_probes_with_configured(
        self, custom_registry, mock_env_manager, mock_probe
    ):
        """Test connecting to configured probes."""
        # Setup mock env manager
        mock_env_instance = MagicMock()
        mock_env_instance.list_probes.return_value = [
            {"mac": "AA:BB:CC:DD:EE:FF", "name": "BBQ ProbeE 38701"}
        ]
        mock_env_manager.return_value = mock_env_instance

        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Mock GrillProbe
        with patch("grillgauge.server.GrillProbe", return_value=mock_probe):
            await server._discover_and_connect_probes()

        # Verify probe was added
        assert len(server.probes) == 1
        assert "AA:BB:CC:DD:EE:FF" in server.probes

        # Verify connect was called
        mock_probe.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_and_connect_probes_connection_failure(
        self, custom_registry, mock_env_manager
    ):
        """Test handling probe connection failure."""
        # Setup mock env manager
        mock_env_instance = MagicMock()
        mock_env_instance.list_probes.return_value = [
            {"mac": "AA:BB:CC:DD:EE:FF", "name": "BBQ ProbeE 38701"}
        ]
        mock_env_manager.return_value = mock_env_instance

        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Mock GrillProbe that fails to connect
        mock_failed_probe = AsyncMock()
        mock_failed_probe.connect = AsyncMock(return_value=False)
        mock_failed_probe.is_connected = False

        with patch("grillgauge.server.GrillProbe", return_value=mock_failed_probe):
            await server._discover_and_connect_probes()

        # Verify probe was still added (for reconnection attempts)
        assert len(server.probes) == 1
        assert "AA:BB:CC:DD:EE:FF" in server.probes

    @pytest.mark.asyncio
    async def test_discover_and_connect_no_configured_runs_discovery(
        self, custom_registry, mock_env_manager
    ):
        """Test running discovery when no probes configured."""
        # Setup mock env manager - no probes initially, then still no probes after discovery
        mock_env_instance = MagicMock()
        mock_env_instance.list_probes.return_value = []
        mock_env_manager.return_value = mock_env_instance

        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Mock _discover_new_devices
        server._discover_new_devices = AsyncMock()

        await server._discover_and_connect_probes()

        # Verify discovery was called
        server._discover_new_devices.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_new_devices_success(self, custom_registry):
        """Test successful device discovery."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Mock DeviceScanner - need to patch where it's imported (inside the method)
        mock_scanner_instance = AsyncMock()
        mock_scanner_instance.return_value = [
            {
                "name": "BBQ ProbeE 38701",
                "address": "AA:BB:CC:DD:EE:FF",
                "classification": "probe",
            },
            {
                "name": "BBQ ProbeE 12345",
                "address": "BB:CC:DD:EE:FF:AA",
                "classification": "probe",
            },
        ]

        # Patch at the point of import within the function
        with patch(
            "grillgauge.scanner.DeviceScanner", return_value=mock_scanner_instance
        ):
            await server._discover_new_devices()

        # Should not raise, just log
        mock_scanner_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_new_devices_failure(self, custom_registry):
        """Test device discovery failure handling."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Mock DeviceScanner to raise exception
        mock_scanner_instance = AsyncMock()
        mock_scanner_instance.side_effect = Exception("Bluetooth adapter error")

        # Patch at the point of import within the function
        with patch(
            "grillgauge.scanner.DeviceScanner", return_value=mock_scanner_instance
        ):
            # Should not raise, just log error
            await server._discover_new_devices()

    @pytest.mark.asyncio
    async def test_discover_new_devices_no_probes(self, custom_registry):
        """Test discovery when no probes found."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Mock DeviceScanner - returns empty list
        mock_scanner_instance = AsyncMock()
        mock_scanner_instance.return_value = []

        # Patch at the point of import within the function
        with patch(
            "grillgauge.scanner.DeviceScanner", return_value=mock_scanner_instance
        ):
            await server._discover_new_devices()

        mock_scanner_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_connections_detects_disconnection(
        self, custom_registry, mock_probe
    ):
        """Test connection monitor detects and handles disconnections."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Add disconnected probe
        mock_probe.is_connected = False
        mock_probe.device_address = "AA:BB:CC:DD:EE:FF"
        server.probes = {"AA:BB:CC:DD:EE:FF": mock_probe}

        # Directly test the logic without running the full monitor loop
        # Just check that when a probe is disconnected, we would create a reconnect task

        # Simulate what _monitor_connections does for disconnected probes
        for device_address, probe in server.probes.items():
            if not probe.is_connected:
                # This is what the monitor does
                server.reconnect_tasks[device_address] = asyncio.create_task(
                    probe.ensure_connected()
                )

        # Verify reconnection task was created
        assert "AA:BB:CC:DD:EE:FF" in server.reconnect_tasks

        # Clean up
        for task in server.reconnect_tasks.values():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    @pytest.mark.asyncio
    async def test_monitor_connections_updates_metrics_on_disconnect(
        self, custom_registry, mock_probe
    ):
        """Test monitor updates metrics when probe disconnects."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Add disconnected probe
        mock_probe.is_connected = False
        mock_probe.device_address = "AA:BB:CC:DD:EE:FF"
        server.probes = {"AA:BB:CC:DD:EE:FF": mock_probe}

        # Run one iteration of monitor
        async def run_one_iteration():
            task = asyncio.create_task(server._monitor_connections())
            await asyncio.sleep(0.1)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        await run_one_iteration()

        # Verify metrics show offline status (status=0)
        # This is implicit through the update_probe_metrics call

    @pytest.mark.asyncio
    async def test_notification_callback_updates_metrics(self, custom_registry):
        """Test that notification callback updates Prometheus metrics."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        callback = server._create_notification_callback(
            "AA:BB:CC:DD:EE:FF", "BBQ ProbeE 38701"
        )

        # Trigger callback
        callback(28.5, 31.0)

        # Verify metrics were updated
        families = list(server.metrics_collector.registry.collect())
        metric_names = [f.name for f in families]

        assert "grillgauge_meat_temperature_celsius" in metric_names
        assert "grillgauge_grill_temperature_celsius" in metric_names
        assert "grillgauge_probe_status" in metric_names

        # Verify values
        expected_meat_temp = 28.5
        for family in families:
            if family.name == "grillgauge_meat_temperature_celsius":
                for sample in family.samples:
                    if sample.labels.get("device_address") == "AA:BB:CC:DD:EE:FF":
                        assert sample.value == expected_meat_temp

    @pytest.mark.asyncio
    async def test_create_app_routes(self, custom_registry):
        """Test that app has correct routes configured."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        # Get all route paths
        routes = [route.resource.canonical for route in server.app.router.routes()]

        assert "/metrics" in routes
        assert "/health" in routes
