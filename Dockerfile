ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install any dependencies your AppDaemon app might need
# For a basic AppDaemon app interacting with HA, often no additional packages are needed beyond what the base image provides.
# If you add external Python libraries to predictive_energy_optimizer.py, you'll need to install them here.
# For example:
# RUN pip install requests

# Copy AppDaemon related files
COPY run.sh /
COPY appdaemon /appdaemon

# Make the run script executable
RUN chmod a+x /run.sh

# Set the working directory to AppDaemon's root
WORKDIR /appdaemon

# Command to execute when the container starts
CMD ["/run.sh"]
