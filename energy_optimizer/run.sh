#!/usr/bin/env bash
set -e

# Activate virtual environment
source /opt/venv/bin/activate

# Start AppDaemon with configuration from /config
exec python3 -m appdaemon -c /config/appdaemon
