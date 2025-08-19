#!/usr/bin/with-contenv bash
set -e

mkdir -p /config/appdaemon/logs
echo "[run.sh] Starting AppDaemon..."
exec python3 -m appdaemon -c /config/appdaemon
