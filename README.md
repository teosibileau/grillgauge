# grillgauge

A CLI tool for monitoring BLE meat probes and exposing metrics to Prometheus.

## Installation

This package uses Poetry for dependency management. To install:

1. Ensure you have Poetry installed: `curl -sSL https://install.python-poetry.org | python3 -`
2. Clone or download the project.
3. Run `poetry install` to install dependencies.

## Setup

## Usage

```bash
poetry run grillgauge --help
```

### Scanning and Configuring BLE Probes

```bash
poetry run grillgauge scan --timeout 10
```

This will automatically scan for BLE devices and classify them:
- Devices with battery and/or temperature capabilities → Added as probes
- Devices without capabilities → Added to ignored list

The system automatically generates probe names (Probe1, Probe2, etc.) and saves configuration to `.env`.

### Managing Ignored Devices

```bash
# View currently ignored devices
poetry run grillgauge ignored

# Remove a device from ignored list
poetry run grillgauge unignore AA:BB:CC:DD:EE:FF
```

## Development

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=grillgauge
```
