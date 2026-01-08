import logging

import coloredlogs

# Configure logger
logger = logging.getLogger(__name__)

# Install coloredlogs with custom format
coloredlogs.install(
    level="INFO",
    logger=logger,
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
