import logging
import os

import coloredlogs

# grillprobeE service UUIDs
DATA_SERVICE = "0000fb00-0000-1000-8000-00805f9b34fb"
TEMP_CHARACTERISTIC = "0000fb02-0000-1000-8000-00805f9b34fb"

# BLE connection timeout (seconds)
# Can be overridden with GRILLGAUGE_BLE_TIMEOUT environment variable
# Default 15s is tuned for Raspberry Pi with BlueZ/D-Bus overhead
# Mac/CoreBluetooth typically connects in ~2s
BLE_CONNECTION_TIMEOUT = float(os.getenv("GRILLGAUGE_BLE_TIMEOUT", "15.0"))

# Configure logger
logger = logging.getLogger(__name__)

# Install coloredlogs with custom format
coloredlogs.install(
    level="INFO",
    logger=logger,
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

# Server Configuration
SCAN_INTERVAL_SECONDS: int = 10  # Temperature polling periodicity

# Prometheus Metric Names
MEAT_TEMPERATURE_METRIC_NAME = "grillgauge_meat_temperature_celsius"
GRILL_TEMPERATURE_METRIC_NAME = "grillgauge_grill_temperature_celsius"
PROBE_STATUS_METRIC_NAME = "grillgauge_probe_status"
