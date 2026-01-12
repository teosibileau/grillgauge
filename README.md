# grillgauge

A CLI tool for monitoring BLE meat probes with support for grillprobeE devices.

## Features

- Automatic grillprobeE device detection and configuration
- Real-time temperature monitoring for meat and grill probes
- Colored logging output for better readability
- Simple configuration management

## Installation

This package uses Poetry for dependency management. To install:

1. Ensure you have Poetry installed: `curl -sSL https://install.python-poetry.org | python3 -`
2. Clone or download the project.
3. Run `poetry install` to install dependencies.

## Usage

```bash
poetry run grillgauge --help
```

### Scanning for Devices

```bash
poetry run grillgauge scan --timeout 10
```

This scans for grillprobeE devices and automatically configures them when found. The tool will show progress and register compatible devices.

#### Example Output
```
INFO Scanning for grillprobeE devices...
INFO Found 1 potential grillprobeE devices
INFO Processing device: 7999C07F-3D73-E8F8-9D5A-AE8DCD4DDEFC
INFO Device name: BBQ ProbeE 26012
INFO Meat temp: 28.0°C, Grill temp: 31.0°C
INFO Successfully registered: BBQ ProbeE 26012
```

### Prometheus Metrics Server

```bash
# Secure default (localhost only)
poetry run grillgauge serve --port 8000

# Allow access from other machines on the network
poetry run grillgauge serve --host 0.0.0.0 --port 8000
```

Starts an HTTP server that exposes grillprobeE temperature metrics for Prometheus monitoring. The server runs background scans every 30 seconds and serves metrics at `/metrics`.

**Security Note**: By default, the server binds to `127.0.0.1` (localhost only) for security. Use `--host 0.0.0.0` only when you need Prometheus to scrape metrics from a different machine on your network.

#### Metrics Endpoints

- `/metrics` - Prometheus metrics output
- `/health` - Health check endpoint

#### Example Metrics Output

```
# HELP grillgauge_meat_temperature_celsius Meat probe temperature in Celsius
# TYPE grillgauge_meat_temperature_celsius gauge
grillgauge_meat_temperature_celsius{device_address="AA:BB:CC:DD:EE:FF",probe_name="bbq-probee-26012"} 65.5

# HELP grillgauge_grill_temperature_celsius Grill temperature in Celsius
# TYPE grillgauge_grill_temperature_celsius gauge
grillgauge_grill_temperature_celsius{device_address="AA:BB:CC:DD:EE:FF",probe_name="bbq-probee-26012"} 225.0

# HELP grillgauge_probe_status Probe connectivity status (1=online, 0=offline)
# TYPE grillgauge_probe_status gauge
grillgauge_probe_status{device_address="AA:BB:CC:DD:EE:FF",probe_name="bbq-probee-26012"} 1
```

#### Fault Tolerance

The metrics server maintains last known good temperature values during BLE connection failures, ensuring stable monitoring data even when probes temporarily disconnect.

### Device Configuration

Configured devices are saved to `.env`:

```
PROBE_MACS=7999C07F-3D73-E8F8-9D5A-AE8DCD4DDEFC
PROBE_NAMES=BBQ ProbeE 26012
PROBE_LAST_SEEN=2025-01-09T12:34:56.789012+00:00
```

## Compatibility

Designed specifically for FMG SH253B grillprobeE thermometers.

## Development

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=grillgauge
```

### Code Quality
Uses Ruff for linting and formatting, Pytest for testing, and Poetry for dependency management.
