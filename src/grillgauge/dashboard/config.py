"""Dashboard configuration with auto-detection and environment overrides."""

import os
from dataclasses import dataclass


@dataclass
class DashboardConfig:
    """Configuration for the GrillGauge dashboard.

    Attributes:
        prometheus_url: Base URL for Prometheus API (e.g., http://localhost:9090)
        weather_update_interval: Seconds between weather updates (default: 600 = 10 min)
        service_update_interval: Seconds between service stats updates (default: 5)
        temp_update_interval: Seconds between temperature updates (default: 15)
    """

    prometheus_url: str
    weather_update_interval: int = 600  # 10 minutes
    service_update_interval: int = 5  # 5 seconds
    temp_update_interval: int = 15  # 15 seconds

    @classmethod
    def auto_detect(cls) -> "DashboardConfig":
        """Auto-detect configuration based on environment.

        Detection logic:
        1. Check PROMETHEUS_URL environment variable
        2. Default to localhost:9090 if not set

        Returns:
            DashboardConfig with detected settings
        """
        # Default to localhost, allow environment variable override
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

        # Allow interval overrides from environment
        weather_interval = int(os.getenv("WEATHER_UPDATE_INTERVAL", "600"))
        service_interval = int(os.getenv("SERVICE_UPDATE_INTERVAL", "5"))
        temp_interval = int(os.getenv("TEMP_UPDATE_INTERVAL", "15"))

        return cls(
            prometheus_url=prometheus_url,
            weather_update_interval=weather_interval,
            service_update_interval=service_interval,
            temp_update_interval=temp_interval,
        )

    @property
    def prometheus_api_url(self) -> str:
        """Get the full Prometheus API query URL.

        Returns:
            Full URL for Prometheus instant query endpoint
        """
        return f"{self.prometheus_url}/api/v1/query"
