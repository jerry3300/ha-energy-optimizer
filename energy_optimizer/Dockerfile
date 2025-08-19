# Use slim Python 3.11 image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential git curl bash libffi-dev tzdata && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir homeassistant==2025.8 requests pytz numpy pandas

# Set working directory
WORKDIR /app

# Copy script and main code
COPY run.sh .
COPY energy_optimizer/ ./energy_optimizer/
COPY config.yaml .

# Make script executable
RUN chmod +x run.sh

# Run the script by default
CMD ["./run.sh"]

