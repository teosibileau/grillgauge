"""Base Prometheus query functions for dashboard data layer.

Provides low-level HTTP client for Prometheus API with query helpers.
All Prometheus metric queries should use these functions.
"""

from typing import Any

from httpx import AsyncClient, HTTPError, Timeout, TimeoutException


async def query_instant(
    prometheus_url: str,
    query: str,
    timeout: float = 5.0,
) -> dict[str, Any] | None:
    """Execute instant query to Prometheus API.

    Calls /api/v1/query endpoint for current metric values.

    Args:
        prometheus_url: Base Prometheus URL (e.g., http://localhost:9090)
        query: PromQL query string
        timeout: Request timeout in seconds (default: 5.0)

    Returns:
        Response data dict with 'result' key, or None on error.
        Format: {"result": [...], "resultType": "vector"}

    Examples:
        >>> data = await query_instant("http://localhost:9090", "up")
        >>> if data and data.get("result"):
        ...     print(f"Found {len(data['result'])} results")
    """
    query_url = f"{prometheus_url}/api/v1/query"

    try:
        async with AsyncClient(timeout=timeout) as client:
            response = await client.get(query_url, params={"query": query})
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                return data.get("data", {})
            return None

    except TimeoutException:
        return None
    except HTTPError:
        return None
    except Exception:
        return None


async def query_range(
    prometheus_url: str,
    query: str,
    start_time: int,
    end_time: int,
    step: str,
    timeout: float = 10.0,
) -> dict[str, Any] | None:
    """Execute range query to Prometheus API.

    Calls /api/v1/query_range endpoint for historical metric values.

    Args:
        prometheus_url: Base Prometheus URL (e.g., http://localhost:9090)
        query: PromQL query string
        start_time: Start timestamp (Unix seconds)
        end_time: End timestamp (Unix seconds)
        step: Step interval (e.g., "15s", "1m")
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        Response data dict with 'result' key, or None on error.
        Format: {"result": [...], "resultType": "matrix"}

    Examples:
        >>> import time
        >>> end = int(time.time())
        >>> start = end - 300  # 5 minutes ago
        >>> data = await query_range("http://localhost:9090", "up", start, end, "15s")
    """
    range_url = f"{prometheus_url}/api/v1/query_range"

    params = {
        "query": query,
        "start": start_time,
        "end": end_time,
        "step": step,
    }

    try:
        async with AsyncClient(timeout=Timeout(timeout)) as client:
            response = await client.get(range_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                return data.get("data", {})
            return None

    except Exception:
        return None


def extract_instant_value(data: dict[str, Any] | None) -> float | None:
    """Extract single float value from instant query result.

    Handles Prometheus instant query response format and extracts the
    first metric value as a float.

    Args:
        data: Prometheus instant query response data dict

    Returns:
        Float value from first result, or None if not found/invalid

    Examples:
        >>> data = {"result": [{"value": [1234567890, "42.5"]}]}
        >>> extract_instant_value(data)
        42.5
    """
    value_length_min = 2

    if not data:
        return None

    results = data.get("result", [])
    if not results or len(results) == 0:
        return None

    value = results[0].get("value")
    if not value or len(value) < value_length_min:
        return None

    try:
        return float(value[1])
    except (ValueError, TypeError, IndexError):
        return None


def extract_range_values(data: dict[str, Any] | None) -> list[float]:
    """Extract list of float values from range query result.

    Handles Prometheus range query response format and extracts all
    metric values as a list of floats (oldest to newest).

    Args:
        data: Prometheus range query response data dict

    Returns:
        List of float values (oldest to newest), empty list if no data

    Examples:
        >>> data = {"result": [{"values": [[1234567890, "25.0"], [1234567905, "26.0"]]}]}
        >>> extract_range_values(data)
        [25.0, 26.0]
    """
    value_length_min = 2

    if not data:
        return []

    results = data.get("result", [])
    if not results or len(results) == 0:
        return []

    values = results[0].get("values", [])
    if not values:
        return []

    try:
        return [float(val[1]) for val in values if len(val) >= value_length_min]
    except (ValueError, TypeError, IndexError):
        return []
