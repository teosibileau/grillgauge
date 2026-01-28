"""Weather data fetching from Open-Meteo API with IP-based geolocation."""

from typing import Any

import httpx


def wind_dir_to_text(degrees: float) -> str:
    """Convert wind direction from degrees to cardinal direction.

    Args:
        degrees: Wind direction in degrees (0-360)

    Returns:
        Cardinal direction (N, NE, E, SE, S, SW, W, NW)

    Examples:
        >>> wind_dir_to_text(0)
        'N'
        >>> wind_dir_to_text(90)
        'E'
        >>> wind_dir_to_text(180)
        'S'
        >>> wind_dir_to_text(270)
        'W'
    """
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((degrees + 22.5) / 45) % 8
    return dirs[idx]


def wmo_code_to_text(code: int) -> str:
    """Convert WMO weather code to human-readable text.

    WMO codes: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM

    Args:
        code: WMO weather code (0-99)

    Returns:
        Human-readable weather description

    Examples:
        >>> wmo_code_to_text(0)
        'Clear'
        >>> wmo_code_to_text(61)
        'Rain'
        >>> wmo_code_to_text(95)
        'Thunderstorm'
    """
    codes = {
        0: "Clear",
        1: "Partly Cloudy",
        2: "Partly Cloudy",
        3: "Partly Cloudy",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Drizzle",
        61: "Rain",
        63: "Rain",
        65: "Rain",
        71: "Snow",
        73: "Snow",
        75: "Snow",
        80: "Showers",
        81: "Showers",
        82: "Showers",
        95: "Thunderstorm",
        96: "Thunderstorm",
        99: "Thunderstorm",
    }
    return codes.get(code, "Unknown")


async def get_location() -> tuple[float | None, float | None]:
    """Get current location from IP address using ip-api.com.

    Returns:
        Tuple of (latitude, longitude), or (None, None) on error
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://ip-api.com/json/")
            response.raise_for_status()
            data = response.json()
            return data.get("lat"), data.get("lon")
    except (httpx.HTTPError, httpx.TimeoutException, ValueError):
        return None, None


async def get_weather(lat: float, lon: float) -> dict[str, Any] | None:
    """Fetch weather data from Open-Meteo API.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Weather data dictionary, or None on error
    """
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
            f"precipitation,cloud_cover,wind_speed_10m,wind_direction_10m,weather_code"
            f"&wind_speed_unit=kmh"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, httpx.TimeoutException, ValueError):
        return None


async def get_weather_data() -> dict[str, Any] | None:
    """Fetch complete weather data with auto-location.

    Returns:
        Dictionary with weather data in format suitable for display:
        {
            'temperature': float,
            'feels_like': float,
            'humidity': int,
            'wind_speed': float,
            'wind_direction': str (cardinal),
            'precipitation': float,
            'cloud_cover': int,
            'status': str (weather description)
        }

        Returns None if location or weather fetch fails.
    """
    # Get location from IP
    lat, lon = await get_location()
    if lat is None or lon is None:
        return None

    # Get weather data
    weather = await get_weather(lat, lon)
    if weather is None or "current" not in weather:
        return None

    current = weather["current"]

    # Extract and format data
    return {
        "temperature": current.get("temperature_2m", 0.0),
        "feels_like": current.get("apparent_temperature", 0.0),
        "humidity": current.get("relative_humidity_2m", 0),
        "wind_speed": current.get("wind_speed_10m", 0.0),
        "wind_direction": wind_dir_to_text(current.get("wind_direction_10m", 0)),
        "precipitation": current.get("precipitation", 0.0),
        "cloud_cover": current.get("cloud_cover", 0),
        "status": wmo_code_to_text(current.get("weather_code", 0)),
    }
