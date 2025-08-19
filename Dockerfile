# Use official Home Assistant add-on base image (updated)
FROM ghcr.io/home-assistant/amd64-addon-base:18

# Set build arguments
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-addon-base:18
ARG BUILD_ARCH=amd64

# Set working directory
WORKDIR /app

# Install dependencies (AppDaemon + Python packages)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    && pip3 install --upgrade pip \
    && pip3 install appdaemon requests pyyaml

# Copy local files
COPY run.sh /run.sh
COPY appdaemon/ /app/appdaemon/

# Ensure run.sh is executable
RUN chmod a+x /run.sh

# Set default command
CMD [ "/run.sh" ]
