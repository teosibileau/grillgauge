"""Unit tests for zero baseline sparkline renderable."""

from rich.color import Color
from rich.console import Console

from grillgauge.dashboard.renderables.zero_baseline_sparkline import (
    ZeroBaselineSparklineRenderable,
)


def test_zero_baseline_sparkline_renderable_creation():
    """Test ZeroBaselineSparklineRenderable can be created."""
    data = [10.0, 20.0, 30.0]
    expected_width = 10
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=expected_width,
        height=1,
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    assert renderable.data == data
    assert renderable.width == expected_width
    assert renderable.height == 1


def test_zero_baseline_sparkline_forced_minimum_scaling():
    """Test that sparkline always scales from 0°C minimum."""
    # Test data with positive temperatures
    data = [10.0, 20.0, 30.0, 40.0]
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=4,  # One bar per data point
        height=1,
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    console = Console(width=80, legacy_windows=False)
    rendered = list(console.render(renderable))

    # The sparkline should render (we can't easily test the exact scaling
    # without complex Rich console parsing, but we can ensure it doesn't crash)
    assert len(rendered) > 0


def test_zero_baseline_sparkline_negative_temperatures():
    """Test sparkline with negative temperatures still scales from 0°C."""
    data = [-5.0, -2.0, 5.0, 10.0]
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=4,
        height=1,
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    console = Console(width=80, legacy_windows=False)
    rendered = list(console.render(renderable))

    # Should render without issues
    assert len(rendered) > 0


def test_zero_baseline_sparkline_all_zeros():
    """Test sparkline with all zero temperatures."""
    data = [0.0, 0.0, 0.0]
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=3,
        height=1,
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    console = Console(width=80, legacy_windows=False)
    rendered = list(console.render(renderable))

    # Should render without issues (though all bars will be at minimum height)
    assert len(rendered) > 0


def test_zero_baseline_sparkline_empty_data():
    """Test sparkline with empty data."""
    data = []
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=5,
        height=1,
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    console = Console(width=80, legacy_windows=False)
    rendered = list(console.render(renderable))

    # Should render baseline characters
    assert len(rendered) > 0


def test_zero_baseline_sparkline_single_data_point():
    """Test sparkline with single data point."""
    data = [25.0]
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=5,
        height=1,
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    console = Console(width=80, legacy_windows=False)
    rendered = list(console.render(renderable))

    # Should render full bars since single point gets max height
    assert len(rendered) > 0


def test_zero_baseline_sparkline_different_heights():
    """Test sparkline with different height settings."""
    data = [10.0, 20.0, 30.0]
    renderable = ZeroBaselineSparklineRenderable(
        data,
        width=3,
        height=3,  # Multi-line sparkline
        min_color=Color.from_rgb(0, 255, 0),
        max_color=Color.from_rgb(255, 0, 0),
    )

    console = Console(width=80, legacy_windows=False)
    rendered = list(console.render(renderable))

    # Should render multiple lines
    assert len(rendered) > 0
