# grillgauge

A CLI tool for monitoring BLE meat probes with support for grillprobeE devices. Designed to run on Raspberry Pi with automated deployment via Ansible.

## Features

- Automatic grillprobeE device detection and configuration
- Real-time temperature monitoring for meat and grill probes
- Prometheus-compatible metrics server for monitoring integration
- Automated periodic BLE device scanning (every 5 minutes)
- Ansible-based deployment to Raspberry Pi
- Systemd service management for production reliability
- Colored logging output for better readability
- Simple configuration management

## Quick Start

### For Development (Local Testing)

1. Ensure you have Poetry installed: `curl -sSL https://install.python-poetry.org | python3 -`
2. Clone the project and install dependencies: `poetry install`
3. Run commands via Poetry: `poetry run grillgauge --help`

### For Production (Raspberry Pi Deployment)

1. **Prerequisites**:
   - Raspberry Pi (Raspberry Pi OS Lite 64-bit recommended)
   - SSH access configured with key-based authentication
   - [Ahoy](https://github.com/ahoy-cli/ahoy) installed on your local machine
   - Docker (for testing Ansible playbooks)

2. **Setup SSH access**:
   ```bash
   # Copy your SSH key to the Raspberry Pi
   ssh-copy-id pi@<raspberry-pi-ip>
   ```

3. **Configure production inventory**:
   ```bash
   ahoy provision setup
   ```
   This interactive wizard will generate your production inventory file with your Raspberry Pi's connection details.

4. **Deploy to Raspberry Pi**:
   ```bash
   ahoy provision deploy
   ```
   This will:
   - Install Python, BlueZ (Bluetooth stack), and all dependencies
   - Deploy the grillgauge application to `/opt/grillgauge`
   - Set up systemd services for metrics server and periodic scanning
   - Configure automatic device discovery every 5 minutes

5. **Verify deployment**:
   ```bash
   ahoy provision status
   ```

## Installation

### Development Installation

This package uses Poetry for dependency management. To install:

1. Ensure you have Poetry installed: `curl -sSL https://install.python-poetry.org | python3 -`
2. Clone or download the project.
3. Run `poetry install` to install dependencies.

### Production Deployment

See the [Quick Start](#quick-start) section for Raspberry Pi deployment via Ansible.

#### System Requirements

- **Development**: macOS, Linux, or Windows with Python 3.10+
- **Production**: Raspberry Pi with Raspberry Pi OS (64-bit recommended)
- **Bluetooth**: BlueZ stack (automatically installed via Ansible on production)
- **Hardware**: FMG SH253B grillprobeE thermometer

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

## Deployment Architecture

GrillGauge is deployed to Raspberry Pi using Ansible and runs as systemd services:

### Systemd Services

1. **grillgauge.service** - Main metrics server
   - Runs `grillgauge serve` on port 8000
   - Exposes Prometheus metrics at `/metrics`
   - Auto-starts on boot

2. **grillgauge-scan.timer** - Periodic device discovery
   - Scans for new BLE devices every 5 minutes
   - First scan runs 2 minutes after boot
   - Logs available via `journalctl -u grillgauge-scan`

### Ansible Provisioning

The deployment uses Ansible roles:

- **bluetooth** - Installs and configures BlueZ Bluetooth stack
- **grillgauge** - Deploys application and systemd services
- **prometheus** - (Optional) Prometheus server setup
- **grafana** - (Optional) Grafana dashboard setup

#### Ahoy Commands

```bash
# Setup production Raspberry Pi inventory (first time)
ahoy provision setup

# Test Ansible playbooks in Docker container
ahoy provision test

# Deploy to production Raspberry Pi
ahoy provision deploy

# Check service status on Raspberry Pi
ahoy provision status

# Show Python package versions
ahoy provision freeze
```

#### Configuration

Ansible variables can be customized in `ansible/roles/grillgauge/vars/main.yml`:

```yaml
grillgauge_scan_frequency_minutes: 5  # Scan interval
grillgauge_scan_timeout_seconds: 10   # Scan duration
```

### Monitoring on Raspberry Pi

```bash
# View metrics server logs
journalctl -u grillgauge -f

# View scan service logs
journalctl -u grillgauge-scan -f

# Check timer status
systemctl status grillgauge-scan.timer
systemctl list-timers grillgauge-scan.timer

# Check Bluetooth status
systemctl status bluetooth
```

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
