import tempfile
from pathlib import Path

import pytest

from grillgauge.scanner import DeviceScanner

DEFAULT_SCAN_TIMEOUT = 10.0


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

    def test_generate_probe_name_no_conflicts(self, scanner):
        """Test name generation with no existing probes."""
        existing_probes = {}
        name = scanner._generate_probe_name(existing_probes)
        assert name == "Probe1"

    def test_generate_probe_name_with_conflicts(self, scanner):
        """Test name generation avoids conflicts."""
        existing_probes = {
            "mac1": {"name": "Probe1"},
            "mac2": {"name": "Probe2"},
            "mac3": {"name": "Probe4"},
        }
        name = scanner._generate_probe_name(existing_probes)
        assert name == "Probe3"  # Should find the next available number

    def test_generate_probe_name_skips_taken_numbers(self, scanner):
        """Test name generation skips taken numbers."""
        existing_probes = {
            "mac1": {"name": "Probe1"},
            "mac2": {"name": "Probe3"},
        }
        name = scanner._generate_probe_name(existing_probes)
        assert name == "Probe2"  # Should find Probe2 as available
