import asyncio

import click

from .server import serve_server


@click.group()
def main():
    """GrillGauge CLI tool for BLE meat probe monitoring."""


@main.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="HTTP server host (127.0.0.1 for localhost only, 0.0.0.0 for all interfaces).",
)
@click.option("--port", default=8000, type=int, help="HTTP server port.")
def serve(host: str, port: int):
    """Start Prometheus metrics server with automatic device discovery."""
    asyncio.run(serve_server(host=host, port=port))


if __name__ == "__main__":
    main()
