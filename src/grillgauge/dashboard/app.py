"""Main GrillGauge dashboard application."""

import os
import subprocess  # nosec B404
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Footer, Header

from .config import DashboardConfig
from .widgets.cooking import CookingWidget
from .widgets.services import ServicesWidget
from .widgets.temperature import GrillTemperatureWidget, MeatTemperatureWidget
from .widgets.weather import WeatherWidget


class ServicesModal(ModalScreen):
    """Modal screen displaying service statistics."""

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        """Compose the modal with services widget."""
        yield Header("Service Statistics")
        with Container(id="services-modal-container"):
            yield ServicesWidget(id="modal-services")
        yield Footer()


class DashboardApp(App):
    """GrillGauge temperature monitoring dashboard.

    Features:
    - Live weather data (auto-location via IP)
    - Cooking temperature safety guide
    - Meat temperature sparkline (0°C baseline, auto-scaling)
    - Grill temperature sparkline (0°C baseline, auto-scaling)

    Keyboard shortcuts:
    - q: Detach session or quit
    - r: Manual refresh all widgets
    - s: Show service statistics
    - ctrl+c: Quit
    """

    CSS_PATH = "styles/dashboard.tcss"
    TITLE = "GrillGauge Dashboard"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "detach", "Detach session or quit"),
        ("r", "refresh", "Refresh"),
        ("s", "show_services", "Show Services"),
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
        self.cooking_widget: CookingWidget | None = None
        self.meat_temp_widget: MeatTemperatureWidget | None = None
        self.grill_temp_widget: GrillTemperatureWidget | None = None

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout.

        Layout: 2x2 grid
        +-------------------+-------------------+
        |   Weather         | Cooking Temps     |
        +-------------------+-------------------+
        | Meat Temp (°C)    | Grill Temp (°C)   |
        +-------------------+-------------------+
        """
        yield Header()

        with Container(id="dashboard-container"), Grid(id="dashboard-grid"):
            # Top left: Weather
            self.weather_widget = WeatherWidget(id="weather")
            yield self.weather_widget

            # Top right: Cooking temperatures
            self.cooking_widget = CookingWidget(id="cooking")
            yield self.cooking_widget

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

        # Temperatures: Update every 15 seconds
        self.set_interval(
            self.config.temp_update_interval,
            self._update_temperatures,
        )

    async def _update_weather(self) -> None:
        """Update weather widget."""
        if self.weather_widget:
            await self.weather_widget.update_weather()

    async def _update_temperatures(self) -> None:
        """Update temperature sparklines."""
        if self.meat_temp_widget:
            await self.meat_temp_widget.update_temperature()
        if self.grill_temp_widget:
            await self.grill_temp_widget.update_temperature()

    async def action_refresh(self) -> None:
        """Manually refresh all widgets (triggered by 'r' key)."""
        await self._update_weather()
        await self._update_temperatures()

    async def action_show_services(self) -> None:
        """Show services statistics modal (triggered by 's' key)."""
        await self.push_screen(ServicesModal())

    async def action_detach(self) -> None:
        """Detach from tmux session, fallback to quit if fails."""
        # Check if we're in a tmux session
        if not os.environ.get("TMUX"):
            # Not in tmux, just quit normally
            self.exit()
            return

        # Attempt to detach
        try:
            subprocess.run(  # nosec B603 B607
                ["tmux", "detach-client"], check=True, capture_output=True, timeout=2
            )
            # Success - we're detached, but method continues
            # The detach will end this client session
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
            Exception,
        ):
            # Detach failed - fallback to quit
            self.exit()


def run_dashboard(config: DashboardConfig | None = None) -> None:
    """Run the dashboard application.

    Args:
        config: Dashboard configuration (auto-detected if not provided)
    """
    app = DashboardApp(config=config)
    app.run()
