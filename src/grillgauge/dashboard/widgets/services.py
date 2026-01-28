"""Service stats widget displaying resource usage in a table."""

from typing import Any

from textual.widgets import DataTable

from ..config import DashboardConfig
from ..data.services import get_service_stats


class ServicesWidget(DataTable):
    """Widget displaying service resource usage statistics.

    Displays a table with columns:
    - SERVICE: Service name
    - CPU%: CPU usage percentage
    - MEM%: Memory usage percentage
    - MEM USAGE: Memory usage in MB
    - UPTIME: Time since service started
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the services widget."""
        super().__init__(*args, **kwargs)
        self.show_header = True
        self.zebra_stripes = True
        self.cursor_type = "none"  # Disable cursor

    def on_mount(self) -> None:
        """Set up the widget when mounted."""
        # Add columns (PID removed - not available from process-exporter)
        self.add_columns(
            "SERVICE",
            "CPU%",
            "MEM%",
            "MEM USAGE",
            "UPTIME",
        )
        # Initial update
        self.run_worker(self.update_services())

    async def update_services(self) -> None:
        """Fetch and display updated service stats."""
        try:
            # Get prometheus_url from config
            config = DashboardConfig.auto_detect()
            stats = await get_service_stats(prometheus_url=config.prometheus_url)
        except Exception:
            # If config or data fetching fails, show empty state
            stats = []

        # Clear existing rows
        self.clear()

        # Add rows for each service
        for stat in stats:
            self.add_row(
                stat["service"],
                stat["cpu"],
                stat["mem"],
                stat["mem_usage"],
                stat["uptime"],
            )

        # If no stats available, show message
        if not stats:
            self.add_row(
                "Not available",
                "-",
                "-",
                "-",
                "-",
            )
