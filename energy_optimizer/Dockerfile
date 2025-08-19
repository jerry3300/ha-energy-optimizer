# Base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
        bash \
        libffi-dev \
        tzdata && \
    rm -rf /var/lib/apt/lists/*

# Install AppDaemon and common dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir appdaemon==4.4.2

# Set working directory
WORKDIR /app

# Copy your project files
COPY run.sh .
COPY energy_optimizer/ ./energy_optimizer/
COPY dashboards/ ./dashboards/
COPY config.yaml .

# Make script executable
RUN chmod +x run.sh

# Default command
CMD ["./run.sh"]

