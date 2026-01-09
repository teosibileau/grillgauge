import asyncio

from bleak import BleakClient, BleakScanner

from .config import logger
from .env import EnvManager

# grillprobeE service UUIDs
DATA_SERVICE = "0000fb00-0000-1000-8000-00805f9b34fb"
TEMP_CHARACTERISTIC = "0000fb02-0000-1000-8000-00805f9b34fb"

# Constants for scanner behavior
DEFAULT_SCAN_TIMEOUT = 10.0
CLIENT_CONNECTION_TIMEOUT = 5.0

# Constants for temperature parsing
MIN_TEMPERATURE_DATA_LENGTH = 7
MEAT_TEMP_START_INDEX = 2
MEAT_TEMP_END_INDEX = 4
GRILL_TEMP_START_INDEX = 4
GRILL_TEMP_END_INDEX = 6
TEMP_DIVISOR = 10.0
TEMP_OFFSET = 40.0


class DeviceScanner:
    def __init__(self, timeout: float = DEFAULT_SCAN_TIMEOUT):
        self.env_manager = EnvManager()
        self.timeout = timeout
        self.devices = []

    async def __call__(self):
        await self._scan_grillprobee_devices()
        return self.devices

    async def _scan_grillprobee_devices(self):
        logger.info("Scanning for grillprobeE devices...")

        try:
            # Discover devices advertising the data service (temporarily less restrictive)
            devices = await BleakScanner.discover(
                timeout=self.timeout, service_uuids=[DATA_SERVICE]
            )

            if not devices:
                logger.info("No grillprobeE devices found")
                return

            logger.info(f"Found {len(devices)} potential grillprobeE devices")

            for device in devices:
                await self._process_device(device)

        except Exception as e:
            logger.error(f"Scan failed: {e}")

    async def _process_device(self, device):
        # Get device name from advertisement data (no exceptions expected)
        device_name = getattr(device, "name", None) or getattr(
            device, "local_name", None
        )
        if device_name:
            logger.info(f"Device name from advertisement: {device_name}")
        else:
            # Fallback to generated name if advertisement doesn't have it
            device_name = f"grillprobeE_{device.address[-4:]}"
            logger.info(f"Using generated device name: {device_name}")

        # Connect to device (this can fail)
        try:
            async with BleakClient(
                device.address, timeout=CLIENT_CONNECTION_TIMEOUT
            ) as client:
                logger.info(f"Processing device: {device.address}")

                # Read temperature data (mandatory)
                temp_data = await self._read_temperature_data(client)
                if not temp_data:
                    logger.error(
                        f"Failed to read temperature data from {device.address}"
                    )
                    return

        except Exception as e:
            logger.error(f"Failed to connect to device {device.address}: {e}")
            return

        # Parse temperatures (binary parsing can fail)
        meat_temp, grill_temp = self._parse_temperature(temp_data)
        if meat_temp is None and grill_temp is None:
            logger.error(f"Invalid temperature data from {device.address}")
            return

        logger.info(f"Meat temp: {meat_temp:.1f}°C, Grill temp: {grill_temp:.1f}°C")

        # Register device (no exceptions expected)
        self.env_manager.add_probe(device.address, device_name)

        device_info = {
            "address": device.address,
            "name": device_name,
            "classification": "probe",
            "capabilities": {
                "meat_temperature": meat_temp,
                "grill_temperature": grill_temp,
            },
        }

        self.devices.append(device_info)
        logger.info(f"Successfully registered: {device_name}")

    async def _read_temperature_data(self, client):
        # Get services (this can fail if connection is bad)
        try:
            services = client.services
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return None

        data_svc = services.get_service(DATA_SERVICE)
        if not data_svc:
            logger.error("Data service not found")
            return None

        temp_char = data_svc.get_characteristic(TEMP_CHARACTERISTIC)
        if not temp_char:
            logger.error("Temperature characteristic not found")
            return None

        # Set up notification handler for temperature data
        notification_received = False
        received_data = None

        def notification_handler(sender, data):
            nonlocal notification_received, received_data
            logger.debug(
                f"Received temperature notification: {data.hex()} sender: {sender}"
            )
            received_data = data
            notification_received = True

        # Subscribe to notifications (this can fail)
        try:
            await client.start_notify(temp_char.uuid, notification_handler)

            # Wait for notification (2 seconds, same as working version)
            await asyncio.sleep(2.0)

            # Clean up notification subscription
            await client.stop_notify(temp_char.uuid)

        except Exception as e:
            logger.error(f"Notification handling failed: {e}")
            return None

        if notification_received and received_data:
            return received_data

        logger.warning("No temperature notifications received within timeout")
        return None

    def _parse_temperature(self, data):
        if len(data) < MIN_TEMPERATURE_DATA_LENGTH:
            logger.warning(f"Temperature data too short: {len(data)} bytes")
            return None, None

        try:
            meat_raw = int.from_bytes(
                data[MEAT_TEMP_START_INDEX:MEAT_TEMP_END_INDEX],
                byteorder="little",
                signed=True,
            )
        except ValueError as e:
            logger.warning(f"Failed to parse meat temperature: {e}")
            return None, None

        try:
            grill_raw = int.from_bytes(
                data[GRILL_TEMP_START_INDEX:GRILL_TEMP_END_INDEX],
                byteorder="little",
                signed=True,
            )
        except ValueError as e:
            logger.warning(f"Failed to parse grill temperature: {e}")
            return None, None

        meat_temp = (meat_raw / TEMP_DIVISOR) - TEMP_OFFSET
        grill_temp = (grill_raw / TEMP_DIVISOR) - TEMP_OFFSET

        return meat_temp, grill_temp
