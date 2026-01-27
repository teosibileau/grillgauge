"""Unit tests for dashboard configuration."""

import os
from unittest.mock import patch

from grillgauge.dashboard.config import DashboardConfig


def test_config_auto_detect_defaults_to_localhost():
    """Test auto-detection defaults to localhost."""
    config = DashboardConfig.auto_detect()
    assert config.prometheus_url == "http://localhost:9090"


def test_config_env_override():
    """Test environment variable overrides."""
    custom_weather_interval = 300  # 5 minutes
    custom_service_interval = 10  # 10 seconds
    custom_temp_interval = 30  # 30 seconds

    with patch.dict(
        os.environ,
        {
            "PROMETHEUS_URL": "http://custom:9090",
            "WEATHER_UPDATE_INTERVAL": "300",
            "SERVICE_UPDATE_INTERVAL": "10",
            "TEMP_UPDATE_INTERVAL": "30",
        },
    ):
        config = DashboardConfig.auto_detect()

        assert config.prometheus_url == "http://custom:9090"
        assert config.weather_update_interval == custom_weather_interval
        assert config.service_update_interval == custom_service_interval
        assert config.temp_update_interval == custom_temp_interval


def test_config_prometheus_api_url():
    """Test Prometheus API URL property."""
    config = DashboardConfig(prometheus_url="http://localhost:9090")

    assert config.prometheus_api_url == "http://localhost:9090/api/v1/query"


def test_config_defaults():
    """Test default configuration values."""
    default_weather_interval = 600  # 10 minutes
    default_service_interval = 5  # 5 seconds
    default_temp_interval = 15  # 15 seconds

    config = DashboardConfig(prometheus_url="http://localhost:9090")

    assert config.weather_update_interval == default_weather_interval
    assert config.service_update_interval == default_service_interval
    assert config.temp_update_interval == default_temp_interval
