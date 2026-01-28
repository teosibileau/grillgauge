"""Unit tests for probe temperature data queries."""

from unittest.mock import patch

import pytest

from grillgauge.dashboard.data.probes import (
    get_grill_temperature,
    get_meat_temperature,
    get_temperature_data,
    get_temperature_history,
)


@pytest.mark.asyncio
async def test_get_meat_temperature_success():
    """Test successful meat temperature fetch."""
    mock_data = {"result": [{"value": [1234567890, "55.5"]}]}
    meat_temp_value = 55.5

    with patch(
        "grillgauge.dashboard.data.probes.query_instant",
        return_value=mock_data,
    ):
        temp = await get_meat_temperature("http://localhost:9090")
        assert temp == meat_temp_value


@pytest.mark.asyncio
async def test_get_meat_temperature_no_data():
    """Test meat temperature fetch with no data."""
    with patch(
        "grillgauge.dashboard.data.probes.query_instant",
        return_value={"result": []},
    ):
        temp = await get_meat_temperature("http://localhost:9090")
        assert temp is None


@pytest.mark.asyncio
async def test_get_meat_temperature_error():
    """Test meat temperature fetch with error."""
    with patch(
        "grillgauge.dashboard.data.probes.query_instant",
        return_value=None,
    ):
        temp = await get_meat_temperature("http://localhost:9090")
        assert temp is None


@pytest.mark.asyncio
async def test_get_grill_temperature_success():
    """Test successful grill temperature fetch."""
    mock_data = {"result": [{"value": [1234567890, "225.0"]}]}
    grill_temp_value = 225.0

    with patch(
        "grillgauge.dashboard.data.probes.query_instant",
        return_value=mock_data,
    ):
        temp = await get_grill_temperature("http://localhost:9090")
        assert temp == grill_temp_value


@pytest.mark.asyncio
async def test_get_grill_temperature_no_data():
    """Test grill temperature fetch with no data."""
    with patch(
        "grillgauge.dashboard.data.probes.query_instant",
        return_value={"result": []},
    ):
        temp = await get_grill_temperature("http://localhost:9090")
        assert temp is None


@pytest.mark.asyncio
async def test_get_grill_temperature_error():
    """Test grill temperature fetch with error."""
    with patch(
        "grillgauge.dashboard.data.probes.query_instant",
        return_value=None,
    ):
        temp = await get_grill_temperature("http://localhost:9090")
        assert temp is None


@pytest.mark.asyncio
async def test_get_temperature_data():
    """Test fetching both meat and grill temperatures."""
    expected_meat_temp = 55.5
    expected_grill_temp = 225.0

    with (
        patch(
            "grillgauge.dashboard.data.probes.get_meat_temperature",
            return_value=55.5,
        ),
        patch(
            "grillgauge.dashboard.data.probes.get_grill_temperature",
            return_value=225.0,
        ),
    ):
        data = await get_temperature_data("http://localhost:9090")
        assert data["meat"] == expected_meat_temp
        assert data["grill"] == expected_grill_temp


@pytest.mark.asyncio
async def test_get_temperature_data_partial():
    """Test fetching temperatures with partial data."""
    expected_grill_temp = 225.0

    with (
        patch(
            "grillgauge.dashboard.data.probes.get_meat_temperature",
            return_value=None,
        ),
        patch(
            "grillgauge.dashboard.data.probes.get_grill_temperature",
            return_value=225.0,
        ),
    ):
        data = await get_temperature_data("http://localhost:9090")
        assert data["meat"] is None
        assert data["grill"] == expected_grill_temp


@pytest.mark.asyncio
async def test_get_temperature_history_success():
    """Test successful historical temperature data fetch."""
    mock_data = {
        "result": [
            {
                "values": [
                    [1234567890, "25.0"],
                    [1234567905, "26.0"],
                    [1234567920, "27.0"],
                    [1234567935, "28.0"],
                    [1234567950, "29.0"],
                ]
            }
        ]
    }
    expected_data_points = 5

    with patch(
        "grillgauge.dashboard.data.probes.query_range",
        return_value=mock_data,
    ):
        temps = await get_temperature_history(
            "http://localhost:9090",
            "grillgauge_meat_temperature_celsius",
            duration_minutes=5,
            step=15,
        )
        assert len(temps) == expected_data_points
        assert temps == [25.0, 26.0, 27.0, 28.0, 29.0]


@pytest.mark.asyncio
async def test_get_temperature_history_no_data():
    """Test historical temperature fetch with no data."""
    with patch(
        "grillgauge.dashboard.data.probes.query_range",
        return_value={"result": []},
    ):
        temps = await get_temperature_history(
            "http://localhost:9090",
            "grillgauge_meat_temperature_celsius",
            duration_minutes=5,
            step=15,
        )
        assert len(temps) == 0


@pytest.mark.asyncio
async def test_get_temperature_history_error():
    """Test historical temperature fetch with API error."""
    with patch(
        "grillgauge.dashboard.data.probes.query_range",
        return_value=None,
    ):
        temps = await get_temperature_history(
            "http://localhost:9090",
            "grillgauge_meat_temperature_celsius",
            duration_minutes=5,
            step=15,
        )
        assert len(temps) == 0
