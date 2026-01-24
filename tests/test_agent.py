"""Tests for Bluetooth pairing agent."""

import contextlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock dbus modules before importing agent
mock_dbus = MagicMock()
mock_dbus.UInt32 = lambda x: x  # Mock UInt32 to return the value directly
mock_dbus.service = MagicMock()
mock_dbus.service.Object = object  # Use plain object as base class
mock_dbus.service.method = lambda *args, **kwargs: lambda f: f  # noqa: ARG005
sys.modules["dbus"] = mock_dbus
sys.modules["dbus.service"] = mock_dbus.service
sys.modules["dbus.mainloop.glib"] = MagicMock()
sys.modules["gi"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()

from grillgauge.agent.agent import AutoPairingAgent  # noqa: E402


class TestAutoPairingAgent:
    """Test suite for AutoPairingAgent class."""

    @pytest.fixture
    def mock_bus(self):
        """Mock D-Bus system bus."""
        return MagicMock()

    @pytest.fixture
    def agent(self, mock_bus):
        """Create AutoPairingAgent instance with mocked D-Bus."""
        # Create instance without calling parent __init__
        agent = object.__new__(AutoPairingAgent)
        agent.path = "/test/agent"
        return agent

    def test_agent_initialization(self, agent):
        """Test agent initializes with correct path."""
        assert agent.path == "/test/agent"

    def test_release_method(self, agent):
        """Test Release method can be called without errors."""
        # Should not raise
        agent.Release()

    def test_authorize_service(self, agent):
        """Test AuthorizeService auto-authorizes without errors."""
        device_path = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"
        service_uuid = "0000fb00-0000-1000-8000-00805f9b34fb"

        # Should return None (auto-authorize)
        result = agent.AuthorizeService(device_path, service_uuid)
        assert result is None

    def test_request_confirmation(self, agent):
        """Test RequestConfirmation auto-confirms pairing."""
        device_path = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"
        passkey = 123456

        # Should return None (auto-confirm)
        result = agent.RequestConfirmation(device_path, passkey)
        assert result is None

    def test_request_authorization(self, agent):
        """Test RequestAuthorization auto-authorizes connections."""
        device_path = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"

        # Should return None (auto-authorize)
        result = agent.RequestAuthorization(device_path)
        assert result is None

    def test_request_pin_code(self, agent):
        """Test RequestPinCode returns default PIN."""
        device_path = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"

        pin = agent.RequestPinCode(device_path)
        assert pin == "0000"
        assert isinstance(pin, str)

    def test_request_passkey(self, agent):
        """Test RequestPasskey returns default passkey."""
        device_path = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"

        # Mock dbus.UInt32
        mock_uint32 = MagicMock(return_value=0)
        with patch("dbus.UInt32", mock_uint32):
            agent.RequestPasskey(device_path)

        # Verify dbus.UInt32 was called with 0
        mock_uint32.assert_called_once_with(0)

    def test_cancel_method(self, agent):
        """Test Cancel method can be called without errors."""
        # Should not raise
        agent.Cancel()


class TestAgentMain:
    """Test suite for agent main entry point."""

    @patch("grillgauge.agent.__main__.GLib")
    @patch("grillgauge.agent.__main__.dbus")
    @patch("grillgauge.agent.__main__.AutoPairingAgent")
    def test_main_registers_agent(self, mock_agent_class, mock_dbus, mock_glib):
        """Test main() registers agent with BlueZ."""
        from grillgauge.agent.__main__ import main

        # Setup mocks
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus

        mock_bluez_obj = MagicMock()
        mock_bus.get_object.return_value = mock_bluez_obj

        mock_manager = MagicMock()
        mock_dbus.Interface.return_value = mock_manager

        mock_mainloop = MagicMock()
        mock_glib.MainLoop.return_value = mock_mainloop

        # Make mainloop.run() exit immediately
        mock_mainloop.run.side_effect = KeyboardInterrupt()

        # Run main (will exit on KeyboardInterrupt)
        with contextlib.suppress(KeyboardInterrupt, SystemExit):
            main()

        # Verify agent was created
        mock_agent_class.assert_called_once()

        # Verify D-Bus objects were accessed
        mock_bus.get_object.assert_called_with("org.bluez", "/org/bluez")
        mock_dbus.Interface.assert_called_with(
            mock_bluez_obj, "org.bluez.AgentManager1"
        )

    @patch("grillgauge.agent.__main__.dbus")
    def test_main_handles_dbus_connection_error(self, mock_dbus):
        """Test main() exits gracefully on D-Bus connection failure."""
        from grillgauge.agent.__main__ import main

        # Make D-Bus connection fail
        mock_dbus.SystemBus.side_effect = Exception("Connection failed")
        mock_dbus.exceptions.DBusException = Exception

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("grillgauge.agent.__main__.GLib")
    @patch("grillgauge.agent.__main__.dbus")
    @patch("grillgauge.agent.__main__.AutoPairingAgent")
    def test_main_handles_registration_error(
        self, mock_agent_class, mock_dbus, mock_glib
    ):
        """Test main() exits gracefully on agent registration failure."""
        from grillgauge.agent.__main__ import main

        # Setup mocks
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus

        mock_bluez_obj = MagicMock()
        mock_bus.get_object.return_value = mock_bluez_obj

        mock_manager = MagicMock()
        mock_dbus.Interface.return_value = mock_manager

        # Make registration fail
        mock_manager.RegisterAgent.side_effect = Exception("Registration failed")
        mock_dbus.exceptions.DBusException = Exception

        # Should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
