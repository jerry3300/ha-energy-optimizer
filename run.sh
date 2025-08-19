#!/usr/bin/env bash
set -e

# Optional: print start message
echo "Starting Home Energy Optimizer add-on..."

# Start AppDaemon
exec appdaemon -c /app/appdaemon/conf
