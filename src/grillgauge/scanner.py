from bleak import BleakClient, BleakScanner

from .config import logger
from .env import EnvManager

MIN_TEMPERATURE_DATA_LENGTH = 2


class DeviceScanner:
    def __init__(self, timeout: float = 10.0):
        """Initialize scanner with timeout."""
        self.env_manager = EnvManager()
        self.timeout = timeout
        self.devices = []  # List of classified devices

    async def __call__(self):
        """Run scan and classification, return results."""
        await self._scan_and_classify()
        return self.devices

    async def _scan_and_classify(self):
        """Scan BLE devices and classify them automatically."""
        logger.info("Scanning for BLE devices...")

        try:
            devices = await BleakScanner.discover(timeout=self.timeout)
            if not devices:
                logger.info("No devices found")
                return

            # Get existing classifications
            existing_probes = {p["mac"]: p for p in self.env_manager.list_probes()}
            ignored_macs = set(self.env_manager.list_ignored())

            classified_count = 0

            for device in devices:
                if device.address in existing_probes or device.address in ignored_macs:
                    continue  # Skip already classified devices

                logger.debug(
                    f"Inspecting device: {device.name or 'Unknown'} ({device.address})"
                )

                battery, temp = await self._inspect_device(device.address)

                if battery is not None or temp is not None:
                    # Valid probe - add to probes
                    name = self._generate_probe_name(existing_probes)
                    self.env_manager.add_probe(device.address, name)

                    device_info = {
                        "address": device.address,
                        "name": name,
                        "classification": "probe",
                        "capabilities": {"battery": battery, "temperature": temp},
                    }

                    logger.info(f"Added probe: {name} ({device.address})")

                else:
                    # No capabilities - add to ignored
                    self.env_manager.add_ignored(device.address)

                    device_info = {
                        "address": device.address,
                        "name": device.name or "Unknown",
                        "classification": "ignored",
                        "capabilities": None,
                    }

                    logger.debug(f"Ignored device: {device.address}")

                self.devices.append(device_info)
                classified_count += 1

            logger.info(f"Classified {classified_count} new devices")

        except Exception as e:
            logger.error(f"Scan failed: {e}")

    async def _inspect_device(self, address: str):
        """Inspect device for battery and temperature."""
        try:
            async with BleakClient(address, timeout=5.0) as client:
                services = await client.get_services()

                battery_level = None
                temperature = None

                # Check battery service
                battery_svc = services.get_service(
                    "0000180f-0000-1000-8000-00805f9b34fb"
                )
                if battery_svc:
                    battery_char = battery_svc.get_characteristic(
                        "00002a19-0000-1000-8000-00805f9b34fb"
                    )
                    if battery_char:
                        battery_data = await client.read_gatt_char(battery_char.uuid)
                        battery_level = battery_data[0] if battery_data else None

                # Check temperature service
                temp_svc = services.get_service("0000181a-0000-1000-8000-00805f9b34fb")
                if temp_svc:
                    temp_char = temp_svc.get_characteristic(
                        "00002a6e-0000-1000-8000-00805f9b34fb"
                    )
                    if temp_char:
                        temp_data = await client.read_gatt_char(temp_char.uuid)
                        if len(temp_data) >= MIN_TEMPERATURE_DATA_LENGTH:
                            temp_raw = int.from_bytes(
                                temp_data[:2], byteorder="little", signed=True
                            )
                            temperature = temp_raw / 100.0

                return battery_level, temperature

        except Exception:
            return None, None

    def _generate_probe_name(self, existing_probes):
        """Generate unique probe name."""
        existing_names = {probe["name"] for probe in existing_probes.values()}

        counter = 1
        while f"Probe{counter}" in existing_names:
            counter += 1

        return f"Probe{counter}"
