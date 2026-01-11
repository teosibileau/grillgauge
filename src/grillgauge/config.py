import logging

import coloredlogs

# grillprobeE service UUIDs
DATA_SERVICE = "0000fb00-0000-1000-8000-00805f9b34fb"
TEMP_CHARACTERISTIC = "0000fb02-0000-1000-8000-00805f9b34fb"

# Configure logger
logger = logging.getLogger(__name__)

# Install coloredlogs with custom format
coloredlogs.install(
    level="INFO",
    logger=logger,
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
