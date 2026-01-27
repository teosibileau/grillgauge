"""Main GrillGauge dashboard application."""

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Grid
from textual.widgets import Footer, Header

from grillgauge.dashboard.config import DashboardConfig
from grillgauge.dashboard.widgets.services import ServicesWidget
from grillgauge.dashboard.widgets.temperature import (
    GrillTemperatureWidget,
    MeatTemperatureWidget,
)
from grillgauge.dashboard.widgets.weather import WeatherWidget


class DashboardApp(App):
    """GrillGauge temperature monitoring dashboard.

    Features:
    - Live weather data (auto-location via IP)
    - Service resource usage (grillgauge + prometheus)
    - Meat temperature sparkline (0°C baseline, auto-scaling)
    - Grill temperature sparkline (0°C baseline, auto-scaling)

    Keyboard shortcuts:
    - q: Quit
    - r: Manual refresh all widgets
    - ctrl+c: Quit
    """

    CSS_PATH = "styles/dashboard.tcss"
    TITLE = "GrillGauge Dashboard"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, config: DashboardConfig | None = None) -> None:
        """Initialize the dashboard app.

        Args:
            config: Dashboard configuration (auto-detected if not provided)
        """
        super().__init__()
        self.config = config or DashboardConfig.auto_detect()

        # Set Tokyo Night theme
        self.theme = "tokyo-night"

        # Widget references for updates
        self.weather_widget: WeatherWidget | None = None
        self.services_widget: ServicesWidget | None = None
        self.meat_temp_widget: MeatTemperatureWidget | None = None
        self.grill_temp_widget: GrillTemperatureWidget | None = None

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout.

        Layout: 2x2 grid
        +-------------------+-------------------+
        |   Weather         | Service Stats     |
        +-------------------+-------------------+
        | Meat Temp (°C)    | Grill Temp (°C)   |
        +-------------------+-------------------+
        """
        yield Header()

        with Container(id="dashboard-container"), Grid(id="dashboard-grid"):
            # Top left: Weather
            self.weather_widget = WeatherWidget(id="weather")
            yield self.weather_widget

            # Top right: Service stats
            self.services_widget = ServicesWidget(id="services")
            yield self.services_widget

            # Bottom left: Meat temperature sparkline
            self.meat_temp_widget = MeatTemperatureWidget(
                prometheus_url=self.config.prometheus_url,
                id="meat-temp",
            )
            yield self.meat_temp_widget

            # Bottom right: Grill temperature sparkline
            self.grill_temp_widget = GrillTemperatureWidget(
                prometheus_url=self.config.prometheus_url,
                id="grill-temp",
            )
            yield self.grill_temp_widget

        yield Footer()

    def on_mount(self) -> None:
        """Set up periodic updates when app is mounted."""
        # Weather: Update every 10 minutes (600 seconds)
        self.set_interval(
            self.config.weather_update_interval,
            self._update_weather,
        )

        # Services: Update every 5 seconds
        self.set_interval(
            self.config.service_update_interval,
            self._update_services,
        )

        # Temperatures: Update every 15 seconds
        self.set_interval(
            self.config.temp_update_interval,
            self._update_temperatures,
        )

    async def _update_weather(self) -> None:
        """Update weather widget."""
        if self.weather_widget:
            await self.weather_widget.update_weather()

    async def _update_services(self) -> None:
        """Update services widget."""
        if self.services_widget:
            await self.services_widget.update_services()

    async def _update_temperatures(self) -> None:
        """Update temperature sparklines."""
        if self.meat_temp_widget:
            await self.meat_temp_widget.update_temperature()
        if self.grill_temp_widget:
            await self.grill_temp_widget.update_temperature()

    async def action_refresh(self) -> None:
        """Manually refresh all widgets (triggered by 'r' key)."""
        await self._update_weather()
        await self._update_services()
        await self._update_temperatures()

    def action_quit(self) -> None:
        """Quit the application (triggered by 'q' key)."""
        self.exit()


def run_dashboard(config: DashboardConfig | None = None) -> None:
    """Run the dashboard application.

    Args:
        config: Dashboard configuration (auto-detected if not provided)
    """
    app = DashboardApp(config=config)
    app.run()
