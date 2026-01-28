"""Unit tests for weather widget."""

from unittest.mock import patch

import pytest

from grillgauge.dashboard.widgets.weather import WeatherWidget, status_to_emoji


def test_status_to_emoji():
    """Test weather status to emoji conversion."""
    assert status_to_emoji("Clear") == "☀️"
    assert status_to_emoji("Partly Cloudy") == "⛅"
    assert status_to_emoji("Cloudy") == "☁️"
    assert status_to_emoji("Fog") == "🌫️"
    assert status_to_emoji("Drizzle") == "🌦️"
    assert status_to_emoji("Rain") == "🌧️"
    assert status_to_emoji("Snow") == "🌨️"
    assert status_to_emoji("Showers") == "🌦️"
    assert status_to_emoji("Thunderstorm") == "⛈️"
    assert status_to_emoji("Unknown") == "🌡️"
    assert status_to_emoji("") == "🌡️"


def test_status_to_emoji_case_sensitivity():
    """Test that status_to_emoji is case-sensitive."""
    assert status_to_emoji("clear") == "🌡️"  # Unknown status
    assert status_to_emoji("PARTLY CLOUDY") == "🌡️"  # Unknown status
    assert status_to_emoji("Clear") == "☀️"  # Exact match


@pytest.mark.asyncio
async def test_weather_widget_render_weather_with_data():
    """Test weather widget rendering with weather data."""
    expected_weather_lines = (
        3  # Updated: now 3 lines (status, temp|feels, humidity|wind)
    )

    widget = WeatherWidget()
    widget.weather_data = {
        "temperature": 20.5,
        "feels_like": 19.0,
        "humidity": 65,
        "wind_speed": 12.5,
        "wind_direction": "S",
        "status": "Partly Cloudy",
    }

    renderable = widget.render_weather()

    # Check that we get a Group renderable
    from rich.console import Group

    assert isinstance(renderable, Group)

    # Check that the group has expected number of lines
    assert len(renderable.renderables) == expected_weather_lines


@pytest.mark.asyncio
async def test_weather_widget_render_weather_no_data():
    """Test weather widget rendering when no data available."""
    expected_error_lines = 1

    widget = WeatherWidget()
    widget.weather_data = None

    renderable = widget.render_weather()

    # Check that we get a Group renderable
    from rich.console import Group

    assert isinstance(renderable, Group)

    # Check that the group has 1 line (error message)
    assert len(renderable.renderables) == expected_error_lines


@pytest.mark.asyncio
async def test_weather_widget_update_weather():
    """Test weather data update functionality."""
    mock_weather_data = {
        "temperature": 20.5,
        "feels_like": 19.0,
        "humidity": 65,
        "wind_speed": 12.5,
        "wind_direction": "S",
        "status": "Partly Cloudy",
    }

    widget = WeatherWidget()

    with patch(
        "grillgauge.dashboard.widgets.weather.get_weather_data",
        return_value=mock_weather_data,
    ) as mock_get_weather:
        await widget.update_weather()

        # Check that get_weather_data was called
        mock_get_weather.assert_called_once()

        # Check that weather_data was set
        assert widget.weather_data == mock_weather_data


@pytest.mark.asyncio
async def test_weather_widget_update_weather_failure():
    """Test weather data update when API fails."""
    widget = WeatherWidget()

    with patch(
        "grillgauge.dashboard.widgets.weather.get_weather_data",
        return_value=None,
    ) as mock_get_weather:
        await widget.update_weather()

        # Check that get_weather_data was called
        mock_get_weather.assert_called_once()

        # Check that weather_data was set to None
        assert widget.weather_data is None


def test_weather_widget_initialization():
    """Test weather widget initialization."""
    widget = WeatherWidget()

    assert widget.weather_data is None
    assert isinstance(widget, WeatherWidget)
