import asyncio
import sys

from bleak import BleakClient
from bleak.exc import BleakDBusError

from .config import BLE_CONNECTION_TIMEOUT, DATA_SERVICE, TEMP_CHARACTERISTIC, logger


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

    def __init__(self, device_or_address):
        """Initialize probe with BLE device object or address string.

        Args:
            device_or_address: Either a BLEDevice object from BleakScanner (recommended for Pi)
                              or a string address (works on Mac, may timeout on Pi/BlueZ)
        """
        if isinstance(device_or_address, str):
            # Address string - backward compatibility, works on Mac
            self.device_address = device_or_address
            self.client = BleakClient(device_or_address, timeout=BLE_CONNECTION_TIMEOUT)
        else:
            # BLEDevice object from scanner - required for reliable Pi connections
            self.device_address = device_or_address.address
            self.client = BleakClient(device_or_address, timeout=BLE_CONNECTION_TIMEOUT)

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

    async def read_temperature(self) -> tuple[float | None, float | None]:  # noqa: PLR0911
        """Read current temperature via BLE notifications."""

        # Skip pairing on macOS (Core Bluetooth doesn't support manual pairing)
        # Only attempt pairing on Linux where BlueZ is available
        if sys.platform != "darwin":
            # Attempt pairing before reading notifications
            # This is required for devices that restrict notifications to paired clients
            try:
                await self.client.pair()
                logger.info("Successfully paired with device %s", self.device_address)
            except BleakDBusError as e:
                error_msg = str(e)

                # Check if device is already paired (not an error)
                if "AlreadyExists" in error_msg or "Already paired" in error_msg:
                    logger.info("Device %s already paired", self.device_address)
                else:
                    # Pairing failed - this is a fatal error in strict mode
                    logger.warning(
                        "Pairing failed for %s: %s. "
                        "Ensure bluetooth-agent service is running: "
                        "sudo systemctl status bluetooth-agent",
                        self.device_address,
                        e,
                    )
                    return None, None  # FAIL IMMEDIATELY
            except Exception as e:
                # Unexpected pairing error - fail immediately
                logger.warning(
                    "Unexpected pairing error for %s: %s", self.device_address, e
                )
                return None, None  # FAIL IMMEDIATELY
        else:
            logger.debug(
                "Skipping pairing on macOS (Core Bluetooth handles pairing automatically)"
            )

        try:
            services = self.client.services
        except Exception as e:
            logger.error("Failed to get services: %s", e)
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
