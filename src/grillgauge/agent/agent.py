"""BlueZ D-Bus pairing agent implementation."""

import logging

import dbus
import dbus.service

AGENT_INTERFACE = "org.bluez.Agent1"

logger = logging.getLogger(__name__)


class AutoPairingAgent(dbus.service.Object):
    """BlueZ pairing agent that auto-accepts all pairing requests.

    Implements org.bluez.Agent1 D-Bus interface for automatic BLE device
    pairing without user interaction. Uses "NoInputNoOutput" capability
    for maximum compatibility.
    """

    def __init__(self, bus, path):
        """Initialize the pairing agent.

        Args:
            bus: D-Bus system bus connection
            path: D-Bus object path for this agent
        """
        super().__init__(bus, path)
        self.path = path
        logger.info("Agent initialized at %s", path)

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):  # noqa: N802
        """Called when agent is unregistered."""
        logger.info("Agent released")

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):  # noqa: N802
        """Auto-authorize all services.

        Args:
            device: D-Bus path of the device
            uuid: Service UUID being authorized
        """
        logger.info("Auto-authorizing service %s for %s", uuid, device)

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):  # noqa: N802
        """Auto-confirm pairing (JustWorks/NoInputNoOutput).

        Args:
            device: D-Bus path of the device
            passkey: Passkey to confirm
        """
        logger.info("Auto-confirming pairing for %s with passkey %06d", device, passkey)

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):  # noqa: N802
        """Auto-authorize connection.

        Args:
            device: D-Bus path of the device
        """
        logger.info("Auto-authorizing connection from %s", device)

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):  # noqa: N802
        """Return default PIN code.

        Args:
            device: D-Bus path of the device

        Returns:
            Default PIN code "0000"
        """
        logger.info("Providing PIN code for %s", device)
        return "0000"

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):  # noqa: N802
        """Return default passkey.

        Args:
            device: D-Bus path of the device

        Returns:
            Default passkey 0
        """
        logger.info("Providing passkey for %s", device)
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):  # noqa: N802
        """Called when pairing is cancelled."""
        logger.warning("Pairing cancelled")
