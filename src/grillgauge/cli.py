import asyncio

import click

from .config import logger
from .scanner import DeviceScanner
from .server import serve_server


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


@main.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="HTTP server host (127.0.0.1 for localhost only, 0.0.0.0 for all interfaces).",
)
@click.option("--port", default=8000, type=int, help="HTTP server port.")
def serve(host: str, port: int):
    """Start Prometheus metrics server for grillprobeE devices."""
    asyncio.run(serve_server(host=host, port=port))


if __name__ == "__main__":
    main()
