# Use official Python slim image to avoid GHCR auth issues
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    bash curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install AppDaemon and required Python libraries
RUN pip install --no-cache-dir appdaemon requests pyyaml

# Copy add-on files
COPY run.sh /run.sh
COPY appdaemon/ /app/appdaemon/

# Make run.sh executable
RUN chmod a+x /run.sh

# Set default command
CMD ["/run.sh"]
