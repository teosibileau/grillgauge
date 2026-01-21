import asyncio

from bleak import BleakScanner
from bleak.exc import BleakDBusError, BleakDeviceNotFoundError, BleakError

from .config import BLE_CONNECTION_TIMEOUT, DATA_SERVICE, logger
from .env import EnvManager
from .probe import GrillProbe


class DeviceScanner:
    # Constants for scanner behavior
    DEFAULT_SCAN_TIMEOUT = 10.0

    def __init__(self, timeout: float = DEFAULT_SCAN_TIMEOUT):
        self.env_manager = EnvManager()
        self.timeout = timeout
        self.devices = []

    async def __call__(self):
        await self._scan_grillprobee_devices()
        return self.devices

    async def _scan_grillprobee_devices(self):
        logger.info("Scanning for grillprobeE devices...")

        # BLE discovery is the main failure point for system-level issues
        try:
            devices = await BleakScanner.discover(
                timeout=self.timeout, service_uuids=[DATA_SERVICE]
            )
        except Exception as e:
            logger.error(f"BLE discovery failed: {e}")
            return

        # Rest of logic is safe and device processing has its own error handling
        if not devices:
            logger.info("No grillprobeE devices found")
            return

        logger.info(f"Found {len(devices)} potential grillprobeE devices")

        for device in devices:
            await self._process_device(device)

    async def _process_device(self, device):
        # Get device name from advertisement data
        device_name = getattr(device, "name", None) or getattr(
            device, "local_name", None
        )
        if device_name:
            logger.info(f"Device name from advertisement: {device_name}")
        else:
            # Fallback to generated name
            device_name = f"grillprobeE_{device.address[-4:]}"
            logger.info(f"Using generated device name: {device_name}")

        # Use GrillProbe to read temperature data
        try:
            async with GrillProbe(device) as probe:
                logger.info(f"Processing device: {device.address}")

                # Read temperature data via notifications
                meat_temp, grill_temp = await probe.read_temperature()
                if meat_temp is None and grill_temp is None:
                    logger.error(
                        f"Failed to read temperature data from {device.address}"
                    )
                    return

        except asyncio.TimeoutError:
            logger.error(
                f"Connection timeout for device {device.address} ({BLE_CONNECTION_TIMEOUT}s limit)"
            )
            return
        except BleakDeviceNotFoundError as e:
            logger.error(f"Device not found: {device.address}: {e}")
            return
        except BleakDBusError as e:
            error_msg = str(e)

            # Check for permission/pairing errors that indicate bluetooth-agent issues
            if "NotPermitted" in error_msg or "NotAuthorized" in error_msg:
                logger.error(
                    "Permission denied for %s. This usually means the device requires pairing. "
                    "Ensure bluetooth-agent service is running: "
                    "sudo systemctl status bluetooth-agent",
                    device.address,
                )
            else:
                logger.error("D-Bus error for %s: %s", device.address, e)
            return
        except BleakError as e:
            logger.error(f"BLE error for {device.address}: {e}")
            return
        except Exception as e:
            logger.error(
                f"Unexpected error processing {device.address}: "
                f"{type(e).__name__}: {e or 'Unknown error'}"
            )
            return

        logger.info(f"Meat temp: {meat_temp:.1f}°C, Grill temp: {grill_temp:.1f}°C")

        # Register device
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
