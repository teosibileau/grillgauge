"""Weather widget displaying current conditions in a card format."""

from typing import Any

from rich.align import Align
from rich.console import Group
from rich.text import Text
from textual.widgets import Static

from grillgauge.dashboard.data.weather import get_weather_data


def status_to_emoji(status: str) -> str:
    """Convert weather status to emoji.

    Args:
        status: Weather status text

    Returns:
        Weather emoji
    """
    emojis = {
        "Clear": "☀️",
        "Partly Cloudy": "⛅",
        "Cloudy": "☁️",
        "Fog": "🌫️",
        "Drizzle": "🌦️",
        "Rain": "🌧️",
        "Snow": "🌨️",
        "Showers": "🌦️",
        "Thunderstorm": "⛈️",
    }
    return emojis.get(status, "🌡️")


class WeatherWidget(Static):
    """Widget displaying current weather conditions.

    Displays weather data in a card-like format with:
    - Large temperature display with emoji
    - Key weather metrics (feels like, humidity, wind)
    - Weather status description
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the weather widget."""
        super().__init__(*args, **kwargs)
        self.weather_data: dict[str, Any] | None = None

    def on_mount(self) -> None:
        """Set up the widget when mounted."""
        self.run_worker(self.update_weather())

    async def update_weather(self) -> None:
        """Fetch and display updated weather data."""
        self.weather_data = await get_weather_data()
        self.update(self.render_weather())

    def render_weather(self) -> Group:
        """Render weather data as a Rich renderable.

        Returns:
            Rich Group with formatted weather display
        """
        if self.weather_data is None:
            # Show error message
            error = Text("Weather Unavailable", style="bold red")
            return Group(Align.center(error, vertical="middle"))

        # Extract data
        temp = self.weather_data["temperature"]
        feels = self.weather_data["feels_like"]
        humidity = self.weather_data["humidity"]
        wind_speed = self.weather_data["wind_speed"]
        wind_dir = self.weather_data["wind_direction"]
        status = self.weather_data["status"]
        emoji = status_to_emoji(status)

        # Build display
        lines = []

        # Line 1: Big emoji on its own line
        emoji_line = Text(emoji, style="bold")
        lines.append(Align.center(emoji_line))

        # Line 2: Temperature
        temp_line = Text(f"{temp:.1f}°C", style="bold cyan")
        lines.append(Align.center(temp_line))

        # Line 3: Status | Feels like | Humidity (all on one line)
        info_line = Text()
        info_line.append(status, style="italic dim")
        info_line.append(" | ", style="dim")
        info_line.append(f"Feels {feels:.0f}°C", style="dim")
        info_line.append(" | ", style="dim")
        info_line.append(f"💧 {humidity}%", style="dim")
        lines.append(Align.center(info_line))

        # Line 4: Wind
        wind_line = Text()
        wind_line.append("🌬️  ", style="")
        wind_line.append(f"{wind_speed:.1f} km/h {wind_dir}", style="green")
        lines.append(Align.center(wind_line))

        return Group(*lines)
