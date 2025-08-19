# Base image
FROM ghcr.io/home-assistant/amd64-base:latest

# Install system packages
RUN apk add --no-cache python3 py3-pip tzdata

# Create virtual environment for AppDaemon
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade "pip<25.2" \
    && /opt/venv/bin/pip install --no-cache-dir appdaemon==4.4.2 pytz

# Add virtual environment to PATH
ENV PATH="/opt/venv/bin:$PATH"

# Copy add-on files
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Default command
CMD ["/run.sh"]
