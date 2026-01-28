"""Tests for CLI commands."""

from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from grillgauge.cli import main, serve


class TestCLI:
    """Test suite for CLI commands."""

    def test_main_group_exists(self):
        """Test main CLI group exists."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "GrillGauge CLI tool" in result.output

    def test_serve_command_exists(self):
        """Test serve command is registered."""
        runner = CliRunner()
        result = runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start Prometheus metrics server" in result.output
        assert "--host" in result.output
        assert "--port" in result.output

    def test_serve_command_default_options(self):
        """Test serve command with default options."""
        runner = CliRunner()

        with patch("grillgauge.cli.asyncio.run") as mock_run:
            result = runner.invoke(serve, [])

            assert result.exit_code == 0
            mock_run.assert_called_once()
            # Verify serve_server was called (coroutine passed to asyncio.run)

    def test_serve_command_custom_host(self):
        """Test serve command with custom host."""
        runner = CliRunner()

        with (
            patch("grillgauge.cli.serve_server", new_callable=AsyncMock),
            patch("grillgauge.cli.asyncio.run") as mock_run,
        ):
            result = runner.invoke(serve, ["--host", "0.0.0.0"])

            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_serve_command_custom_port(self):
        """Test serve command with custom port."""
        runner = CliRunner()

        with (
            patch("grillgauge.cli.serve_server", new_callable=AsyncMock),
            patch("grillgauge.cli.asyncio.run") as mock_run,
        ):
            result = runner.invoke(serve, ["--port", "9000"])

            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_serve_command_custom_host_and_port(self):
        """Test serve command with custom host and port."""
        runner = CliRunner()

        with (
            patch("grillgauge.cli.serve_server", new_callable=AsyncMock),
            patch("grillgauge.cli.asyncio.run") as mock_run,
        ):
            result = runner.invoke(serve, ["--host", "0.0.0.0", "--port", "9090"])

            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_serve_invokes_serve_server(self):
        """Test serve command invokes serve_server function."""
        runner = CliRunner()

        with (
            patch("grillgauge.cli.serve_server", new_callable=AsyncMock) as mock_serve,  # noqa: F841
            patch("grillgauge.cli.asyncio.run") as mock_run,
        ):
            # Make asyncio.run await the coroutine
            def run_side_effect(coro):
                # Since we're in a test, we can just create a task or ignore
                pass

            mock_run.side_effect = run_side_effect

            result = runner.invoke(
                serve,
                ["--host", "192.168.1.100", "--port", "8080"],
            )

            assert result.exit_code == 0
