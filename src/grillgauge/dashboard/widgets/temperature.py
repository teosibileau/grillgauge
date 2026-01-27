"""Temperature sparkline widgets with FIXED Y-axis for consistent scaling."""

from collections import deque
from typing import Any

from textual.app import RenderResult
from textual.widgets import Sparkline

from grillgauge.dashboard.data.probes import (
    get_grill_temperature,
    get_meat_temperature,
    get_temperature_history,
)
from grillgauge.dashboard.renderables.zero_baseline_sparkline import (
    ZeroBaselineSparklineRenderable,
)


class TemperatureWidget(Sparkline):
    """Base temperature sparkline widget with 0°C baseline.

    Prepends a 0 value to the data so the sparkline scales from 0°C to the
    maximum temperature in the dataset. This ensures temperatures are visible
    even when they're constant, and provides a consistent baseline for comparison.

    Maintains 50 data points (~12.5 minutes of history at 15-second intervals).
    """

    def __init__(
        self,
        prometheus_url: str,
        temp_type: str = "meat",
        max_points: int = 50,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the temperature widget.

        Args:
            prometheus_url: Base Prometheus API URL
            temp_type: Temperature type ('meat' or 'grill')
            max_points: Maximum number of data points to retain (default: 50)
            *args: Additional positional arguments for Sparkline
            **kwargs: Additional keyword arguments for Sparkline
        """
        super().__init__(*args, **kwargs)
        self.prometheus_url = prometheus_url
        self.temp_type = temp_type
        self.max_points = max_points
        self.data_points: deque[float] = deque(maxlen=max_points)

    async def on_mount(self) -> None:
        """Set up the widget when mounted - preload historical data."""
        # Calculate duration needed to fill the entire sparkline
        # max_points * step_seconds / 60 = duration_minutes
        # Example: 50 points * 15 seconds / 60 = 12.5 minutes
        step_seconds = 15  # Must match Prometheus scrape interval
        duration_minutes = (self.max_points * step_seconds) / 60

        metric_name = (
            "grillgauge_meat_temperature_celsius"
            if self.temp_type == "meat"
            else "grillgauge_grill_temperature_celsius"
        )

        # Query for enough historical data to fill the entire sparkline
        # Add 1 minute buffer to ensure we get enough data points
        historical_data = await get_temperature_history(
            self.prometheus_url,
            metric_name,
            duration_minutes=int(duration_minutes) + 1,
            step=step_seconds,
        )

        if historical_data:
            # Preload with actual historical data
            # Limit to max_points if we got more data than needed
            if len(historical_data) > self.max_points:
                historical_data = historical_data[-self.max_points :]

            # If we have less data than max_points, pad with zeros at the start
            if len(historical_data) < self.max_points:
                padding = self.max_points - len(historical_data)
                for _ in range(padding):
                    self.data_points.append(0.0)

            # Add the historical data
            for temp in historical_data:
                self.data_points.append(temp)
        else:
            # Fallback: Initialize with zeros if historical query fails
            for _ in range(self.max_points):
                self.data_points.append(0.0)

        self.update_sparkline()

    async def update_temperature(self) -> None:
        """Fetch and display updated temperature data."""
        # Fetch temperature based on type
        if self.temp_type == "meat":
            temp = await get_meat_temperature(self.prometheus_url)
        else:  # grill
            temp = await get_grill_temperature(self.prometheus_url)

        # Add new data point (or 0 if unavailable)
        if temp is not None:
            self.data_points.append(temp)
        else:
            # Keep the sparkline alive even if data is temporarily unavailable
            # Use the last value if available, otherwise 0
            last_value = self.data_points[-1] if self.data_points else 0.0
            self.data_points.append(last_value)

        # Update the sparkline display
        self.update_sparkline()

    def update_sparkline(self) -> None:
        """Update the sparkline with current data points."""
        # Convert deque to list for Sparkline
        raw_data = list(self.data_points)

        if not raw_data:
            return

        # Set data directly (0°C baseline handled in custom renderable)
        self.data = raw_data

        # Set summary with series name and current temperature
        series_name = self.temp_type.capitalize()  # "Meat" or "Grill"
        current = raw_data[-1]
        self.summary = f"{series_name}: {current:.1f}°C"

    def render(self) -> RenderResult:
        """Render sparkline with forced 0°C baseline scaling."""
        data = self.data or []

        # Get colors same as parent Sparkline
        _, base = self.background_colors
        min_color = base + (
            self.get_component_styles("sparkline--min-color").color
            if self.min_color is None
            else self.min_color
        )
        max_color = base + (
            self.get_component_styles("sparkline--max-color").color
            if self.max_color is None
            else self.max_color
        )

        # Use custom renderable with forced 0°C minimum
        return ZeroBaselineSparklineRenderable(
            data,
            width=self.size.width,
            height=self.size.height,
            min_color=min_color.rich_color,
            max_color=max_color.rich_color,
            summary_function=self.summary_function,
            summary=self.summary,
        )


class MeatTemperatureWidget(TemperatureWidget):
    """Sparkline widget for meat probe temperature (0°C baseline)."""

    def __init__(self, prometheus_url: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the meat temperature widget.

        Args:
            prometheus_url: Base Prometheus API URL
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            *args,
            prometheus_url=prometheus_url,
            temp_type="meat",
            **kwargs,
        )


class GrillTemperatureWidget(TemperatureWidget):
    """Sparkline widget for grill temperature (0°C baseline)."""

    def __init__(self, prometheus_url: str, *args: Any, **kwargs: Any) -> None:
        """Initialize the grill temperature widget.

        Args:
            prometheus_url: Base Prometheus API URL
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            *args,
            prometheus_url=prometheus_url,
            temp_type="grill",
            **kwargs,
        )
