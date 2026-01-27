"""Unit tests for services widget."""

from unittest.mock import patch

import pytest

from grillgauge.dashboard.widgets.services import ServicesWidget


class TestServicesWidget:
    """Test the ServicesWidget class."""

    def test_initialization(self):
        """Test ServicesWidget initialization."""
        widget = ServicesWidget()

        # Check DataTable properties are set correctly
        assert widget.show_header is True
        assert widget.zebra_stripes is True
        assert widget.cursor_type == "none"

    @patch("grillgauge.dashboard.widgets.services.ServicesWidget.run_worker")
    def test_on_mount(self, mock_run_worker):
        """Test widget setup on mount."""
        widget = ServicesWidget()

        # Mock the add_columns method since we're inheriting from DataTable
        with patch.object(widget, "add_columns") as mock_add_columns:
            widget.on_mount()

            # Verify columns are added correctly
            mock_add_columns.assert_called_once_with(
                "SERVICE",
                "CPU%",
                "MEM%",
                "MEM USAGE",
                "UPTIME",
            )

            # Verify worker is started
            mock_run_worker.assert_called_once()

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.services.DashboardConfig")
    async def test_update_services_with_data(self, mock_config_class):
        """Test service data update with available statistics."""
        # Mock the config
        mock_config = mock_config_class.auto_detect.return_value
        mock_config.prometheus_url = "http://localhost:9090"

        # Mock service stats data
        mock_stats = [
            {
                "service": "grillgauge",
                "cpu": "2.5%",
                "mem": "1.1%",
                "mem_usage": "45.0MB",
                "uptime": "2d 3h 45m",
            },
            {
                "service": "prometheus",
                "cpu": "1.2%",
                "mem": "0.8%",
                "mem_usage": "32.1MB",
                "uptime": "1d 12h 30m",
            },
        ]

        widget = ServicesWidget()

        with (
            patch(
                "grillgauge.dashboard.widgets.services.get_service_stats",
                return_value=mock_stats,
            ) as mock_get_stats,
            patch.object(widget, "clear") as mock_clear,
            patch.object(widget, "add_row") as mock_add_row,
        ):
            await widget.update_services()

            # Verify config was accessed
            mock_config_class.auto_detect.assert_called_once()

            # Verify service stats were fetched
            mock_get_stats.assert_called_once_with(
                prometheus_url="http://localhost:9090"
            )

            # Verify table was cleared
            mock_clear.assert_called_once()

            # Verify rows were added for each service (2 services in mock_stats)
            assert mock_add_row.call_count == len(mock_stats)
            mock_add_row.assert_any_call(
                "grillgauge",
                "2.5%",
                "1.1%",
                "45.0MB",
                "2d 3h 45m",
            )
            mock_add_row.assert_any_call(
                "prometheus",
                "1.2%",
                "0.8%",
                "32.1MB",
                "1d 12h 30m",
            )

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.services.DashboardConfig")
    async def test_update_services_no_data(self, mock_config_class):
        """Test service data update when no statistics are available."""
        # Mock the config
        mock_config = mock_config_class.auto_detect.return_value
        mock_config.prometheus_url = "http://localhost:9090"

        # Mock empty service stats
        mock_stats = []

        widget = ServicesWidget()

        with (
            patch(
                "grillgauge.dashboard.widgets.services.get_service_stats",
                return_value=mock_stats,
            ) as mock_get_stats,
            patch.object(widget, "clear") as mock_clear,
            patch.object(widget, "add_row") as mock_add_row,
        ):
            await widget.update_services()

            # Verify config was accessed
            mock_config_class.auto_detect.assert_called_once()

            # Verify service stats were fetched
            mock_get_stats.assert_called_once_with(
                prometheus_url="http://localhost:9090"
            )

            # Verify table was cleared
            mock_clear.assert_called_once()

            # Verify "Not available" row was added
            mock_add_row.assert_called_once_with(
                "Not available",
                "-",
                "-",
                "-",
                "-",
            )

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.services.DashboardConfig")
    async def test_update_services_single_service(self, mock_config_class):
        """Test service data update with a single service."""
        # Mock the config
        mock_config = mock_config_class.auto_detect.return_value
        mock_config.prometheus_url = "http://localhost:9090"

        # Mock single service stats
        mock_stats = [
            {
                "service": "grillgauge",
                "cpu": "5.0%",
                "mem": "2.1%",
                "mem_usage": "85.2MB",
                "uptime": "5d 1h 15m",
            }
        ]

        widget = ServicesWidget()

        with (
            patch(
                "grillgauge.dashboard.widgets.services.get_service_stats",
                return_value=mock_stats,
            ) as mock_get_stats,
            patch.object(widget, "clear") as mock_clear,
            patch.object(widget, "add_row") as mock_add_row,
        ):
            await widget.update_services()

            # Verify service stats were fetched
            mock_get_stats.assert_called_once_with(
                prometheus_url="http://localhost:9090"
            )

            # Verify table was cleared
            mock_clear.assert_called_once()

            # Verify single row was added
            mock_add_row.assert_called_once_with(
                "grillgauge",
                "5.0%",
                "2.1%",
                "85.2MB",
                "5d 1h 15m",
            )

    @pytest.mark.asyncio
    @patch("grillgauge.dashboard.widgets.services.DashboardConfig")
    async def test_update_services_config_error(self, mock_config_class):
        """Test service data update when config auto-detection fails."""
        # Mock config auto-detection to raise an exception
        mock_config_class.auto_detect.side_effect = Exception("Config error")

        widget = ServicesWidget()

        with (
            patch(
                "grillgauge.dashboard.widgets.services.get_service_stats"
            ) as mock_get_stats,
            patch.object(widget, "clear") as mock_clear,
            patch.object(widget, "add_row") as mock_add_row,
        ):
            # Should handle the error gracefully and show "Not available"
            await widget.update_services()

            # Verify get_service_stats was not called due to config error
            mock_get_stats.assert_not_called()

            # Verify table was cleared
            mock_clear.assert_called_once()

            # Verify "Not available" row was added
            mock_add_row.assert_called_once_with(
                "Not available",
                "-",
                "-",
                "-",
                "-",
            )
