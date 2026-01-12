import asyncio
import contextlib
import time
from typing import Any

from aiohttp import web
from prometheus_client import generate_latest

from .config import SCAN_INTERVAL_SECONDS, logger
from .env import EnvManager
from .metrics import MetricsCollector
from .probe import GrillProbe


class MetricsServer:
    """HTTP server for Prometheus metrics with background probe scanning."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, registry=None):
        self.host = host
        self.port = port
        self.metrics_collector = MetricsCollector(registry=registry)
        self.scan_task: asyncio.Task[Any] | None = None
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
            return web.json_response({"status": "healthy", "timestamp": time.time()})

        app.router.add_get("/metrics", metrics_handler)
        app.router.add_get("/health", health_handler)

        return app

    async def _scan_probes_once(self):
        """Scan all configured probes once and update metrics."""
        env_manager = EnvManager()
        probes = env_manager.list_probes()

        logger.debug(f"Found {len(probes)} configured probes")
        if not probes:
            logger.warning("No probes configured - run 'grillgauge scan' first")
            return

        for probe_config in probes:
            device_address = probe_config["mac"]
            probe_name = probe_config["name"]

            try:
                async with GrillProbe(device_address) as probe:
                    meat_temp, grill_temp = await probe.read_temperature()

                    # Update metrics (status=1 for successful read)
                    self.metrics_collector.update_probe_metrics(
                        device_address=device_address,
                        meat_temp=meat_temp,
                        grill_temp=grill_temp,
                        status=1,
                    )

                    logger.debug(
                        f"Successfully read {probe_name} ({device_address}): "
                        f"meat={meat_temp}°C, grill={grill_temp}°C"
                    )

            except Exception as e:
                # BLE read failed - update status to offline, keep last good temps
                self.metrics_collector.update_probe_metrics(
                    device_address=device_address,
                    meat_temp=None,  # Keep last known good
                    grill_temp=None,  # Keep last known good
                    status=0,  # Mark offline
                )
                logger.warning(f"Failed to read {probe_name} ({device_address}): {e}")

    async def _background_scan_loop(self):
        """Background task that periodically scans all probes."""
        logger.info(
            f"Starting background probe scanning (every {SCAN_INTERVAL_SECONDS}s)"
        )

        while True:
            try:
                await self._scan_probes_once()
            except Exception as e:
                logger.error(f"Error in background scan loop: {e}")

            await asyncio.sleep(SCAN_INTERVAL_SECONDS)

    async def start(self):
        """Start the server and background scanning."""
        # Start background scanning task
        self.scan_task = asyncio.create_task(self._background_scan_loop())

        # Start HTTP server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(
            f"Prometheus metrics available at http://{self.host}:{self.port}/metrics"
        )
        logger.info(f"Health check available at http://{self.host}:{self.port}/health")

        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            if self.scan_task:
                self.scan_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.scan_task

            await runner.cleanup()
            logger.info("Server shutdown complete")


async def serve_server(host: str = "127.0.0.1", port: int = 8000):
    """Start the metrics server."""
    server = MetricsServer(host=host, port=port)
    await server.start()
