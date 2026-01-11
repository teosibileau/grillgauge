import tempfile
from pathlib import Path

import pytest

from grillgauge.scanner import DeviceScanner

DEFAULT_SCAN_TIMEOUT = 10.0

# Expected temperature values for testing
EXPECTED_MEAT_TEMP = 28.0
EXPECTED_GRILL_TEMP = 31.0


class TestDeviceScanner:
    @pytest.fixture
    def temp_env_file(self):
        """Class method fixture for temporary .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            yield f.name
        Path(f.name).unlink()

    @pytest.fixture
    def scanner(self, temp_env_file):
        """Class method fixture providing DeviceScanner instance."""
        scanner = DeviceScanner()
        scanner.env_manager.env_file = temp_env_file  # Override env file
        return scanner

    def test_scanner_initialization(self, scanner):
        """Test scanner initializes correctly."""
        assert scanner.timeout == DEFAULT_SCAN_TIMEOUT
        assert scanner.devices == []
        assert hasattr(scanner, "env_manager")

    def test_parse_temperature_valid_data(self, scanner):
        """Test parsing valid grillprobeE temperature data."""
        # Sample data: FF-FF-A8-02-C6-02-0C
        # Meat temp: (0x02A8 / 10.0) - 40.0 = 68.0 - 40.0 = 28.0°C
        # Grill temp: (0x02C6 / 10.0) - 40.0 = 71.0 - 40.0 = 31.0°C
        data = bytes([0xFF, 0xFF, 0xA8, 0x02, 0xC6, 0x02, 0x0C])
        meat_temp, grill_temp = scanner._parse_temperature(data)

        assert meat_temp == EXPECTED_MEAT_TEMP
        assert grill_temp == EXPECTED_GRILL_TEMP

    def test_parse_temperature_insufficient_data(self, scanner):
        """Test parsing temperature data with insufficient bytes."""
        data = bytes([0xFF, 0xFF, 0xA8])  # Only 3 bytes, need 7
        meat_temp, grill_temp = scanner._parse_temperature(data)

        assert meat_temp is None
        assert grill_temp is None

    def test_parse_temperature_invalid_data(self, scanner):
        """Test parsing temperature data with invalid values."""
        # Use data that would cause parsing errors
        data = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF])  # All FF bytes
        meat_temp, grill_temp = scanner._parse_temperature(data)

        # Should still parse but give extreme values
        assert meat_temp is not None
        assert grill_temp is not None
