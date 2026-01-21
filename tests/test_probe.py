from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from grillgauge.probe import GrillProbe

# Expected temperature values for testing
EXPECTED_MEAT_TEMP = 28.0
EXPECTED_GRILL_TEMP = 31.0


class TestGrillProbe:
    @pytest.fixture
    def mock_bleak_client(self):
        """Simple BleakClient mock."""
        client = AsyncMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client

    @pytest.fixture
    def grill_probe(self):
        """GrillProbe instance for testing."""
        return GrillProbe("AA:BB:CC:DD:EE:FF")

    def test_grill_probe_initialization(self, grill_probe):
        """Test GrillProbe initializes with device address."""
        assert grill_probe.device_address == "AA:BB:CC:DD:EE:FF"
        assert grill_probe.client is not None

    def test_grill_probe_initialization_with_device_object(self):
        """Test GrillProbe initializes with BLEDevice object from scanner."""
        # Mock BLEDevice object (what BleakScanner.discover() returns)
        mock_device = MagicMock()
        mock_device.address = "BB:CC:DD:EE:FF:AA"
        mock_device.name = "BBQ ProbeE 12345"

        # Initialize with device object
        probe = GrillProbe(mock_device)

        # Should extract address from device object
        assert probe.device_address == "BB:CC:DD:EE:FF:AA"
        assert probe.client is not None

    @pytest.mark.asyncio
    async def test_context_manager_connection(self, grill_probe, mock_bleak_client):
        """Test context manager connects and disconnects properly."""
        # Replace the client with our mock
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            assert grill_probe.client is not None

        mock_bleak_client.connect.assert_called_once()
        mock_bleak_client.disconnect.assert_called_once()

    def test_read_device_name_from_advertisement(self, grill_probe):
        """Test reading device name when available in advertisement."""
        mock_device = MagicMock()
        mock_device.name = "BBQ ProbeE 26012"

        name = grill_probe.read_device_name(mock_device)
        assert name == "BBQ ProbeE 26012"

    def test_read_device_name_fallback(self, grill_probe):
        """Test device name fallback when advertisement doesn't have it."""
        mock_device = MagicMock()
        mock_device.name = None
        mock_device.local_name = None

        name = grill_probe.read_device_name(mock_device)
        assert name == "grillprobeE_E:FF"

    @pytest.mark.asyncio
    async def test_read_temperature_success(self, grill_probe, mock_bleak_client):
        """Test successful temperature reading."""
        # Mock services object
        mock_services = MagicMock()
        mock_service = MagicMock()
        mock_char = MagicMock()

        mock_bleak_client.services = mock_services
        mock_services.get_service.return_value = mock_service
        mock_service.get_characteristic.return_value = mock_char

        # Mock notification with valid data
        test_data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        async def mock_start_notify(_uuid, callback):
            callback(None, test_data)  # Simulate notification

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_bleak_client.stop_notify = AsyncMock()

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        assert meat_temp == EXPECTED_MEAT_TEMP
        assert grill_temp == EXPECTED_GRILL_TEMP

    @pytest.mark.asyncio
    async def test_read_temperature_connection_error(
        self, grill_probe, mock_bleak_client
    ):
        """Test temperature reading with connection error."""
        # Make accessing services raise an exception
        type(mock_bleak_client).services = PropertyMock(
            side_effect=Exception("Connection failed")
        )

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        assert meat_temp is None
        assert grill_temp is None

    @pytest.mark.asyncio
    async def test_read_temperature_invalid_data(self, grill_probe, mock_bleak_client):
        """Test temperature reading with invalid notification data."""
        # Mock service setup
        mock_services = MagicMock()
        mock_service = MagicMock()
        mock_char = MagicMock()

        mock_bleak_client.services = mock_services
        mock_services.get_service.return_value = mock_service
        mock_service.get_characteristic.return_value = mock_char

        # Mock notification with invalid data (too short)
        async def mock_start_notify(_uuid, callback):
            callback(None, bytes([0xFF, 0xFF]))  # Only 2 bytes

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_bleak_client.stop_notify = AsyncMock()

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        assert meat_temp is None  # Should fail parsing
        assert grill_temp is None

    @pytest.mark.asyncio
    async def test_read_temperature_attempts_pairing(
        self, grill_probe, mock_bleak_client
    ):
        """Test that pairing is attempted before reading temperature."""
        # Mock successful pairing
        mock_bleak_client.pair = AsyncMock(return_value=None)

        # Mock services and notification
        mock_services = MagicMock()
        mock_service = MagicMock()
        mock_char = MagicMock()

        mock_bleak_client.services = mock_services
        mock_services.get_service.return_value = mock_service
        mock_service.get_characteristic.return_value = mock_char

        # Mock notification with valid data
        test_data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        async def mock_start_notify(_uuid, callback):
            callback(None, test_data)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_bleak_client.stop_notify = AsyncMock()

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        # Verify pairing was called
        mock_bleak_client.pair.assert_called_once()

        # Verify temperature reading succeeded
        assert meat_temp == EXPECTED_MEAT_TEMP
        assert grill_temp == EXPECTED_GRILL_TEMP

    @pytest.mark.asyncio
    async def test_read_temperature_fails_if_pairing_fails(
        self, grill_probe, mock_bleak_client
    ):
        """Test that temperature reading fails immediately if pairing fails."""
        from bleak.exc import BleakDBusError

        # Mock pairing failure
        mock_bleak_client.pair = AsyncMock(
            side_effect=BleakDBusError("org.bluez.Error.Failed", "Pairing failed")
        )

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        # Should fail immediately - return None for both temperatures
        assert meat_temp is None
        assert grill_temp is None

        # Verify pairing was attempted
        mock_bleak_client.pair.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_temperature_handles_already_paired(
        self, grill_probe, mock_bleak_client
    ):
        """Test graceful handling when device is already paired."""
        from bleak.exc import BleakDBusError

        # Mock "already paired" error
        mock_bleak_client.pair = AsyncMock(
            side_effect=BleakDBusError(
                "org.bluez.Error.AlreadyExists", "Already paired"
            )
        )

        # Mock services and notification
        mock_services = MagicMock()
        mock_service = MagicMock()
        mock_char = MagicMock()

        mock_bleak_client.services = mock_services
        mock_services.get_service.return_value = mock_service
        mock_service.get_characteristic.return_value = mock_char

        # Mock notification with valid data
        test_data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        async def mock_start_notify(_uuid, callback):
            callback(None, test_data)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_start_notify)
        mock_bleak_client.stop_notify = AsyncMock()

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        # Should succeed - already paired is not an error
        assert meat_temp == EXPECTED_MEAT_TEMP
        assert grill_temp == EXPECTED_GRILL_TEMP

    @pytest.mark.asyncio
    async def test_read_temperature_handles_permission_error(
        self, grill_probe, mock_bleak_client
    ):
        """Test handling of NotPermitted error during pairing."""
        from bleak.exc import BleakDBusError

        # Mock permission denied error
        mock_bleak_client.pair = AsyncMock(
            side_effect=BleakDBusError(
                "org.bluez.Error.NotPermitted", "Operation not permitted"
            )
        )

        # Replace the client
        grill_probe.client = mock_bleak_client

        async with grill_probe:
            meat_temp, grill_temp = await grill_probe.read_temperature()

        # Should fail immediately
        assert meat_temp is None
        assert grill_temp is None

        # Verify pairing was attempted
        mock_bleak_client.pair.assert_called_once()
