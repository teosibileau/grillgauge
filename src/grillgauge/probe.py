import asyncio
import contextlib

from bleak import BleakClient
from bleak.exc import BleakDeviceNotFoundError

from .config import BLE_CONNECTION_TIMEOUT, TEMP_CHARACTERISTIC, logger


class GrillProbe:
    """Handles persistent BLE connection with a grillprobeE device."""

    # Temperature parsing constants
    MIN_TEMPERATURE_DATA_LENGTH = 7
    MEAT_TEMP_START_INDEX = 2
    MEAT_TEMP_END_INDEX = 4
    GRILL_TEMP_START_INDEX = 4
    GRILL_TEMP_END_INDEX = 6
    TEMP_DIVISOR = 10.0
    TEMP_OFFSET = 40.0

    # Reconnection constants
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 5.0

    def __init__(self, device_or_address, notification_callback=None):
        """Initialize probe with persistent connection.

        Args:
            device_or_address: Either a BLEDevice object from BleakScanner (recommended for Pi)
                              or a string address (works on Mac, may timeout on Pi/BlueZ)
            notification_callback: Callback function(meat_temp, grill_temp) called on each notification
        """
        if isinstance(device_or_address, str):
            self.device_address = device_or_address
            self._initial_device = device_or_address
        else:
            self.device_address = device_or_address.address
            self._initial_device = device_or_address

        self.client = None
        self.notification_callback = notification_callback
        self._connected = False
        self._subscribed = False
        self._reconnect_task = None
        self._last_meat_temp = None
        self._last_grill_temp = None

    async def connect(self):
        """Connect to device and subscribe to notifications."""
        logger.info(f"Connecting to {self.device_address}...")

        try:
            # First try with initial device (BLEDevice object or address string)
            self.client = BleakClient(
                self._initial_device, timeout=BLE_CONNECTION_TIMEOUT
            )
            await self.client.connect()
            self._connected = True
            logger.info(f"Connected to {self.device_address}")

            # Subscribe to notifications
            await self._subscribe_notifications()
        except BleakDeviceNotFoundError:
            # Device object is stale, fall back to address string
            logger.warning(
                f"BLEDevice object stale for {self.device_address}, retrying with address string..."
            )
            try:
                self.client = BleakClient(
                    self.device_address, timeout=BLE_CONNECTION_TIMEOUT
                )
                await self.client.connect()
                self._connected = True
                logger.info(f"Connected to {self.device_address} using address string")

                # Subscribe to notifications
                await self._subscribe_notifications()
            except Exception as e:
                logger.error(
                    f"Failed to connect to {self.device_address} with address string: {e}"
                )
                self._connected = False
                return False
            else:
                return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.device_address}: {e}")
            self._connected = False
            return False
        else:
            return True

    async def _subscribe_notifications(self):
        """Subscribe to temperature notifications."""
        if not self._connected or not self.client:
            logger.warning("Cannot subscribe - not connected")
            return False

        try:
            # Clean up any stale subscriptions
            with contextlib.suppress(Exception):
                await self.client.stop_notify(TEMP_CHARACTERISTIC)
                logger.debug("Cleaned stale notification state")

            # Subscribe with timeout
            await asyncio.wait_for(
                self.client.start_notify(
                    TEMP_CHARACTERISTIC, self._notification_handler
                ),
                timeout=5.0,
            )
            self._subscribed = True
            logger.info(f"Subscribed to notifications for {self.device_address}")
        except asyncio.TimeoutError:
            logger.error(
                f"Timeout subscribing to notifications for {self.device_address}"
            )
            self._subscribed = False
            return False
        except Exception as e:
            logger.error(f"Failed to subscribe to notifications: {e}")
            self._subscribed = False
            return False
        else:
            return True

    def _notification_handler(self, sender, data):
        """Handle incoming temperature notifications."""
        logger.debug(f"Received notification from {self.device_address}: {data.hex()}")

        meat_temp, grill_temp = self._parse_temperature(data)

        if meat_temp is not None and grill_temp is not None:
            self._last_meat_temp = meat_temp
            self._last_grill_temp = grill_temp

            logger.debug(
                f"{self.device_address}: Meat={meat_temp:.1f}°C, Grill={grill_temp:.1f}°C"
            )

            # Call user callback if provided
            if self.notification_callback:
                try:
                    self.notification_callback(meat_temp, grill_temp)
                except Exception as e:
                    logger.error(f"Error in notification callback: {e}")

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
            grill_raw = int.from_bytes(
                data[self.GRILL_TEMP_START_INDEX : self.GRILL_TEMP_END_INDEX],
                byteorder="little",
                signed=True,
            )

            meat_temp = (meat_raw / self.TEMP_DIVISOR) - self.TEMP_OFFSET
            grill_temp = (grill_raw / self.TEMP_DIVISOR) - self.TEMP_OFFSET
        except Exception as e:
            logger.warning(f"Failed to parse temperature: {e}")
            return None, None
        else:
            return meat_temp, grill_temp

    async def disconnect(self):
        """Disconnect from device."""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task

        if self.client and self._connected:
            try:
                if self._subscribed:
                    await self.client.stop_notify(TEMP_CHARACTERISTIC)
                    self._subscribed = False
                await self.client.disconnect()
                logger.info(f"Disconnected from {self.device_address}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connected = False

    async def ensure_connected(self):
        """Ensure connection is active, reconnect if needed."""
        if not self._connected or not self.client or not self.client.is_connected:
            logger.warning(f"Connection lost to {self.device_address}, reconnecting...")
            await self._reconnect()

    async def _reconnect(self):
        """Reconnect to device with exponential backoff."""
        for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
            logger.info(
                f"Reconnection attempt {attempt + 1}/{self.MAX_RECONNECT_ATTEMPTS}"
            )

            # Clean up old client
            if self.client:
                with contextlib.suppress(Exception):
                    await self.client.disconnect()

            self._connected = False
            self._subscribed = False

            # Try to reconnect
            if await self.connect():
                logger.info(f"Successfully reconnected to {self.device_address}")
                return True

            # Wait before retry with exponential backoff
            delay = self.RECONNECT_DELAY * (2**attempt)
            logger.info(f"Waiting {delay}s before next reconnection attempt...")
            await asyncio.sleep(delay)

        logger.error(
            f"Failed to reconnect to {self.device_address} after {self.MAX_RECONNECT_ATTEMPTS} attempts"
        )
        return False

    @property
    def is_connected(self):
        """Check if device is connected."""
        return self._connected and self.client and self.client.is_connected

    @property
    def last_temperature(self):
        """Get last received temperature reading."""
        return self._last_meat_temp, self._last_grill_temp
