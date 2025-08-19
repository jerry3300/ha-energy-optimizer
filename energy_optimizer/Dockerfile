# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set environment variables
ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

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

# Upgrade pip and install required Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        homeassistant==2025.8 \
        requests \
        pytz \
        numpy \
        pandas

# Set working directory
WORKDIR /app

# Copy your add-on files (adjust if your add-on has more files)
COPY . /app

# Set entrypoint or command for the add-on (adjust as needed)
CMD ["python", "main.py"]


