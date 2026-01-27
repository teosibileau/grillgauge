"""Probe temperature data queries from Prometheus metrics.

Queries temperature metrics from grillprobeE BBQ thermometer probes.
Uses base Prometheus client for all HTTP operations.
"""

from typing import Any

from grillgauge.dashboard.data import prometheus


async def get_meat_temperature(prometheus_url: str) -> float | None:
    """Get current meat probe temperature from Prometheus.

    Args:
        prometheus_url: Base Prometheus API URL

    Returns:
        Current meat temperature in Celsius, or None if unavailable
    """
    data = await prometheus.query_instant(
        prometheus_url, "grillgauge_meat_temperature_celsius"
    )
    return prometheus.extract_instant_value(data)


async def get_grill_temperature(prometheus_url: str) -> float | None:
    """Get current grill probe temperature from Prometheus.

    Args:
        prometheus_url: Base Prometheus API URL

    Returns:
        Current grill temperature in Celsius, or None if unavailable
    """
    data = await prometheus.query_instant(
        prometheus_url, "grillgauge_grill_temperature_celsius"
    )
    return prometheus.extract_instant_value(data)


async def get_temperature_history(
    prometheus_url: str,
    metric_name: str,
    duration_minutes: int = 5,
    step: int = 15,
) -> list[float]:
    """Query Prometheus for historical temperature data.

    Uses range query to fetch historical data points for sparkline initialization.

    Args:
        prometheus_url: Base Prometheus URL (e.g., http://localhost:9090)
        metric_name: Metric to query (e.g., grillgauge_meat_temperature_celsius)
        duration_minutes: How many minutes of history to fetch (default: 5)
        step: Step size in seconds between data points (default: 15)

    Returns:
        List of temperature values (floats), oldest to newest.
        Returns empty list on error.
    """
    import time

    end_time = int(time.time())
    start_time = end_time - (duration_minutes * 60)

    data = await prometheus.query_range(
        prometheus_url, metric_name, start_time, end_time, f"{step}s"
    )
    return prometheus.extract_range_values(data)


async def get_temperature_data(prometheus_url: str) -> dict[str, Any]:
    """Get both meat and grill temperatures from Prometheus.

    Args:
        prometheus_url: Base Prometheus API URL

    Returns:
        Dictionary with:
        {
            'meat': float or None,
            'grill': float or None
        }
    """
    meat_temp = await get_meat_temperature(prometheus_url)
    grill_temp = await get_grill_temperature(prometheus_url)

    return {
        "meat": meat_temp,
        "grill": grill_temp,
    }
