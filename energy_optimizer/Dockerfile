# Use the Home Assistant base image
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

# Set environment variables
ENV LANG C.UTF-8
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime and build dependencies
RUN apk add --no-cache \
        python3 \
        py3-pip \
        tzdata \
        build-base \
        linux-headers \
        libffi-dev \
        git \
        bash \
        curl

# Create a virtual environment and install AppDaemon + pytz
RUN python3 -m venv /opt/venv \
    && pip install --upgrade "pip<25.2" \
    && pip install --no-cache-dir appdaemon==4.4.2 pytz

# Copy your add-on files (adjust this path if needed)
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Set the entrypoint
CMD [ "/run.sh" ]
