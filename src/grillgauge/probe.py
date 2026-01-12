import asyncio

from bleak import BleakClient

from .config import DATA_SERVICE, TEMP_CHARACTERISTIC, logger


class GrillProbe:
    """Handles BLE communication with a specific grillprobeE device."""

    # Temperature parsing constants
    MIN_TEMPERATURE_DATA_LENGTH = 7
    MEAT_TEMP_START_INDEX = 2
    MEAT_TEMP_END_INDEX = 4
    GRILL_TEMP_START_INDEX = 4
    GRILL_TEMP_END_INDEX = 6
    TEMP_DIVISOR = 10.0
    TEMP_OFFSET = 40.0

    def __init__(self, device_address: str):
        """Initialize probe with BLE device address."""
        self.device_address = device_address
        self.client = BleakClient(device_address, timeout=5.0)

    async def __aenter__(self):
        """Async context manager entry - connect to device."""
        await self.client.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect."""
        await self.client.disconnect()

    def read_device_name(self, device) -> str | None:
        """Read device name from BLE advertisement data."""
        # Try advertisement data first
        device_name = getattr(device, "name", None) or getattr(
            device, "local_name", None
        )
        if device_name:
            return device_name

        # Fallback to generated name
        return f"grillprobeE_{self.device_address[-4:]}"

    async def read_temperature(self) -> tuple[float | None, float | None]:
        """Read current temperature via BLE notifications."""
        try:
            services = self.client.services
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return None, None

        data_svc = services.get_service(DATA_SERVICE)
        if not data_svc:
            logger.error("Data service not found")
            return None, None

        temp_char = data_svc.get_characteristic(TEMP_CHARACTERISTIC)
        if not temp_char:
            logger.error("Temperature characteristic not found")
            return None, None

        # Set up notification handler
        notification_received = False
        received_data = None

        def notification_handler(_sender, data):
            nonlocal notification_received, received_data
            logger.debug(f"Received temperature notification: {data.hex()}")
            received_data = data
            notification_received = True

        # Subscribe to notifications
        try:
            await self.client.start_notify(temp_char.uuid, notification_handler)

            # Wait for notification (2 seconds)
            await asyncio.sleep(2.0)

            # Clean up notification subscription
            await self.client.stop_notify(temp_char.uuid)

        except Exception as e:
            logger.error(f"Notification handling failed: {e}")
            return None, None

        if notification_received and received_data:
            return self._parse_temperature(received_data)

        logger.warning("No temperature notifications received within timeout")
        return None, None

    def _parse_temperature(self, data) -> tuple[float | None, float | None]:
        """Parse 7-byte temperature notification from grillprobeE."""
        if len(data) < self.MIN_TEMPERATURE_DATA_LENGTH:
            logger.warning(f"Temperature data too short: {len(data)} bytes")
            return None, None

        try:
            meat_raw = int.from_bytes(
                data[self.MEAT_TEMP_START_INDEX : self.MEAT_TEMP_END_INDEX],
                byteorder="little",
                signed=True,
            )
        except ValueError as e:
            logger.warning(f"Failed to parse meat temperature: {e}")
            return None, None

        try:
            grill_raw = int.from_bytes(
                data[self.GRILL_TEMP_START_INDEX : self.GRILL_TEMP_END_INDEX],
                byteorder="little",
                signed=True,
            )
        except ValueError as e:
            logger.warning(f"Failed to parse grill temperature: {e}")
            return None, None

        meat_temp = (meat_raw / self.TEMP_DIVISOR) - self.TEMP_OFFSET
        grill_temp = (grill_raw / self.TEMP_DIVISOR) - self.TEMP_OFFSET

        return meat_temp, grill_temp
