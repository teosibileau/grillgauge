from datetime import datetime, timezone

from dotenv import dotenv_values, set_key


class EnvManager:
    """Manages grillgauge configuration stored in .env file."""

    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file

    def _get_list(self, key: str) -> list[str]:
        """Get a comma-separated list from .env file."""
        env_values = dotenv_values(self.env_file)
        value = env_values.get(key, "")
        return [item.strip() for item in value.split(",") if item.strip()]

    def _set_list(self, key: str, items: list[str]):
        """Set a comma-separated list to .env file."""
        value = ",".join(items)
        set_key(self.env_file, key, value)

    def add_probe(self, mac: str, name: str):
        """Add or update a probe."""
        macs = self._get_list("PROBE_MACS")
        names = self._get_list("PROBE_NAMES")
        last_seen = self._get_list("PROBE_LAST_SEEN")
        now = datetime.now(timezone.utc).isoformat()

        if mac in macs:
            idx = macs.index(mac)
            names[idx] = name
            last_seen[idx] = now
        else:
            macs.append(mac)
            names.append(name)
            last_seen.append(now)

        self._set_list("PROBE_MACS", macs)
        self._set_list("PROBE_NAMES", names)
        self._set_list("PROBE_LAST_SEEN", last_seen)

    def remove_probe(self, mac: str):
        """Remove a probe by MAC address."""
        macs = self._get_list("PROBE_MACS")
        names = self._get_list("PROBE_NAMES")
        last_seen = self._get_list("PROBE_LAST_SEEN")

        if mac in macs:
            idx = macs.index(mac)
            macs.pop(idx)
            names.pop(idx)
            last_seen.pop(idx)

            self._set_list("PROBE_MACS", macs)
            self._set_list("PROBE_NAMES", names)
            self._set_list("PROBE_LAST_SEEN", last_seen)

    def list_probes(self) -> list[dict[str, str]]:
        """Return list of probe dictionaries."""
        macs = self._get_list("PROBE_MACS")
        names = self._get_list("PROBE_NAMES")
        last_seen = self._get_list("PROBE_LAST_SEEN")

        probes = []
        for i in range(len(macs)):
            probe = {
                "mac": macs[i],
                "name": names[i] if i < len(names) else "Unknown",
                "last_seen": last_seen[i] if i < len(last_seen) else "",
            }
            probes.append(probe)
        return probes

    def add_ignored(self, mac: str):
        """Add a device to ignored list."""
        ignored = set(self._get_list("IGNORED_MACS"))
        ignored.add(mac)
        self._set_list("IGNORED_MACS", list(ignored))

    def remove_ignored(self, mac: str):
        """Remove a device from ignored list."""
        ignored = set(self._get_list("IGNORED_MACS"))
        ignored.discard(mac)
        self._set_list("IGNORED_MACS", list(ignored))

    def list_ignored(self) -> list[str]:
        """Return list of ignored MAC addresses."""
        return self._get_list("IGNORED_MACS")
