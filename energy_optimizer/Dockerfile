# Use the official Home Assistant base image
FROM ghcr.io/home-assistant/amd64-base:latest

# Install system packages
RUN apk add --no-cache python3 py3-pip tzdata

# Create a virtual environment for AppDaemon
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install appdaemon==4.4.2 pytz

# Add virtual environment to PATH so python and pip point to it
ENV PATH="/opt/venv/bin:$PATH"

# Copy add-on files (adjust source folder if needed)
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Set the default command
CMD [ "/run.sh" ]
