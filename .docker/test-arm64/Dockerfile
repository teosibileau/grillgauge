# Minimal Debian ARM64 base for testing Ansible provisioning
FROM debian:bookworm-slim

# Essential system tools for Ansible provisioning
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    python3 \
    python3-pip \
    python3-dev \
    python3-apt \
    python3-packaging \
    python3-setuptools \
    build-essential \
    systemd \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Ensure Ansible can create temporary directories
RUN mkdir -p /tmp/grillgauge

# Keep container running for interactive use
# CMD ["sleep", "infinity"]
CMD ["/lib/systemd/systemd"]
