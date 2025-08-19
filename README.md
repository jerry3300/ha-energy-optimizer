Home Energy Optimizer Add-on for Home Assistant
This add-on provides a predictive energy management system for your Home Assistant instance. Its primary goal is to maximize revenue from selling surplus solar energy back to the grid during high spot price periods, while simultaneously ensuring your home's energy self-sufficiency by optimally charging your battery and heating your water boiler.

Features
Intelligent Grid Export: Sells energy to the grid primarily during high spot electricity prices from OTE (Czech Day-Ahead Market data).

Battery Management: Aims to charge your FVE battery to a user-defined optimal level (default 100%) by sunset, prioritizing solar energy. It avoids charging from the grid unless absolutely critical (e.g., battery below 20%).

Boiler Optimization: Heats your hot water boiler to a user-defined optimal temperature (default 70°C) by sunset, utilizing surplus solar power in fine steps (0W, 800W, 1600W).

Day-Ahead Predictive Scheduling: Uses hourly solar forecasts from Solcast and hourly spot electricity prices from OTE to make informed decisions about energy flow.

User-Configurable Parameters: Easily adjust key optimization parameters directly from your Home Assistant UI.

Requirements
Before installing this add-on, ensure you have the following Home Assistant integrations and entities configured and working:

Solax Integration: For inverter data (sensor.solax_grid_export, sensor.solax_grid_import, sensor.solax_house_load, sensor.solax_battery_power_charge, sensor.solax_pv_power_total, sensor.solax_today_s_export_energy, sensor.solax_today_s_import_energy, sensor.solax_battery_input_energy_today, sensor.solax_battery_output_energy_today, sensor.solax_today_s_solar_energy, number.solax_battery_charge_max_current, sensor.solax_battery_voltage_charge, sensor.solax_battery_capacity, number.solax_export_control_user_limit).

Home Assistant CZ Energy Spot Prices Add-on: For OTE electricity spot prices (sensor.current_spot_electricity_price).

Solcast Add-on: For PV production forecasts (sensor.solcast_pv_forecast_forecast_today, sensor.solcast_pv_forecast_forecast_tomorrow, etc., specifically accessing detailedForecast attributes).

Sun Integration: Home Assistant's built-in sun entities (sun.sun, sensor.sun_next_rising, sensor.sun_next_sunset).

Boiler Control: Entities for your boiler relays (switch.boiler_relay_1, switch.boiler_relay_2) and temperature sensor (sensor.boiler_temp).

AppDaemon: This add-on runs as an AppDaemon app. You need to have the official Home Assistant AppDaemon add-on installed and running.

Installation
Add Custom Add-on Repository:

In Home Assistant, navigate to Settings > Add-ons.

Click on the Add-on Store tab (bottom right corner).

Click the three dots menu (top right) and select Repositories.

Add the URL of your GitHub repository (e.g., https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME) and click Add.

Close the repository list and refresh the Add-on Store page (you might need to refresh your browser).

You should now see the "Energy Optimizer" add-on listed under "Custom add-ons".

Install the Energy Optimizer Add-on:

Click on the "Energy Optimizer" add-on.

Click Install.

After installation, go to the Configuration tab for the add-on. Verify the appdaemon_url and timezone settings. The timezone should be Europe/Prague for Zvole. Adjust if necessary.

Click Save.

Start the Add-on:

Go to the Info tab of the "Energy Optimizer" add-on.

Click Start.

Check the Logs tab to ensure AppDaemon starts successfully and your predictive_energy_optimizer app initializes without errors.

Add Home Assistant Configuration (YAML):

You need to add the following input_number entities to your Home Assistant configuration.yaml file (or a split file like input_numbers.yaml if you use that structure). These will create UI controls for the optimization parameters.

<details>
<summary>Click to expand Home Assistant YAML Configuration</summary>

