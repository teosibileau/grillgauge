import asyncio
import contextlib
import time
from typing import Any

from aiohttp import web
from prometheus_client import generate_latest

from .config import logger
from .env import EnvManager
from .metrics import MetricsCollector
from .probe import GrillProbe


class MetricsServer:
    """HTTP server for Prometheus metrics with persistent BLE connections."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, registry=None):
        self.host = host
        self.port = port
        self.metrics_collector = MetricsCollector(registry=registry)
        self.probes = {}  # {device_address: GrillProbe}
        self.reconnect_tasks = {}  # {device_address: asyncio.Task}
        self.monitor_task: asyncio.Task[Any] | None = None
        self.app = self._create_app()

    def _create_app(self) -> web.Application:
        """Create aiohttp application with routes."""
        app = web.Application()

        async def metrics_handler(request: web.Request) -> web.Response:  # noqa: ARG001
            """Serve Prometheus metrics."""
            # Generate metrics output
            output = generate_latest()
            return web.Response(
                text=output.decode("utf-8"),
                content_type="text/plain; version=0.0.4",
                charset="utf-8",
            )

        async def health_handler(request: web.Request) -> web.Response:  # noqa: ARG001
            """Health check endpoint."""
            connected_count = sum(
                1 for probe in self.probes.values() if probe.is_connected
            )
            return web.json_response(
                {
                    "status": "healthy",
                    "timestamp": time.time(),
                    "probes": {"total": len(self.probes), "connected": connected_count},
                }
            )

        app.router.add_get("/metrics", metrics_handler)
        app.router.add_get("/health", health_handler)

        return app

    def _create_notification_callback(self, device_address: str, probe_name: str):
        """Create a notification callback for a specific probe."""

        def callback(meat_temp: float, grill_temp: float):
            """Update metrics when notification is received."""
            logger.info(
                f"{probe_name}: Meat={meat_temp:.1f}°C, Grill={grill_temp:.1f}°C"
            )

            # Update Prometheus metrics
            self.metrics_collector.update_probe_metrics(
                device_address=device_address,
                meat_temp=meat_temp,
                grill_temp=grill_temp,
                status=1,  # Online
            )

        return callback

    async def _discover_and_connect_probes(self):
        """Connect to configured probes."""
        env_manager = EnvManager()

        # First, check if we have configured probes
        configured_probes = env_manager.list_probes()

        if not configured_probes:
            # No probes configured - run discovery
            logger.info("No probes configured. Running device discovery...")
            await self._discover_new_devices()
            configured_probes = env_manager.list_probes()

        if not configured_probes:
            logger.warning("No probes found or configured")
            return

        logger.info(f"Connecting to {len(configured_probes)} configured probe(s)...")

        # Connect to each configured probe using address string
        # (BLEDevice objects become stale on Pi/BlueZ)
        for probe_config in configured_probes:
            device_address = probe_config["mac"]
            probe_name = probe_config["name"]

            # Create probe with notification callback
            callback = self._create_notification_callback(device_address, probe_name)
            probe = GrillProbe(
                device_address, notification_callback=callback
            )  # Use address string

            # Connect
            logger.info(f"Connecting to {probe_name} ({device_address})...")
            if await probe.connect():
                self.probes[device_address] = probe
                logger.info(f"✓ {probe_name} connected and subscribed to notifications")
            else:
                logger.error(f"✗ Failed to connect to {probe_name}")
                # Store probe anyway for reconnection attempts
                self.probes[device_address] = probe

    async def _discover_new_devices(self):
        """Discover and register new grillprobeE devices."""
        logger.info("Running device discovery scan...")
        try:
            # Import scanner here to avoid circular imports
            from .scanner import DeviceScanner

            scanner = DeviceScanner(timeout=10.0)
            devices = await scanner()

            probes = [d for d in devices if d["classification"] == "probe"]
            logger.info(f"Discovery complete: found {len(probes)} new probe(s)")

            if probes:
                for probe in probes:
                    logger.info(f"  - {probe['name']} ({probe['address']})")
        except Exception as e:
            logger.error(f"Device discovery failed: {e}")

    async def _monitor_connections(self):
        """Background task to monitor and restore lost connections."""
        logger.info("Starting connection monitor...")

        while True:
            await asyncio.sleep(30)  # Check every 30 seconds

            for device_address, probe in self.probes.items():
                if not probe.is_connected:
                    logger.warning(
                        f"Probe {device_address} disconnected, attempting reconnection..."
                    )

                    # Update metrics to show offline
                    self.metrics_collector.update_probe_metrics(
                        device_address=device_address,
                        meat_temp=None,
                        grill_temp=None,
                        status=0,  # Offline
                    )

                    # Try to reconnect (store task reference)
                    self.reconnect_tasks[device_address] = asyncio.create_task(
                        probe.ensure_connected()
                    )

    async def start(self):
        """Start the server and establish persistent connections."""
        # Wait a bit for Bluetooth to be ready
        await asyncio.sleep(3)

        # Discover and connect to all probes
        await self._discover_and_connect_probes()

        # Start connection monitor
        self.monitor_task = asyncio.create_task(self._monitor_connections())

        # Start HTTP server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(
            f"Prometheus metrics available at http://{self.host}:{self.port}/metrics"
        )
        logger.info(f"Health check available at http://{self.host}:{self.port}/health")
        logger.info(
            f"Monitoring {len(self.probes)} probe(s) with persistent connections"
        )

        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            # Disconnect all probes
            logger.info("Disconnecting probes...")
            for probe in self.probes.values():
                await probe.disconnect()

            # Cancel monitor task
            if self.monitor_task:
                self.monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.monitor_task

            await runner.cleanup()
            logger.info("Server shutdown complete")


async def serve_server(host: str = "127.0.0.1", port: int = 8000):
    """Start the metrics server."""
    server = MetricsServer(host=host, port=port)
    await server.start()
