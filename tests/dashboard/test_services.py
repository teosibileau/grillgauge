"""Unit tests for service statistics from Prometheus metrics."""

from unittest.mock import patch

import pytest

from grillgauge.dashboard.data.services import (
    format_uptime,
    get_service_stats,
    get_service_stats_prometheus,
)


def test_format_uptime_days():
    """Test uptime formatting with days."""
    assert format_uptime(186300) == "2d 3h 45m"


def test_format_uptime_hours():
    """Test uptime formatting with hours only."""
    assert format_uptime(13500) == "3h 45m"


def test_format_uptime_minutes():
    """Test uptime formatting with minutes only."""
    assert format_uptime(2700) == "45m"


def test_format_uptime_zero():
    """Test uptime formatting with zero seconds."""
    assert format_uptime(0) == "0m"


def test_format_uptime_single_day():
    """Test uptime formatting with exactly one day."""
    assert format_uptime(86400) == "1d"  # Only non-zero parts are shown


@pytest.mark.asyncio
async def test_get_service_stats_prometheus_success():
    """Test getting service stats with all metrics available."""

    # Mock prometheus.query_instant to return expected data
    async def mock_query(_prometheus_url, query):
        if "node_memory_MemTotal_bytes" in query:
            return {"result": [{"value": [0, "4363632640"]}]}  # 4GB RAM
        if "cpu_seconds_total" in query:
            return {"result": [{"value": [0, "2.5"]}]}  # 2.5% CPU
        if 'memtype="resident"' in query:
            return {"result": [{"value": [0, "47185920"]}]}  # 45MB
        if "oldest_start_time_seconds" in query:
            return {"result": [{"value": [0, "1706000000"]}]}  # Some timestamp
        return None

    with (
        patch(
            "grillgauge.dashboard.data.prometheus.query_instant", side_effect=mock_query
        ),
        patch("time.time", return_value=1706186300),  # 186300 seconds later
    ):
        stats = await get_service_stats_prometheus(
            "http://localhost:9090", ["grillgauge"]
        )

        assert len(stats) == 1
        assert stats[0]["service"] == "grillgauge"
        assert stats[0]["cpu"] == "2.5%"
        assert stats[0]["mem"] == "1.1%"  # 45MB / 4GB * 100
        assert stats[0]["mem_usage"] == "45.0MB"
        assert stats[0]["uptime"] == "2d 3h 45m"


@pytest.mark.asyncio
async def test_get_service_stats_prometheus_missing_metrics():
    """Test getting service stats when metrics are unavailable."""

    async def mock_query(_prometheus_url, _query):
        # Return None for all queries (metrics not available)
        return None

    with patch(
        "grillgauge.dashboard.data.prometheus.query_instant", side_effect=mock_query
    ):
        stats = await get_service_stats_prometheus(
            "http://localhost:9090", ["grillgauge"]
        )

        assert len(stats) == 0


@pytest.mark.asyncio
async def test_get_service_stats_prometheus_empty_results():
    """Test getting service stats when queries return empty results."""

    async def mock_query(_prometheus_url, _query):
        # Return empty result arrays
        return {"result": []}

    with patch(
        "grillgauge.dashboard.data.prometheus.query_instant", side_effect=mock_query
    ):
        stats = await get_service_stats_prometheus(
            "http://localhost:9090", ["grillgauge"]
        )

        assert len(stats) == 0


@pytest.mark.asyncio
async def test_get_service_stats_default_prometheus_url():
    """Test get_service_stats with default Prometheus URL."""

    async def mock_get_stats(prometheus_url, _services):
        assert prometheus_url == "http://localhost:9090"
        return []

    with patch(
        "grillgauge.dashboard.data.services.get_service_stats_prometheus",
        side_effect=mock_get_stats,
    ):
        stats = await get_service_stats()
        assert stats == []


@pytest.mark.asyncio
async def test_get_service_stats_default_services():
    """Test get_service_stats with default service list."""

    async def mock_get_stats(prometheus_url, _services):
        # services will be None from wrapper, gets set to default in prometheus func
        assert prometheus_url == "http://localhost:9090"
        return []

    with patch(
        "grillgauge.dashboard.data.services.get_service_stats_prometheus",
        side_effect=mock_get_stats,
    ):
        stats = await get_service_stats("http://localhost:9090")
        assert stats == []