# configuration.yaml or input_numbers.yaml
input_number:
  optimization_period:
    name: Optimization Period (minutes)
    min: 5
    max: 60
    step: 5
    initial: 15
    unit_of_measurement: min
    icon: mdi:timer-cog

  min_battery_soc:
    name: Minimum Required Battery SoC
    min: 0
    max: 100
    step: 1
    initial: 80
    unit_of_measurement: '%'
    icon: mdi:battery-alert

  optimal_battery_soc:
    name: Optimal Battery SoC
    min: 0
    max: 100
    step: 1
    initial: 100
    unit_of_measurement: '%'
    icon: mdi:battery-charging

  min_boiler_temp:
    name: Minimum Boiler Temperature
    min: 40
    max: 80
    step: 1
    initial: 55
    unit_of_measurement: °C
    icon: mdi:thermometer-minus

  optimal_boiler_temp:
    name: Optimal Boiler Temperature
    min: 40
    max: 80
    step: 1
    initial: 70
    unit_of_measurement: °C
    icon: mdi:thermometer-check

  min_spot_price:
    name: Minimum Spot Price to Export
    min: 0
    max: 5000
    step: 10
    initial: 300
    unit_of_measurement: CZK/MWh
    icon: mdi:currency-eur

</details>

After adding these, restart Home Assistant Core (Developer Tools -> YAML -> Restart Core, or full HA restart).

How it Works
The add-on works by running a Python script within an AppDaemon container. This script:

Reads Sensor Data: Gathers current data from your Solax inverter, boiler, and forecasts from OTE and Solcast.

Analyzes & Predicts: Uses solar forecasts and historical consumption (if you integrate it) to predict future energy availability and demand. It also looks at the hourly OTE spot prices to identify peak export opportunities.

Makes Decisions: Based on configurable parameters (e.g., desired battery SoC, boiler temperature, minimum export price) and the predictive analysis, it determines the optimal strategy for the current time.

Controls Devices: Adjusts your number.solax_battery_charge_max_current and number.solax_export_control_user_limit entities, and controls switch.boiler_relay_1 and switch.boiler_relay_2.

Fine-tuning & Customization
Input Numbers: The input_number entities in Home Assistant are your primary way to fine-tune the optimization goals. Experiment with these values to find what works best for your specific needs and energy patterns.

AppDaemon Script (predictive_energy_optimizer.py):

The predictive logic for energy consumption (estimated_remaining_consumption_kwh) is currently a basic placeholder. To improve accuracy, you could:

Integrate Historical Consumption: Develop a method to access and average your sensor.solax_house_load data over previous days/weeks, especially considering weekly patterns (weekdays vs. weekends). Home Assistant's history statistics can be very useful here.

Machine Learning (Advanced): For highly accurate predictions, you might consider training a simple machine learning model (e.g., a linear regression) using historical PV production, consumption, weather forecasts, and time-of-day/week as features.

The find_highest_price_hour function can be expanded to consider not just the single highest price, but periods of high prices for more sustained export.

The "PV peak approaching" detection is simplistic. A more robust solution could analyze the solcast_pv_forecast_forecast_today for a significant rise in pv_estimate over the next few hours.

Boiler Efficiency: The script uses a placeholder efficiency = 0.9 for boiler heating. If you have data on your boiler's actual efficiency, adjust this value for more accurate calculations.

Troubleshooting
Check Add-on Logs: The first place to look for issues is the "Logs" tab of the "Energy Optimizer" add-on in Home Assistant.

Home Assistant Logs: Check your main Home Assistant logs (Settings -> System -> Logs) for any related errors or warnings.

Entity States: Ensure all required sensor and number entities mentioned in the "Requirements" section are available and reporting valid numerical states.

Timezones: Verify that your Home Assistant timezone and the timezone configured in the add-on's config.yaml (and thus passed to AppDaemon) are correct for Zvole (Central European Summer Time, Europe/Prague).

This video can help you understand the basics of AppDaemon and how to create simple apps within Home Assistant: Home Assistant and AppDaemon.
