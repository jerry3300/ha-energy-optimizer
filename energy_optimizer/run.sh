#!/usr/bin/env bash
set -euo pipefail

echo "[INFO] Energy Optimizer add-on starting..."

# Read options provided by the add-on
OPTS_FILE="/data/options.json"
if [ -f "$OPTS_FILE" ]; then
  PERIOD=$(jq -r '.optimization_period // 300' "$OPTS_FILE")
  BATT_CURR=$(jq -r '.battery_charge_current // 25' "$OPTS_FILE")
  MIN_SOC=$(jq -r '.min_soc // 80' "$OPTS_FILE")
  OPT_SOC=$(jq -r '.opt_soc // 100' "$OPTS_FILE")
  MIN_BT=$(jq -r '.min_boiler_temp // 55' "$OPTS_FILE")
  OPT_BT=$(jq -r '.opt_boiler_temp // 70' "$OPTS_FILE")
  MIN_PRICE=$(jq -r '.min_spot_price // 300' "$OPTS_FILE")
  GRID_SOC=$(jq -r '.min_grid_charge_soc // 20' "$OPTS_FILE")
  TZSTR=$(jq -r '.timezone // "UTC"' "$OPTS_FILE")
else
  echo "[WARN] No options.json found, using defaults"
  PERIOD=300; BATT_CURR=25; MIN_SOC=80; OPT_SOC=100; MIN_BT=55; OPT_BT=70; MIN_PRICE=300; GRID_SOC=20; TZSTR="UTC"
fi

export TZ="$TZSTR"
echo "[INFO] Time zone: $TZ"

# Prepare AppDaemon config
mkdir -p /config/energy_optimizer
mkdir -p /app/config

# Write appdaemon.yaml
cat > /app/config/appdaemon.yaml <<EOF
appdaemon:
  time_zone: "${TZ}"
  plugins:
    HASS:
      type: hass
      ha_url: http://supervisor/core
      token: ${SUPERVISOR_TOKEN}
http:
  url: http://0.0.0.0:5050
admin:
api:
EOF

# apps.yaml with args from options
mkdir -p /app/config/apps
cat > /app/config/apps/apps.yaml <<EOF
energy_optimizer:
  module: energy_optimizer
  class: EnergyOptimizer
  optimization_period: ${PERIOD}
  battery_charge_current: ${BATT_CURR}
  min_soc: ${MIN_SOC}
  opt_soc: ${OPT_SOC}
  min_boiler_temp: ${MIN_BT}
  opt_boiler_temp: ${OPT_BT}
  min_spot_price: ${MIN_PRICE}
  min_grid_charge_soc: ${GRID_SOC}
EOF

# First-run helper files for user to import (sensors & dashboards)
if [ ! -f /config/energy_optimizer/sensors.yaml ]; then
  cp /app/resources/sensors.yaml /config/energy_optimizer/sensors.yaml || true
fi
if [ ! -f /config/energy_optimizer/dashboards.yaml ]; then
  cp /app/resources/dashboards.yaml /config/energy_optimizer/dashboards.yaml || true
fi
echo "[INFO] Helper files available in /config/energy_optimizer (import into HA)."

# Launch AppDaemon
echo "[INFO] Launching AppDaemon..."
exec appdaemon -c /app/config -D DEBUG
