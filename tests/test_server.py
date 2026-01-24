from unittest.mock import AsyncMock, patch

import pytest
from prometheus_client import CollectorRegistry

from grillgauge.server import MetricsServer


class TestMetricsServer:
    """Test the MetricsServer class."""

    @pytest.fixture
    def custom_registry(self):
        """Custom Prometheus registry for testing."""
        return CollectorRegistry()

    @pytest.fixture
    def mock_env_manager(self):
        """Mock EnvManager for testing."""
        with patch("grillgauge.server.EnvManager") as mock_env:
            mock_env.return_value.list_probes.return_value = [
                {"mac": "AA:BB:CC:11:22:33", "name": "Test Probe"},
            ]
            yield mock_env

    @pytest.fixture
    def mock_grill_probe(self):
        """Mock GrillProbe for testing."""
        with patch("grillgauge.server.GrillProbe") as mock_probe:
            mock_instance = AsyncMock()
            mock_instance.read_temperature.return_value = (65.5, 225.0)
            mock_probe.return_value.__aenter__.return_value = mock_instance
            mock_probe.return_value.__aexit__.return_value = None
            yield mock_probe

    @pytest.fixture
    def mock_device_scanner(self):
        """Mock DeviceScanner for testing."""
        with patch("grillgauge.server.DeviceScanner") as mock_scanner:
            mock_instance = AsyncMock()
            mock_instance.return_value = [
                {
                    "address": "DD:EE:FF:00:11:22",
                    "name": "grillprobeE_11:22",
                    "classification": "probe",
                    "capabilities": {
                        "meat_temperature": 25.0,
                        "grill_temperature": 30.0,
                    },
                }
            ]
            mock_scanner.return_value = mock_instance
            yield mock_scanner

    def test_server_initialization(self, custom_registry):
        """Test MetricsServer initialization."""
        server = MetricsServer(host="127.0.0.1", port=9000, registry=custom_registry)
        assert server.host == "127.0.0.1"
        assert server.port == 9000  # noqa: PLR2004
        assert server.scan_task is None

    @pytest.mark.asyncio
    async def test_scan_probes_once_success(
        self, mock_env_manager, mock_grill_probe, custom_registry
    ):
        """Test successful probe scanning."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        await server._scan_probes_once()

        # Verify probe was read
        mock_grill_probe.assert_called_once_with("AA:BB:CC:11:22:33")
        mock_grill_probe.return_value.__aenter__.return_value.read_temperature.assert_called_once()

        # Verify metrics were updated
        # (This would need more detailed mocking of MetricsCollector)

    @pytest.mark.asyncio
    async def test_scan_probes_once_failure(self, mock_env_manager, custom_registry):
        """Test probe scanning with BLE failure."""
        with patch("grillgauge.server.GrillProbe") as mock_probe:
            # Simulate BLE failure
            mock_instance = AsyncMock()
            mock_instance.read_temperature.side_effect = Exception("BLE timeout")
            mock_probe.return_value.__aenter__.return_value = mock_instance
            mock_probe.return_value.__aexit__.return_value = None

            server = MetricsServer(host="127.0.0.1", registry=custom_registry)
            await server._scan_probes_once()

            # Verify probe was attempted
            mock_probe.assert_called_once_with("AA:BB:CC:11:22:33")
            # Metrics should be updated with status=0 (fault tolerance applies)

    def test_health_endpoint(self, custom_registry):
        """Test health endpoint creation."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)
        app = server._create_app()

        # Check that routes are registered
        routes = [str(route) for route in app.router.routes()]
        assert any("/metrics" in route for route in routes)
        assert any("/health" in route for route in routes)

    @pytest.mark.asyncio
    async def test_discover_new_devices_success(
        self, mock_device_scanner, custom_registry
    ):
        """Test successful device discovery."""
        server = MetricsServer(host="127.0.0.1", registry=custom_registry)

        await server._discover_new_devices()

        # Verify scanner was called
        mock_device_scanner.assert_called_once()
        # Verify scanner instance was awaited
        mock_device_scanner.return_value.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discover_new_devices_failure(self, custom_registry):
        """Test device discovery with scanner failure."""
        with patch("grillgauge.server.DeviceScanner") as mock_scanner:
            # Simulate scanner failure
            mock_instance = AsyncMock()
            mock_instance.side_effect = Exception("BLE discovery failed")
            mock_scanner.return_value = mock_instance

            server = MetricsServer(host="127.0.0.1", registry=custom_registry)

            # Should not raise, just log error
            await server._discover_new_devices()

            mock_scanner.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_new_devices_no_probes(self, custom_registry):
        """Test device discovery when no new probes found."""
        with patch("grillgauge.server.DeviceScanner") as mock_scanner:
            # Return empty list (no probes)
            mock_instance = AsyncMock()
            mock_instance.return_value = []
            mock_scanner.return_value = mock_instance

            server = MetricsServer(host="127.0.0.1", registry=custom_registry)
            await server._discover_new_devices()

            mock_scanner.assert_called_once()
