FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends     jq tzdata tini ca-certificates  && rm -rf /var/lib/apt/lists/*

# AppDaemon + deps
RUN python -m pip install --upgrade pip &&     pip install appdaemon==4.4.2 requests pytz aiohttp pandas

WORKDIR /app

# Copy add-on files
COPY run.sh /run.sh
COPY appdaemon /app/appdaemon
COPY resources /app/resources

RUN chmod +x /run.sh

# S6 not used; we use tini as simple init
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/run.sh"]
