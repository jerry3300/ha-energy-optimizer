#!/usr/bin/with-contenv bashio

# Set AppDaemon configuration path
APPD_CONFIG="/appdaemon/appdaemon.yaml"

# Get timezone from add-on options
TIMEZONE=$(bashio::config 'timezone')

# Set the timezone for the container
ln -snf /usr/share/zoneinfo/${TIMEZONE} /etc/localtime
echo ${TIMEZONE} > /etc/timezone

# Create AppDaemon config file
cat > ${APPD_CONFIG} <<EOF
secrets: /config/secrets.yaml # Standard Home Assistant secrets file
appdaemon:
  latitude: $(bashio::config 'latitude')
  longitude: $(bashio::config 'longitude')
  elevation: $(bashio::config 'elevation')
  time_zone: $(bashio::config 'timezone')
  plugins:
    HASS:
      type: hass
      ha_url: $(bashio::config 'appdaemon_url')
      # ha_key: YOUR_HA_LONG_LIVED_ACCESS_TOKEN # Usually not needed with AppDaemon HA add-on
logs:
  main_log:
    filename: /var/log/appdaemon.log
    log_level: INFO
  error_log:
    filename: /var/log/appdaemon.err
    log_level: ERROR
  access_log:
    filename: /var/log/appdaemon.access
    log_level: INFO
apps: /appdaemon/apps
EOF

# Start AppDaemon
bashio::log.info "Starting AppDaemon..."
appdaemon -c ${APPD_CONFIG}
