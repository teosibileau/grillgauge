"""Data fetching modules for dashboard widgets."""

from grillgauge.dashboard.data.probes import get_grill_temperature, get_meat_temperature
from grillgauge.dashboard.data.services import get_service_stats
from grillgauge.dashboard.data.weather import get_weather_data

__all__ = [
    "get_grill_temperature",
    "get_meat_temperature",
    "get_service_stats",
    "get_weather_data",
]
