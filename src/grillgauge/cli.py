import asyncio
import click
from bleak import BleakScanner


@click.group()
def main():
    """GrillGauge CLI tool for BLE meat probe monitoring."""
    pass


@main.command()
@click.option("--timeout", default=5.0, help="Scan timeout in seconds.")
def scan(timeout):
    """Scan for BLE devices and display information."""
    click.echo("Scanning for BLE devices...")

    async def _scan():
        try:
            devices = await BleakScanner.discover(timeout=timeout)
            if not devices:
                click.echo("No devices found.")
                return

            for device in devices:
                click.echo(
                    f"Name: {device.name or 'Unknown'}, Address: {device.address}, RSSI: {device.rssi}"
                )
                if device.metadata:
                    click.echo(f"  Metadata: {device.metadata}")
                click.echo("---")
        except Exception as e:
            click.echo(f"Error during scan: {e}")

    asyncio.run(_scan())


if __name__ == "__main__":
    main()
