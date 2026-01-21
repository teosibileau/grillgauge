"""Entry point for running bluetooth pairing agent as a module."""

import logging
import signal
import sys

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

from .agent import AutoPairingAgent

AGENT_PATH = "/org/bluez/grillgauge/agent"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def main():
    """Run the Bluetooth pairing agent."""
    # Set up D-Bus main loop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    try:
        bus = dbus.SystemBus()
    except dbus.exceptions.DBusException:
        logger.exception("Failed to connect to D-Bus system bus")
        sys.exit(1)

    # Create and register agent
    try:
        AutoPairingAgent(bus, AGENT_PATH)

        obj = bus.get_object("org.bluez", "/org/bluez")
        manager = dbus.Interface(obj, "org.bluez.AgentManager1")

        manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
        manager.RequestDefaultAgent(AGENT_PATH)

        logger.info("Bluetooth pairing agent registered at %s", AGENT_PATH)
        logger.info("Capability: NoInputNoOutput (auto-accepts all pairing)")
        logger.info("Press Ctrl+C to exit")

    except dbus.exceptions.DBusException:
        logger.exception("Failed to register agent")
        sys.exit(1)

    # Set up GLib main loop
    mainloop = GLib.MainLoop()

    def signal_handler(_sig, _frame):
        """Handle shutdown signals."""
        logger.info("Shutting down...")
        try:
            manager.UnregisterAgent(AGENT_PATH)
            logger.info("Agent unregistered")
        except Exception:
            logger.warning("Failed to unregister agent", exc_info=True)
        mainloop.quit()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run main loop
    try:
        mainloop.run()
    except Exception:
        logger.exception("Main loop error")
        sys.exit(1)


if __name__ == "__main__":
    main()
