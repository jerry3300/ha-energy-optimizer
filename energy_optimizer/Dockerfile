ARG BUILD_FROM=ghcr.io/hassio-addons/base:14.2.3
FROM ${BUILD_FROM}

# Install Python + AppDaemon
RUN apk add --no-cache python3 py3-pip tzdata && \
    pip3 install --no-cache-dir appdaemon==4.4.2 pytz

# Copy our AppDaemon config and apps
COPY appdaemon /config/appdaemon/

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

# S6 overlay entrypoint
CMD [ "/run.sh" ]
