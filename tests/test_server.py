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
