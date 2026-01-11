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
