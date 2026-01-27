"""Unit tests for temperature widgets."""

from collections import deque
from unittest.mock import patch

import pytest

from grillgauge.dashboard.widgets.temperature import (
    GrillTemperatureWidget,
    MeatTemperatureWidget,
    TemperatureWidget,
)


class TestTemperatureWidget:
    """Test the base TemperatureWidget class."""

    def test_initialization_default(self):
        """Test widget initialization with default parameters."""
        max_points = 50
        widget = TemperatureWidget("http://localhost:9090")

        assert widget.prometheus_url == "http://localhost:9090"
        assert widget.temp_type == "meat"
        assert widget.max_points == max_points
        assert isinstance(widget.data_points, deque)
        assert widget.data_points.maxlen == max_points
        assert len(widget.data_points) == 0

    def test_initialization_custom(self):
        """Test widget initialization with custom parameters."""
        custom_max_points = 25
        widget = TemperatureWidget(
            prometheus_url="http://custom:9090",
            temp_type="grill",
            max_points=custom_max_points,
        )

        assert widget.prometheus_url == "http://custom:9090"
        assert widget.temp_type == "grill"
        assert widget.max_points == custom_max_points
        assert widget.data_points.maxlen == custom_max_points

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_temperature_history")
    async def test_on_mount_with_historical_data_full(self, mock_history):
        """Test on_mount with full historical data available."""
        expected_data_points = [20.0, 21.0, 22.0, 23.0, 24.0]
        max_points = 5
        mock_history.return_value = expected_data_points

        widget = TemperatureWidget("http://localhost:9090", max_points=max_points)
        await widget.on_mount()

        assert len(widget.data_points) == max_points
        assert list(widget.data_points) == expected_data_points
        assert widget.data == [0.0, *expected_data_points]  # 0 baseline prepended
        assert widget.summary == "24.0°C"

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_temperature_history")
    async def test_on_mount_with_historical_data_partial(self, mock_history):
        """Test on_mount with partial historical data."""
        partial_data = [22.0, 23.0, 24.0]
        max_points = 5
        mock_history.return_value = partial_data

        widget = TemperatureWidget("http://localhost:9090", max_points=max_points)
        await widget.on_mount()

        assert len(widget.data_points) == max_points
        # Should be padded with zeros at the start
        expected_points = [0.0, 0.0, *partial_data]
        assert list(widget.data_points) == expected_points
        assert widget.data == [0.0, *expected_points]
        assert widget.summary == "24.0°C"

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_temperature_history")
    async def test_on_mount_with_historical_data_excess(self, mock_history):
        """Test on_mount with more historical data than max_points."""
        excess_data = [18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0]
        max_points = 5
        mock_history.return_value = excess_data

        widget = TemperatureWidget("http://localhost:9090", max_points=max_points)
        await widget.on_mount()

        assert len(widget.data_points) == max_points
        # Should keep only the last 5 points
        assert list(widget.data_points) == [20.0, 21.0, 22.0, 23.0, 24.0]

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_temperature_history")
    async def test_on_mount_no_historical_data(self, mock_history):
        """Test on_mount when historical data query fails."""
        mock_history.return_value = None
        max_points = 3

        widget = TemperatureWidget("http://localhost:9090", max_points=max_points)
        await widget.on_mount()

        assert len(widget.data_points) == max_points
        assert list(widget.data_points) == [0.0, 0.0, 0.0]
        assert widget.data == [0.0, 0.0, 0.0, 0.0]
        assert widget.summary == "0.0°C"

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_meat_temperature")
    async def test_update_temperature_meat_success(self, mock_get_temp):
        """Test update_temperature for meat temperature with successful fetch."""
        mock_get_temp.return_value = 55.5
        expected_length = 4

        widget = TemperatureWidget("http://localhost:9090", temp_type="meat")
        # Pre-populate with some data
        widget.data_points.extend([50.0, 51.0, 52.0])

        await widget.update_temperature()

        assert len(widget.data_points) == expected_length
        assert list(widget.data_points) == [50.0, 51.0, 52.0, 55.5]
        assert widget.data == [0.0, 50.0, 51.0, 52.0, 55.5]
        assert widget.summary == "55.5°C"

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_grill_temperature")
    async def test_update_temperature_grill_success(self, mock_get_temp):
        """Test update_temperature for grill temperature with successful fetch."""
        mock_get_temp.return_value = 225.0
        expected_length = 4

        widget = TemperatureWidget("http://localhost:9090", temp_type="grill")
        widget.data_points.extend([200.0, 210.0, 220.0])

        await widget.update_temperature()

        assert len(widget.data_points) == expected_length
        assert list(widget.data_points) == [200.0, 210.0, 220.0, 225.0]
        assert widget.data == [0.0, 200.0, 210.0, 220.0, 225.0]
        assert widget.summary == "225.0°C"

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_meat_temperature")
    async def test_update_temperature_failure_with_existing_data(self, mock_get_temp):
        """Test update_temperature when fetch fails but has existing data."""
        mock_get_temp.return_value = None
        expected_length = 4

        widget = TemperatureWidget("http://localhost:9090", temp_type="meat")
        widget.data_points.extend([50.0, 51.0, 52.0])

        await widget.update_temperature()

        assert len(widget.data_points) == expected_length
        # Should use the last value when fetch fails
        assert list(widget.data_points) == [50.0, 51.0, 52.0, 52.0]
        assert widget.summary == "52.0°C"

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.temperature.get_meat_temperature")
    async def test_update_temperature_failure_no_existing_data(self, mock_get_temp):
        """Test update_temperature when fetch fails and no existing data."""
        mock_get_temp.return_value = None

        widget = TemperatureWidget("http://localhost:9090", temp_type="meat")

        await widget.update_temperature()

        assert len(widget.data_points) == 1
        assert list(widget.data_points) == [0.0]
        assert widget.summary == "0.0°C"

    def test_update_sparkline_empty_data(self):
        """Test update_sparkline with empty data points."""
        widget = TemperatureWidget("http://localhost:9090")

        widget.update_sparkline()

        # Should not crash, data should remain None or empty
        assert widget.data is None or widget.data == []

    def test_update_sparkline_with_data(self):
        """Test update_sparkline with data points."""
        widget = TemperatureWidget("http://localhost:9090")
        widget.data_points.extend([10.0, 20.0, 30.0])

        widget.update_sparkline()

        assert widget.data == [0.0, 10.0, 20.0, 30.0]  # 0 baseline prepended
        assert widget.summary == "30.0°C"

    def test_update_sparkline_deque_behavior(self):
        """Test that deque maxlen is respected."""
        max_points = 3
        widget = TemperatureWidget("http://localhost:9090", max_points=max_points)

        # Add more points than max_points
        for i in range(5):
            widget.data_points.append(float(i))

        assert len(widget.data_points) == max_points  # Should only keep last 3
        assert list(widget.data_points) == [2.0, 3.0, 4.0]

        widget.update_sparkline()
        assert widget.data == [0.0, 2.0, 3.0, 4.0]
        assert widget.summary == "4.0°C"


class TestMeatTemperatureWidget:
    """Test the MeatTemperatureWidget class."""

    def test_initialization(self):
        """Test MeatTemperatureWidget initialization."""
        default_max_points = 50
        widget = MeatTemperatureWidget("http://localhost:9090")

        assert widget.prometheus_url == "http://localhost:9090"
        assert widget.temp_type == "meat"
        assert widget.max_points == default_max_points
        assert isinstance(widget, TemperatureWidget)


class TestGrillTemperatureWidget:
    """Test the GrillTemperatureWidget class."""

    def test_initialization(self):
        """Test GrillTemperatureWidget initialization."""
        default_max_points = 50
        widget = GrillTemperatureWidget("http://localhost:9090")

        assert widget.prometheus_url == "http://localhost:9090"
        assert widget.temp_type == "grill"
        assert widget.max_points == default_max_points
        assert isinstance(widget, TemperatureWidget)
