#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Energy Optimizer - AppDaemon Add-on Runner
# ==============================================================================

# Ensure AppDaemon configuration directory exists
mkdir -p /app/appdaemon/conf/apps

# Start AppDaemon with the configuration folder
appdaemon -c /app/appdaemon/conf
