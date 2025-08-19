# Use Python 3.13 slim image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    libzstd-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install high-performance compression Python package
RUN pip install --no-cache-dir zlib-ng

# Install Home Assistant and additional packages
RUN pip install --no-cache-dir homeassistant==2025.8 requests pytz numpy pandas

# Set working directory
WORKDIR /config

# Expose Home Assistant default port
EXPOSE 8123

# Run Home Assistant
CMD ["hass", "--config", "/config"]
