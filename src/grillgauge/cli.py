import asyncio

import click

from .config import logger
from .scanner import DeviceScanner


@click.group()
def main():
    """GrillGauge CLI tool for BLE meat probe monitoring."""


@main.command()
@click.option("--timeout", default=10.0, help="Scan timeout in seconds.")
def scan(timeout):
    """Automatically scan and classify BLE devices."""
    scanner = DeviceScanner(timeout=timeout)

    async def run_scan():
        devices = await scanner()

        probes = [d for d in devices if d["classification"] == "probe"]
        ignored = [d for d in devices if d["classification"] == "ignored"]

        logger.info(
            f"Scan complete: {len(probes)} probes added, {len(ignored)} devices ignored"
        )

        if probes:
            logger.info("New probes:")
            for probe in probes:
                logger.info(f"  - {probe['name']} ({probe['address']})")

    asyncio.run(run_scan())


if __name__ == "__main__":
    main()
