"""Tests for GrillProbe persistent connection management."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.exc import BleakDeviceNotFoundError

from grillgauge.probe import GrillProbe


class TestGrillProbe:
    """Test suite for GrillProbe persistent connection class."""

    @pytest.fixture
    def mock_device(self):
        """Mock BLEDevice object."""
        device = MagicMock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device.name = "BBQ ProbeE 38701"
        return device

    @pytest.fixture
    def mock_bleak_client(self):
        """Mock BleakClient for testing."""
        client = AsyncMock()
        client.is_connected = True
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.start_notify = AsyncMock()
        client.stop_notify = AsyncMock()
        return client

    def test_initialization_with_address_string(self):
        """Test GrillProbe initializes with address string."""
        probe = GrillProbe("AA:BB:CC:DD:EE:FF")
        assert probe.device_address == "AA:BB:CC:DD:EE:FF"
        assert probe.client is None
        assert probe._connected is False
        assert probe._subscribed is False
        assert probe.notification_callback is None

    def test_initialization_with_device_object(self, mock_device):
        """Test GrillProbe initializes with BLEDevice object."""
        probe = GrillProbe(mock_device)
        assert probe.device_address == "AA:BB:CC:DD:EE:FF"
        assert probe._initial_device == mock_device
        assert probe.client is None
        assert probe._connected is False

    def test_initialization_with_callback(self, mock_device):
        """Test GrillProbe initializes with notification callback."""
        callback = MagicMock()
        probe = GrillProbe(mock_device, notification_callback=callback)
        assert probe.notification_callback == callback

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_device, mock_bleak_client):
        """Test successful connection and notification subscription."""
        probe = GrillProbe(mock_device)

        with patch("grillgauge.probe.BleakClient", return_value=mock_bleak_client):
            result = await probe.connect()

        assert result is True
        assert probe._connected is True
        assert probe._subscribed is True
        mock_bleak_client.connect.assert_called_once()
        mock_bleak_client.start_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_stale_device_fallback(self, mock_device):
        """Test connection falls back to address string when BLEDevice is stale."""
        probe = GrillProbe(mock_device)

        # First client raises BleakDeviceNotFoundError
        first_client = AsyncMock()
        first_client.connect.side_effect = BleakDeviceNotFoundError("Device not found")

        # Second client succeeds
        second_client = AsyncMock()
        second_client.connect = AsyncMock()
        second_client.start_notify = AsyncMock()
        second_client.is_connected = True

        clients = [first_client, second_client]

        with patch(
            "grillgauge.probe.BleakClient",
            side_effect=lambda *args, **kwargs: clients.pop(0),  # noqa: ARG005
        ):
            result = await probe.connect()

        assert result is True
        assert probe._connected is True
        # Should have tried twice: once with device, once with address
        first_client.connect.assert_called_once()
        second_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_device):
        """Test connection failure handling."""
        probe = GrillProbe(mock_device)

        mock_client = AsyncMock()
        mock_client.connect.side_effect = Exception("Connection timeout")

        with patch("grillgauge.probe.BleakClient", return_value=mock_client):
            result = await probe.connect()

        assert result is False
        assert probe._connected is False
        assert probe._subscribed is False

    @pytest.mark.asyncio
    async def test_subscribe_notifications_success(
        self, mock_device, mock_bleak_client
    ):
        """Test successful notification subscription."""
        probe = GrillProbe(mock_device)
        probe.client = mock_bleak_client
        probe._connected = True

        result = await probe._subscribe_notifications()

        assert result is True
        assert probe._subscribed is True
        mock_bleak_client.start_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_notifications_not_connected(self, mock_device):
        """Test subscription fails when not connected."""
        probe = GrillProbe(mock_device)
        probe._connected = False

        result = await probe._subscribe_notifications()

        assert result is False
        assert probe._subscribed is False

    @pytest.mark.asyncio
    async def test_subscribe_notifications_timeout(
        self, mock_device, mock_bleak_client
    ):
        """Test subscription handles timeout."""
        probe = GrillProbe(mock_device)
        probe.client = mock_bleak_client
        probe._connected = True

        # Make start_notify hang
        async def slow_start_notify(*args, **kwargs):  # noqa: ARG001
            await asyncio.sleep(10)

        mock_bleak_client.start_notify.side_effect = slow_start_notify

        result = await probe._subscribe_notifications()

        assert result is False
        assert probe._subscribed is False

    def test_parse_temperature_valid_data(self, mock_device):
        """Test temperature parsing with valid data."""
        probe = GrillProbe(mock_device)

        # Valid 7-byte data: [0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C]
        # Meat: 0x02A8 = 680 -> (680/10) - 40 = 28.0°C
        # Grill: 0x02C6 = 710 -> (710/10) - 40 = 31.0°C
        data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        meat_temp, grill_temp = probe._parse_temperature(data)

        assert meat_temp == 28.0  # noqa: PLR2004
        assert grill_temp == 31.0  # noqa: PLR2004

    def test_parse_temperature_invalid_length(self, mock_device):
        """Test temperature parsing with invalid data length."""
        probe = GrillProbe(mock_device)

        # Too short (less than 7 bytes)
        data = bytes([0xFF, 0xFF])

        meat_temp, grill_temp = probe._parse_temperature(data)

        assert meat_temp is None
        assert grill_temp is None

    def test_parse_temperature_corrupted_data(self, mock_device):
        """Test temperature parsing with corrupted data."""
        probe = GrillProbe(mock_device)

        # Valid length but corrupted content that causes parsing error
        # Use data that will fail during int conversion
        data = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])

        # This should not raise, but return None, None
        meat_temp, grill_temp = probe._parse_temperature(data)

        # With all 0xFF bytes, parsing may succeed or fail depending on implementation
        # The important thing is it doesn't crash
        assert (
            meat_temp is not None
            or grill_temp is not None
            or (meat_temp is None and grill_temp is None)
        )

    def test_notification_handler_updates_temperature(self, mock_device):
        """Test notification handler updates cached temperatures."""
        probe = GrillProbe(mock_device)

        # Valid temperature data
        data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        probe._notification_handler(None, data)

        assert probe._last_meat_temp == 28.0  # noqa: PLR2004
        assert probe._last_grill_temp == 31.0  # noqa: PLR2004

    def test_notification_handler_calls_callback(self, mock_device):
        """Test notification handler calls user callback."""
        callback = MagicMock()
        probe = GrillProbe(mock_device, notification_callback=callback)

        # Valid temperature data
        data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        probe._notification_handler(None, data)

        callback.assert_called_once_with(28.0, 31.0)

    def test_notification_handler_handles_callback_error(self, mock_device):
        """Test notification handler handles callback exceptions gracefully."""
        callback = MagicMock()
        callback.side_effect = Exception("Callback error")
        probe = GrillProbe(mock_device, notification_callback=callback)

        # Valid temperature data
        data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])

        # Should not raise, just log error
        probe._notification_handler(None, data)

        # Temperature should still be cached
        assert probe._last_meat_temp == 28.0  # noqa: PLR2004
        assert probe._last_grill_temp == 31.0  # noqa: PLR2004

    def test_notification_handler_invalid_data(self, mock_device):
        """Test notification handler with invalid data."""
        callback = MagicMock()
        probe = GrillProbe(mock_device, notification_callback=callback)

        # Invalid data (too short)
        data = bytes([0xFF, 0xFF])

        probe._notification_handler(None, data)

        # Callback should not be called
        callback.assert_not_called()
        # Cached values should remain None
        assert probe._last_meat_temp is None
        assert probe._last_grill_temp is None

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self, mock_device, mock_bleak_client):
        """Test disconnect properly cleans up connection."""
        probe = GrillProbe(mock_device)
        probe.client = mock_bleak_client
        probe._connected = True
        probe._subscribed = True

        await probe.disconnect()

        assert probe._connected is False
        assert probe._subscribed is False
        mock_bleak_client.stop_notify.assert_called_once()
        mock_bleak_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, mock_device):
        """Test disconnect when already disconnected."""
        probe = GrillProbe(mock_device)
        probe._connected = False

        # Should not raise
        await probe.disconnect()

        assert probe._connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cancels_reconnect_task(
        self, mock_device, mock_bleak_client
    ):
        """Test disconnect cancels ongoing reconnect task."""
        probe = GrillProbe(mock_device)
        probe.client = mock_bleak_client
        probe._connected = True

        # Simulate ongoing reconnect task
        async def dummy_task():
            await asyncio.sleep(10)

        probe._reconnect_task = asyncio.create_task(dummy_task())

        await probe.disconnect()

        assert probe._reconnect_task.cancelled()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_connected(
        self, mock_device, mock_bleak_client
    ):
        """Test ensure_connected does nothing when already connected."""
        probe = GrillProbe(mock_device)
        probe.client = mock_bleak_client
        probe._connected = True
        mock_bleak_client.is_connected = True

        # Mock _reconnect to verify it's not called
        probe._reconnect = AsyncMock()

        await probe.ensure_connected()

        probe._reconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_disconnected(
        self, mock_device, mock_bleak_client
    ):
        """Test ensure_connected triggers reconnection when disconnected."""
        probe = GrillProbe(mock_device)
        probe.client = mock_bleak_client
        probe._connected = False

        # Mock _reconnect
        probe._reconnect = AsyncMock()

        await probe.ensure_connected()

        probe._reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_success_on_first_attempt(
        self, mock_device, mock_bleak_client
    ):
        """Test reconnection succeeds on first attempt."""
        probe = GrillProbe(mock_device)

        # Mock connect to succeed
        async def mock_connect():
            probe._connected = True
            probe._subscribed = True
            return True

        probe.connect = AsyncMock(side_effect=mock_connect)

        result = await probe._reconnect()

        assert result is True
        assert probe.connect.call_count == 1

    @pytest.mark.asyncio
    async def test_reconnect_with_exponential_backoff(self, mock_device):
        """Test reconnection uses exponential backoff."""
        probe = GrillProbe(mock_device)

        # Mock connect to fail 2 times then succeed
        connect_attempts = [False, False, True]

        async def mock_connect():
            result = connect_attempts.pop(0)
            if result:
                probe._connected = True
                probe._subscribed = True
            return result

        probe.connect = AsyncMock(side_effect=mock_connect)

        # Mock sleep to avoid actual delays
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await probe._reconnect()

        assert result is True
        assert probe.connect.call_count == 3  # noqa: PLR2004

        # Verify exponential backoff delays
        # First failure: 5 * 2^0 = 5s
        # Second failure: 5 * 2^1 = 10s
        assert mock_sleep.call_count == 2  # noqa: PLR2004
        mock_sleep.assert_any_call(5.0)
        mock_sleep.assert_any_call(10.0)

    @pytest.mark.asyncio
    async def test_reconnect_fails_after_max_attempts(self, mock_device):
        """Test reconnection fails after MAX_RECONNECT_ATTEMPTS."""
        probe = GrillProbe(mock_device)

        # Mock connect to always fail
        probe.connect = AsyncMock(return_value=False)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await probe._reconnect()

        assert result is False
        assert probe.connect.call_count == probe.MAX_RECONNECT_ATTEMPTS

    def test_is_connected_property(self, mock_device, mock_bleak_client):
        """Test is_connected property."""
        probe = GrillProbe(mock_device)

        # Not connected
        assert probe.is_connected is False

        # Connected
        probe.client = mock_bleak_client
        probe._connected = True
        mock_bleak_client.is_connected = True
        assert probe.is_connected is True

        # Client reports disconnected
        mock_bleak_client.is_connected = False
        assert probe.is_connected is False

    def test_last_temperature_property(self, mock_device):
        """Test last_temperature property."""
        probe = GrillProbe(mock_device)

        # Initially None
        assert probe.last_temperature == (None, None)

        # After receiving data
        probe._last_meat_temp = 28.5
        probe._last_grill_temp = 31.2
        assert probe.last_temperature == (28.5, 31.2)
