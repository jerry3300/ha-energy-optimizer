FROM python:3.11-slim

# Install OS dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential git curl bash libffi-dev tzdata && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir homeassistant==2025.8 requests pytz numpy pandas

# Set working directory
WORKDIR /app

# Copy mandatory files
COPY run.sh .
COPY config.yaml .

# Copy energy_optimizer if it exists
RUN mkdir -p energy_optimizer && \
    if [ -d "./energy_optimizer" ]; then \
        cp -r ./energy_optimizer/* energy_optimizer/; \
    fi

# Make script executable
RUN chmod +x run.sh

CMD ["./run.sh"]

