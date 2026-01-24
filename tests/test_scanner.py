import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.exc import BleakDBusError, BleakDeviceNotFoundError, BleakError

from grillgauge.scanner import DeviceScanner

DEFAULT_SCAN_TIMEOUT = 10.0

# Expected temperature values for testing
EXPECTED_MEAT_TEMP = 28.0
EXPECTED_GRILL_TEMP = 31.0


class TestDeviceScanner:
    @pytest.fixture
    def temp_env_file(self):
        """Class method fixture for temporary .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            yield f.name
        Path(f.name).unlink()

    @pytest.fixture
    def scanner(self, temp_env_file):
        """Class method fixture providing DeviceScanner instance."""
        scanner = DeviceScanner()
        scanner.env_manager.env_file = temp_env_file  # Override env file
        return scanner

    @pytest.fixture
    def mock_device(self):
        """Mock BLE device for testing."""
        device = MagicMock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device.name = "BBQ ProbeE 12345"
        return device

    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly."""
        assert scanner.timeout == DEFAULT_SCAN_TIMEOUT
        assert scanner.devices == []
        assert hasattr(scanner, "env_manager")

    @pytest.mark.asyncio
    async def test_process_device_timeout_error(self, scanner, mock_device):
        """Test device processing handles asyncio.TimeoutError correctly."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to raise TimeoutError on connection
            mock_probe = AsyncMock()
            mock_probe.__aenter__.side_effect = asyncio.TimeoutError()
            mock_probe_class.return_value = mock_probe

            # Process device should catch the timeout and log it
            await scanner._process_device(mock_device)

            # Device should not be added to scanner.devices
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_process_device_not_found_error(self, scanner, mock_device):
        """Test device processing handles BleakDeviceNotFoundError correctly."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to raise DeviceNotFoundError
            mock_probe = AsyncMock()
            mock_probe.__aenter__.side_effect = BleakDeviceNotFoundError(
                "AA:BB:CC:DD:EE:FF"
            )
            mock_probe_class.return_value = mock_probe

            # Process device should catch the error and log it
            await scanner._process_device(mock_device)

            # Device should not be added to scanner.devices
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_process_device_dbus_error(self, scanner, mock_device):
        """Test device processing handles BleakDBusError correctly."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to raise DBusError
            mock_probe = AsyncMock()
            mock_probe.__aenter__.side_effect = BleakDBusError(
                "org.bluez.Error.Failed", ["Connection failed"]
            )
            mock_probe_class.return_value = mock_probe

            # Process device should catch the error and log it
            await scanner._process_device(mock_device)

            # Device should not be added to scanner.devices
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_process_device_generic_bleak_error(self, scanner, mock_device):
        """Test device processing handles generic BleakError correctly."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to raise generic BleakError
            mock_probe = AsyncMock()
            mock_probe.__aenter__.side_effect = BleakError("Generic BLE failure")
            mock_probe_class.return_value = mock_probe

            # Process device should catch the error and log it
            await scanner._process_device(mock_device)

            # Device should not be added to scanner.devices
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_process_device_unexpected_error(self, scanner, mock_device):
        """Test device processing handles unexpected exceptions correctly."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to raise unexpected exception
            mock_probe = AsyncMock()
            mock_probe.__aenter__.side_effect = RuntimeError("Unexpected error")
            mock_probe_class.return_value = mock_probe

            # Process device should catch the error and log it with type name
            await scanner._process_device(mock_device)

            # Device should not be added to scanner.devices
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_process_device_success(self, scanner, mock_device):
        """Test successful device processing and registration."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock for successful connection and temperature read
            mock_probe = AsyncMock()
            mock_probe.read_temperature = AsyncMock(
                return_value=(EXPECTED_MEAT_TEMP, EXPECTED_GRILL_TEMP)
            )
            mock_probe.__aenter__.return_value = mock_probe
            mock_probe.__aexit__.return_value = None
            mock_probe_class.return_value = mock_probe

            # Process device
            await scanner._process_device(mock_device)

            # Device should be added to scanner.devices
            assert len(scanner.devices) == 1
            assert scanner.devices[0]["address"] == "AA:BB:CC:DD:EE:FF"
            assert scanner.devices[0]["name"] == "BBQ ProbeE 12345"
            assert (
                scanner.devices[0]["capabilities"]["meat_temperature"]
                == EXPECTED_MEAT_TEMP
            )
            assert (
                scanner.devices[0]["capabilities"]["grill_temperature"]
                == EXPECTED_GRILL_TEMP
            )

    @pytest.mark.asyncio
    async def test_process_device_failed_temperature_read(self, scanner, mock_device):
        """Test device processing when temperature read returns None."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to return None temperatures (read failure)
            mock_probe = AsyncMock()
            mock_probe.read_temperature = AsyncMock(return_value=(None, None))
            mock_probe.__aenter__.return_value = mock_probe
            mock_probe.__aexit__.return_value = None
            mock_probe_class.return_value = mock_probe

            # Process device
            await scanner._process_device(mock_device)

            # Device should NOT be added (temperature read failed)
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_process_device_no_name_uses_generated(self, scanner):
        """Test device processing generates name when device has no name."""
        # Mock device without name
        mock_device = MagicMock()
        mock_device.address = "BB:CC:DD:EE:FF:AA"
        mock_device.name = None
        mock_device.local_name = None

        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock for successful connection
            mock_probe = AsyncMock()
            mock_probe.read_temperature = AsyncMock(
                return_value=(EXPECTED_MEAT_TEMP, EXPECTED_GRILL_TEMP)
            )
            mock_probe.__aenter__.return_value = mock_probe
            mock_probe.__aexit__.return_value = None
            mock_probe_class.return_value = mock_probe

            # Process device
            await scanner._process_device(mock_device)

            # Device should use generated name
            assert len(scanner.devices) == 1
            assert scanner.devices[0]["name"] == "grillprobeE_F:AA"

    @pytest.mark.asyncio
    async def test_process_device_dbus_permission_error(self, scanner, mock_device):
        """Test device processing handles NotPermitted DBus error."""
        with patch("grillgauge.scanner.GrillProbe") as mock_probe_class:
            # Configure mock to raise NotPermitted error
            mock_probe = AsyncMock()
            mock_probe.__aenter__.side_effect = BleakDBusError(
                "org.bluez.Error.NotPermitted", ["Permission denied"]
            )
            mock_probe_class.return_value = mock_probe

            # Process device should catch and log with specific message
            await scanner._process_device(mock_device)

            # Device should not be added
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_scan_grillprobee_devices_success(self, scanner):
        """Test successful scan and device discovery."""
        # Mock BleakScanner.discover
        mock_device1 = MagicMock()
        mock_device1.address = "AA:BB:CC:DD:EE:FF"
        mock_device1.name = "BBQ ProbeE 12345"

        mock_device2 = MagicMock()
        mock_device2.address = "BB:CC:DD:EE:FF:AA"
        mock_device2.name = "BBQ ProbeE 67890"

        with (
            patch(
                "grillgauge.scanner.BleakScanner.discover",
                new_callable=AsyncMock,
                return_value=[mock_device1, mock_device2],
            ),
            patch("grillgauge.scanner.GrillProbe") as mock_probe_class,
        ):
            # Configure mock probe
            mock_probe = AsyncMock()
            mock_probe.read_temperature = AsyncMock(
                return_value=(EXPECTED_MEAT_TEMP, EXPECTED_GRILL_TEMP)
            )
            mock_probe.__aenter__.return_value = mock_probe
            mock_probe.__aexit__.return_value = None
            mock_probe_class.return_value = mock_probe

            # Run scan
            await scanner._scan_grillprobee_devices()

            # Should have found 2 devices
            assert len(scanner.devices) == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_scan_grillprobee_devices_no_devices_found(self, scanner):
        """Test scan when no devices are found."""
        with patch(
            "grillgauge.scanner.BleakScanner.discover",
            new_callable=AsyncMock,
            return_value=[],
        ):
            # Run scan
            await scanner._scan_grillprobee_devices()

            # Should have found 0 devices
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_scan_grillprobee_devices_retry_on_inprogress(self, scanner):
        """Test scan retries on InProgress error."""
        mock_device = MagicMock()
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_device.name = "BBQ ProbeE 12345"

        # First call raises InProgress, second succeeds
        discover_calls = [
            Exception("Operation already in progress"),
            [mock_device],
        ]

        async def mock_discover(*args, **kwargs):  # noqa: ARG001
            result = discover_calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with (
            patch(
                "grillgauge.scanner.BleakScanner.discover", side_effect=mock_discover
            ),
            patch("grillgauge.scanner.GrillProbe") as mock_probe_class,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            # Configure mock probe
            mock_probe = AsyncMock()
            mock_probe.read_temperature = AsyncMock(
                return_value=(EXPECTED_MEAT_TEMP, EXPECTED_GRILL_TEMP)
            )
            mock_probe.__aenter__.return_value = mock_probe
            mock_probe.__aexit__.return_value = None
            mock_probe_class.return_value = mock_probe

            # Run scan
            await scanner._scan_grillprobee_devices()

            # Should eventually succeed
            assert len(scanner.devices) == 1

    @pytest.mark.asyncio
    async def test_scan_grillprobee_devices_generic_error(self, scanner):
        """Test scan handles generic errors."""
        with patch(
            "grillgauge.scanner.BleakScanner.discover",
            new_callable=AsyncMock,
            side_effect=Exception("Generic BLE error"),
        ):
            # Run scan
            await scanner._scan_grillprobee_devices()

            # Should handle error gracefully
            assert len(scanner.devices) == 0

    @pytest.mark.asyncio
    async def test_call_method(self, scanner):
        """Test __call__ method invokes scan."""
        with patch(
            "grillgauge.scanner.BleakScanner.discover",
            new_callable=AsyncMock,
            return_value=[],
        ):
            # Call scanner as a function
            devices = await scanner()

            # Should return devices list
            assert devices == []
            assert devices is scanner.devices

    @pytest.mark.asyncio
    async def test_scan_with_custom_timeout(self):
        """Test scanner respects custom timeout."""
        custom_timeout = 5.0
        scanner = DeviceScanner(timeout=custom_timeout)

        assert scanner.timeout == custom_timeout
