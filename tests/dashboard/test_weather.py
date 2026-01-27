"""Unit tests for weather data fetching."""

from unittest.mock import AsyncMock, patch

import pytest

from grillgauge.dashboard.data.weather import (
    get_location,
    get_weather,
    get_weather_data,
    wind_dir_to_text,
    wmo_code_to_text,
)


def test_wind_dir_to_text():
    """Test wind direction conversion from degrees to cardinal."""
    assert wind_dir_to_text(0) == "N"
    assert wind_dir_to_text(45) == "NE"
    assert wind_dir_to_text(90) == "E"
    assert wind_dir_to_text(135) == "SE"
    assert wind_dir_to_text(180) == "S"
    assert wind_dir_to_text(225) == "SW"
    assert wind_dir_to_text(270) == "W"
    assert wind_dir_to_text(315) == "NW"
    assert wind_dir_to_text(360) == "N"  # Wraps around


def test_wmo_code_to_text():
    """Test WMO weather code conversion."""
    assert wmo_code_to_text(0) == "Clear"
    assert wmo_code_to_text(1) == "Partly Cloudy"
    assert wmo_code_to_text(45) == "Fog"
    assert wmo_code_to_text(51) == "Drizzle"
    assert wmo_code_to_text(61) == "Rain"
    assert wmo_code_to_text(71) == "Snow"
    assert wmo_code_to_text(80) == "Showers"
    assert wmo_code_to_text(95) == "Thunderstorm"
    assert wmo_code_to_text(999) == "Unknown"  # Unknown code


@pytest.mark.asyncio
async def test_get_location_success():
    """Test successful location fetch."""
    san_francisco_lat = 37.7749
    san_francisco_lon = -122.4194

    mock_response = AsyncMock()
    mock_response.json = lambda: {"lat": san_francisco_lat, "lon": san_francisco_lon}
    mock_response.raise_for_status = lambda: None  # synchronous method

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        lat, lon = await get_location()
        assert lat == san_francisco_lat
        assert lon == san_francisco_lon


@pytest.mark.asyncio
async def test_get_location_failure():
    """Test location fetch failure."""
    import httpx

    mock_get = AsyncMock(side_effect=httpx.HTTPError("Network error"))
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        lat, lon = await get_location()
        assert lat is None
        assert lon is None


@pytest.mark.asyncio
async def test_get_weather_success():
    """Test successful weather data fetch."""
    test_temperature = 20.5

    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "current": {
            "temperature_2m": test_temperature,
            "apparent_temperature": 19.0,
            "relative_humidity_2m": 65,
            "precipitation": 0.0,
            "cloud_cover": 25,
            "wind_speed_10m": 12.5,
            "wind_direction_10m": 180,
            "weather_code": 1,
        }
    }
    mock_response.raise_for_status = lambda: None  # synchronous method

    mock_get = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        weather = await get_weather(37.7749, -122.4194)
        assert weather is not None
        assert weather["current"]["temperature_2m"] == test_temperature


@pytest.mark.asyncio
async def test_get_weather_failure():
    """Test weather fetch failure."""
    import httpx

    mock_get = AsyncMock(side_effect=httpx.HTTPError("API error"))
    mock_client_instance = AsyncMock()
    mock_client_instance.get = mock_get

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        weather = await get_weather(37.7749, -122.4194)
        assert weather is None


@pytest.mark.asyncio
async def test_get_weather_data_success():
    """Test complete weather data fetch with formatting."""
    # Mock get_location
    san_francisco_lat = 37.7749
    san_francisco_lon = -122.4194
    test_temperature = 20.5
    test_feels_like = 19.0
    test_humidity = 65
    test_wind_speed = 12.5
    test_cloud_cover = 25

    with (
        patch(
            "grillgauge.dashboard.data.weather.get_location",
            return_value=(san_francisco_lat, san_francisco_lon),
        ),
        patch(
            "grillgauge.dashboard.data.weather.get_weather",
            return_value={
                "current": {
                    "temperature_2m": test_temperature,
                    "apparent_temperature": test_feels_like,
                    "relative_humidity_2m": test_humidity,
                    "precipitation": 0.0,
                    "cloud_cover": test_cloud_cover,
                    "wind_speed_10m": test_wind_speed,
                    "wind_direction_10m": 180,
                    "weather_code": 1,
                }
            },
        ),
    ):
        data = await get_weather_data()

        assert data is not None
        assert data["temperature"] == test_temperature
        assert data["feels_like"] == test_feels_like
        assert data["humidity"] == test_humidity
        assert data["wind_speed"] == test_wind_speed
        assert data["wind_direction"] == "S"  # 180 degrees
        assert data["precipitation"] == 0.0
        assert data["cloud_cover"] == test_cloud_cover
        assert data["status"] == "Partly Cloudy"  # WMO code 1


@pytest.mark.asyncio
async def test_get_weather_data_location_failure():
    """Test weather data fetch when location fails."""
    with patch(
        "grillgauge.dashboard.data.weather.get_location",
        return_value=(None, None),
    ):
        data = await get_weather_data()
        assert data is None


@pytest.mark.asyncio
async def test_get_weather_data_weather_failure():
    """Test weather data fetch when weather API fails."""
    with (
        patch(
            "grillgauge.dashboard.data.weather.get_location",
            return_value=(37.7749, -122.4194),
        ),
        patch("grillgauge.dashboard.data.weather.get_weather", return_value=None),
    ):
        data = await get_weather_data()
        assert data is None
