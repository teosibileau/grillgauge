"""Service resource usage statistics from Prometheus metrics.

Pure Prometheus solution using process-exporter and node-exporter metrics.
No systemctl or ps commands needed - works cross-platform.
"""

import time
from typing import Any

from grillgauge.dashboard.data import prometheus


def format_uptime(seconds: int) -> str:
    """Format uptime seconds into human-readable string.

    Args:
        seconds: Uptime in seconds

    Returns:
        Formatted string like '2d 3h 45m' or '3h 45m' or '45m'
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or not parts:  # Always show minutes if nothing else
        parts.append(f"{minutes}m")

    return " ".join(parts)


async def get_service_stats_prometheus(
    prometheus_url: str, services: list[str] | None = None
) -> list[dict[str, Any]]:
    """Get service stats from Prometheus metrics.

    Queries process-exporter metrics for CPU, memory, and uptime.
    Queries node-exporter for total system memory to calculate MEM%.

    Args:
        prometheus_url: Base Prometheus URL (e.g., http://localhost:9090)
        services: List of service names (default: ['grillgauge', 'prometheus'])

    Returns:
        List of service stat dictionaries with keys:
        - service: str (service name)
        - cpu: str (e.g., '2.5%')
        - mem: str (e.g., '1.2%')
        - mem_usage: str (e.g., '45.3MB')
        - uptime: str (e.g., '2d 3h 45m')
    """
    if services is None:
        services = ["grillgauge", "prometheus"]

    stats = []

    # Get total system memory (for MEM% calculation)
    total_mem_result = await prometheus.query_instant(
        prometheus_url, "node_memory_MemTotal_bytes"
    )
    total_mem_bytes = 1  # Default to avoid division by zero
    if total_mem_result and total_mem_result.get("result"):
        total_mem_bytes = float(total_mem_result["result"][0]["value"][1])

    for service in services:
        # Query metrics for this service
        # groupname matches ExeBase in process-exporter config
        groupname = service

        # CPU%: sum of system+user rates over last 1 minute, multiply by 100 for percentage
        cpu_query = (
            f"sum(rate(namedprocess_namegroup_cpu_seconds_total"
            f'{{groupname="{groupname}"}}[1m])) * 100'
        )
        cpu_result = await prometheus.query_instant(prometheus_url, cpu_query)

        mem_query = (
            f"namedprocess_namegroup_memory_bytes"
            f'{{groupname="{groupname}",memtype="resident"}}'
        )
        mem_result = await prometheus.query_instant(prometheus_url, mem_query)

        # Start time (oldest process in the group)
        start_query = (
            f"namedprocess_namegroup_oldest_start_time_seconds"
            f'{{groupname="{groupname}"}}'
        )
        start_result = await prometheus.query_instant(prometheus_url, start_query)

        # Check if all queries succeeded
        if not all([cpu_result, mem_result, start_result]):
            continue  # Skip if any query failed

        # Check if we got actual results (not empty arrays)
        if not all(
            [
                cpu_result.get("result"),
                mem_result.get("result"),
                start_result.get("result"),
            ]
        ):
            continue  # Skip if no data for this service

        # Extract values
        cpu_value = 0.0
        if cpu_result.get("result"):
            cpu_value = float(cpu_result["result"][0]["value"][1])

        mem_bytes = 0.0
        if mem_result.get("result"):
            mem_bytes = float(mem_result["result"][0]["value"][1])

        start_time = 0.0
        if start_result.get("result"):
            start_time = float(start_result["result"][0]["value"][1])

        # Calculate metrics
        mem_mb = mem_bytes / (1024 * 1024)
        mem_pct = (mem_bytes / total_mem_bytes) * 100

        # Calculate uptime
        uptime_seconds = int(time.time() - start_time)
        uptime_str = format_uptime(uptime_seconds)

        stats.append(
            {
                "service": service,
                "cpu": f"{cpu_value:.1f}%",
                "mem": f"{mem_pct:.1f}%",
                "mem_usage": f"{mem_mb:.1f}MB",
                "uptime": uptime_str,
            }
        )

    return stats


async def get_service_stats(
    prometheus_url: str | None = None, services: list[str] | None = None
) -> list[dict[str, Any]]:
    """Get service stats (backwards compatible wrapper).

    Args:
        prometheus_url: Prometheus URL (default: http://localhost:9090)
        services: Service names (default: ['grillgauge', 'prometheus'])

    Returns:
        List of service stat dictionaries. Empty list if Prometheus unavailable.
    """
    if prometheus_url is None:
        prometheus_url = "http://localhost:9090"

    return await get_service_stats_prometheus(prometheus_url, services)
