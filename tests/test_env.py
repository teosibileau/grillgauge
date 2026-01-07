import tempfile
from pathlib import Path

import pytest

from grillgauge.env import EnvManager


class TestEnvManager:
    EXPECTED_MIXED_PROBE_COUNT = 2

    @pytest.fixture
    def temp_env_file(self):
        """Class method fixture for temporary .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            yield f.name
        Path(f.name).unlink()

    @pytest.fixture
    def env_manager(self, temp_env_file):
        """Class method fixture providing EnvManager instance."""
        return EnvManager(temp_env_file)

    def test_empty_env(self, env_manager):
        """Test operations on empty .env file."""
        assert env_manager.list_probes() == []
        assert env_manager.list_ignored() == []

    def test_add_probe(self, env_manager):
        """Test adding a probe."""
        env_manager.add_probe("AA:BB:CC:DD:EE:FF", "TestProbe")
        probes = env_manager.list_probes()
        assert len(probes) == 1
        assert probes[0]["mac"] == "AA:BB:CC:DD:EE:FF"
        assert probes[0]["name"] == "TestProbe"
        assert "last_seen" in probes[0]

    def test_add_duplicate_probe_updates(self, env_manager):
        """Test adding probe with same MAC updates existing."""
        env_manager.add_probe("AA:BB:CC:DD:EE:FF", "TestProbe1")
        env_manager.add_probe("AA:BB:CC:DD:EE:FF", "TestProbe2")
        probes = env_manager.list_probes()
        assert len(probes) == 1
        assert probes[0]["name"] == "TestProbe2"

    def test_remove_probe(self, env_manager):
        """Test removing a probe."""
        env_manager.add_probe("AA:BB:CC:DD:EE:FF", "TestProbe")
        env_manager.remove_probe("AA:BB:CC:DD:EE:FF")
        assert env_manager.list_probes() == []

    def test_remove_nonexistent_probe(self, env_manager):
        """Test removing non-existent probe does nothing."""
        env_manager.remove_probe("AA:BB:CC:DD:EE:FF")
        assert env_manager.list_probes() == []

    def test_add_ignored(self, env_manager):
        """Test adding ignored device."""
        env_manager.add_ignored("XX:YY:ZZ:AA:BB:CC")
        assert "XX:YY:ZZ:AA:BB:CC" in env_manager.list_ignored()

    def test_add_duplicate_ignored_no_duplicates(self, env_manager):
        """Test adding same MAC to ignored doesn't create duplicates."""
        env_manager.add_ignored("XX:YY:ZZ:AA:BB:CC")
        env_manager.add_ignored("XX:YY:ZZ:AA:BB:CC")
        ignored = env_manager.list_ignored()
        assert ignored.count("XX:YY:ZZ:AA:BB:CC") == 1

    def test_remove_ignored(self, env_manager):
        """Test removing ignored device."""
        env_manager.add_ignored("XX:YY:ZZ:AA:BB:CC")
        env_manager.remove_ignored("XX:YY:ZZ:AA:BB:CC")
        assert env_manager.list_ignored() == []

    def test_remove_nonexistent_ignored(self, env_manager):
        """Test removing non-existent ignored device does nothing."""
        env_manager.remove_ignored("XX:YY:ZZ:AA:BB:CC")
        assert env_manager.list_ignored() == []

    def test_mixed_operations(self, env_manager):
        """Test probes and ignored coexist and operate independently."""
        env_manager.add_probe("AA:BB:CC:DD:EE:FF", "Probe1")
        env_manager.add_ignored("XX:YY:ZZ:AA:BB:CC")
        env_manager.add_probe("11:22:33:44:55:66", "Probe2")

        probes = env_manager.list_probes()
        ignored = env_manager.list_ignored()

        assert len(probes) == self.EXPECTED_MIXED_PROBE_COUNT
        assert len(ignored) == 1
        assert "XX:YY:ZZ:AA:BB:CC" in ignored

        # Verify probe data structure
        probe_macs = [p["mac"] for p in probes]
        probe_names = [p["name"] for p in probes]
        assert "AA:BB:CC:DD:EE:FF" in probe_macs
        assert "11:22:33:44:55:66" in probe_macs
        assert "Probe1" in probe_names
        assert "Probe2" in probe_names
