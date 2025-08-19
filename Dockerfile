FROM ghcr.io/home-assistant/amd64-addon-base:15

# Install AppDaemon
RUN pip install appdaemon==4.3.4

# Copy files
COPY run.sh /
COPY appdaemon/ /appdaemon/

CMD [ "/run.sh" ]
