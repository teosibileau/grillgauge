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


@main.command()
@click.option(
    "--prometheus-url",
    envvar="PROMETHEUS_URL",
    help="Prometheus API URL (auto-detected if not specified).",
)
def dashboard(prometheus_url: str | None):
    """Launch interactive temperature monitoring dashboard.

    The dashboard displays:
    - Live weather data (auto-location)
    - Service resource usage (grillgauge, prometheus)
    - Meat temperature sparkline (0-300°C fixed Y-axis)
    - Grill temperature sparkline (0-300°C fixed Y-axis)

    Keyboard shortcuts:
    - q: Quit
    - r: Manual refresh
    - ctrl+c: Quit

    Configuration is auto-detected based on hostname:
    - Running on Pi: Uses localhost:9090
    - Running remotely: Uses grillgauge:9090

    Override with --prometheus-url or PROMETHEUS_URL environment variable.
    """
    from grillgauge.dashboard.app import run_dashboard
    from grillgauge.dashboard.config import DashboardConfig

    # Create config with optional override
    if prometheus_url:
        # Parse base URL from full API URL if needed
        base_url = prometheus_url.replace("/api/v1/query", "")
        config = DashboardConfig.auto_detect()
        config.prometheus_url = base_url
    else:
        config = DashboardConfig.auto_detect()

    # Run the dashboard
    run_dashboard(config=config)


if __name__ == "__main__":
    main()
