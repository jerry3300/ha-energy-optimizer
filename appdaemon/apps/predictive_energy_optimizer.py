import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta, timezone
import logging

# Configure logging to show info messages
logging.basicConfig(level=logging.INFO)

class PredictiveEnergyOptimizer(hass.Hass):

    def initialize(self):
        """Initializes the app and sets up listeners."""
        # Listen for a time pattern, this replaces the Home Assistant automation trigger
        # and allows AppDaemon to manage its own scheduling.
        # We will trigger every 15 minutes as per user request for the optimization period.
        optimization_period_minutes = self.get_arg('optimization_period', 15)
        self.run_every(self.run_optimizer, datetime.now(), optimization_period_minutes * 60)
        
        self.log(f"Predictive Energy Optimizer initialized. Running every {optimization_period_minutes} minutes.")

    def run_optimizer(self, kwargs):
        """Main function to run the energy optimization logic."""
        self.log("Running energy optimization script.")
        
        # Retrieve all necessary data from Home Assistant entities
        pv_power_now = self.get_state('sensor.solax_pv_power_total')
        house_load = self.get_state('sensor.solax_house_load')
        battery_capacity = self.get_state('sensor.solax_battery_capacity')
        boiler_temp = self.get_state('sensor.boiler_temp')
        grid_price_attr = self.get_state(entity_id='sensor.current_spot_electricity_price', attribute='all')
        
        # Get OTE hourly data from attributes
        grid_prices = self.get_ote_hourly_data(grid_price_attr)
        current_grid_price = grid_prices.get(self.now_plus_delta(minutes=0).hour, 0) # Get current hour's price

        solcast_forecast_today_attr = self.get_state(entity_id='sensor.solcast_pv_forecast_forecast_today', attribute='all')
        solcast_forecast_tomorrow_attr = self.get_state(entity_id='sensor.solcast_pv_forecast_forecast_tomorrow', attribute='all')
        
        # Parse Solcast detailed forecast
        solcast_forecast_today = solcast_forecast_today_attr.get('attributes', {}).get('detailedForecast', [])
        solcast_forecast_tomorrow = solcast_forecast_tomorrow_attr.get('attributes', {}).get('detailedForecast', [])

        sun_next_rising = self.get_state('sensor.sun_next_rising')
        sun_next_sunset = self.get_state('sensor.sun_next_sunset')
        
        # Retrieve user-defined parameters directly from input_number entities
        min_battery_soc = self.get_float_state('input_number.min_battery_soc')
        optimal_battery_soc = self.get_float_state('input_number.optimal_battery_soc')
        min_boiler_temp = self.get_float_state('input_number.min_boiler_temp')
        optimal_boiler_temp = self.get_float_state('input_number.optimal_boiler_temp')
        min_spot_price = self.get_float_state('input_number.min_spot_price') # CZK / MWh

        # Convert entity states to float, handling potential 'unknown' or 'unavailable' states
        pv_power = float(pv_power_now) if pv_power_now not in ['unknown', 'unavailable'] else 0.0
        load = float(house_load) if house_load not in ['unknown', 'unavailable'] else 0.0
        battery_soc_percent = float(battery_capacity) if battery_capacity not in ['unknown', 'unavailable'] else 0.0
        current_boiler_temp = float(boiler_temp) if boiler_temp not in ['unknown', 'unavailable'] else 0.0

        # Run the core logic
        self.optimize_energy_flow(
            pv_power,
            load,
            battery_soc_percent,
            current_boiler_temp,
            current_grid_price,
            grid_prices, # Pass full hourly prices for predictive decisions
            solcast_forecast_today,
            solcast_forecast_tomorrow, # Pass tomorrow's forecast for day-ahead planning
            sun_next_rising,
            sun_next_sunset,
            min_battery_soc,
            optimal_battery_soc,
            min_boiler_temp,
            optimal_boiler_temp,
            min_spot_price
        )

    def get_float_state(self, entity_id, default=0.0):
        """Helper to safely get float state or a default value."""
        state = self.get_state(entity_id)
        try:
            return float(state)
        except (ValueError, TypeError):
            self.log(f"Warning: Could not convert state of {entity_id} ('{state}') to float. Using default {default}.")
            return default

    def get_ote_hourly_data(self, grid_price_attr):
        """Parses OTE hourly data from entity attributes."""
        prices = {}
        if grid_price_attr and grid_price_attr.get('attributes'):
            # The OTE data generator maps date to value. We need to extract hour.
            for date_str, price_val in grid_price_attr['attributes'].items():
                try:
                    dt_object = datetime.fromisoformat(date_str).astimezone(self.get_timezone())
                    prices[dt_object.hour] = price_val
                except ValueError:
                    self.log(f"Could not parse OTE date: {date_str}")
        return prices
    
    def get_timezone(self):
        """Returns the timezone set in AppDaemon config."""
        return self.tz
        
    def convert_ha_time_to_datetime(self, time_string):
        """Converts Home Assistant's time string format to a timezone-aware datetime object."""
        try:
            # Home Assistant times are usually ISO formatted, and AppDaemon handles timezone.
            dt = datetime.fromisoformat(time_string).astimezone(self.get_timezone())
            return dt
        except ValueError as e:
            self.log(f"Error converting time string '{time_string}': {e}")
            return None

    def optimize_energy_flow(self, pv_current_power, house_current_load, battery_soc_percent, boiler_current_temp,
                             current_grid_price, ote_hourly_prices, solcast_forecast_today, solcast_forecast_tomorrow,
                             sun_next_rising, sun_next_sunset, min_batt_soc, opt_batt_soc, min_boiler_temp,
                             opt_boiler_temp, min_spot_price):
        """Core logic to decide energy flow."""

        current_time_local = self.datetime() # Get current time in local timezone
        sunset_time_local = self.convert_ha_time_to_datetime(sun_next_sunset)
        sunrise_time_local = self.convert_ha_time_to_datetime(sun_next_rising)

        self.log(f"Current time: {current_time_local}, Sunset: {sunset_time_local}, Sunrise: {sunrise_time_local}")
        
        # Determine current state needs
        boiler_needs_min_temp = boiler_current_temp < min_boiler_temp
        boiler_needs_opt_temp = boiler_current_temp < opt_boiler_temp
        battery_needs_min_charge = battery_soc_percent < min_batt_soc
        battery_needs_opt_charge = battery_soc_percent < opt_batt_soc

        # Default actions
        battery_charge_current = 0  # Default to no additional battery charging (Solax self-use handles basic)
        export_limit = 0            # Default to no power sent to grid
        boiler_relay_1_state = 'off'
        boiler_relay_2_state = 'off'

        # --- Predictive Logic (Day-ahead Planning Simplified) ---
        # This section uses the forecasts to make more informed decisions for the *next few hours* or *rest of the day*.
        
        # Estimate remaining PV production today (kWh)
        remaining_pv_today_kwh = self.get_remaining_forecast(solcast_forecast_today, current_time_local)
        self.log(f"Estimated remaining PV today: {remaining_pv_today_kwh:.2f} kWh")

        # Estimate remaining household consumption until sunset (very basic, could be improved with historical data)
        # For simplicity, assume average load for remaining daylight hours.
        # This is a placeholder; a real system would use historical consumption patterns.
        hours_until_sunset = (sunset_time_local - current_time_local).total_seconds() / 3600
        if hours_until_sunset > 0:
            # Let's assume an average hourly consumption for now. This needs to be refined with historical data.
            # You would ideally have an entity or calculation for 'forecasted_hourly_consumption'
            # For demonstration, let's just use current_load as a proxy for hourly average if it's not too low.
            # A better approach: use historical daily averages or rolling averages.
            estimated_remaining_consumption_kwh = house_current_load / 1000 * hours_until_sunset 
            # Or fetch a `sensor.forecasted_daily_home_consumption` from HA
        else:
            estimated_remaining_consumption_kwh = 0

        self.log(f"Estimated remaining consumption until sunset: {estimated_remaining_consumption_kwh:.2f} kWh")

        # Required energy to reach optimal battery SoC (kWh)
        # Battery capacity is 12 kWh.
        required_battery_kwh = (opt_batt_soc - battery_soc_percent) / 100 * 12 
        if required_battery_kwh < 0: required_battery_kwh = 0 # Already at or above optimal

        # Required energy to heat boiler to optimal (kWh)
        # Specific heat capacity of water = 4.186 kJ/(kg·°C)
        # Density of water = 1 kg/L. Boiler capacity = 120 L = 120 kg
        # Energy = mass * specific_heat * delta_T (Joules)
        # Convert to kWh: 1 kWh = 3.6 x 10^6 Joules
        required_boiler_kwh = 0
        if boiler_current_temp < opt_boiler_temp:
            delta_t = opt_boiler_temp - boiler_current_temp
            # Ensure delta_t is positive, if temp is already above optimal, no heating needed
            if delta_t > 0:
                # Assuming boiler efficiency (e.g., 90%)
                efficiency = 0.9 
                energy_joules = 120 * 4186 * delta_t # J
                required_boiler_kwh = (energy_joules / 3.6e6) / efficiency
        
        self.log(f"Required battery kWh: {required_battery_kwh:.2f} kWh")
        self.log(f"Required boiler kWh: {required_boiler_kwh:.2f} kWh")

        total_energy_needed_today = required_battery_kwh + required_boiler_kwh + estimated_remaining_consumption_kwh
        self.log(f"Total energy needed today (approx): {total_energy_needed_today:.2f} kWh")
        self.log(f"PV Current Power: {pv_current_power} W, House Load: {house_current_load} W")
        self.log(f"Battery SoC: {battery_soc_percent}%, Boiler Temp: {boiler_current_temp}°C")
        self.log(f"Current Grid Price: {current_grid_price} CZK/MWh")


        # --- Decision Logic ---
        
        # Stage 1: Critical Needs & Self-Sufficiency (Prioritized)
        # The Solax inverter handles self-consumption directly. Our logic is for *excess* PV.

        # If battery is critically low or boiler needs minimum temp, prioritize charging/heating
        if battery_needs_min_charge or boiler_needs_min_temp:
            self.log("Critical: Battery or boiler needs. Prioritizing charging/heating.")
            battery_charge_current = 25 # Max charge
            if boiler_needs_min_temp:
                boiler_relay_1_state = 'on'
                boiler_relay_2_state = 'on'
            export_limit = 0 # No export when critical needs exist
            
        # Stage 2: Optimal Charging & Heating before sunset or if PV is abundant
        elif current_time_local < sunset_time_local:
            # If we have significant surplus PV production (PV > Load significantly), consider optimal charging/heating
            # A simple heuristic: if PV production is > (house_load + some buffer for charging)
            # The 'some buffer' is effectively the inverter's behavior in self-use mode.
            
            # If we still need to reach optimal battery or boiler temp
            if battery_needs_opt_charge or boiler_needs_opt_temp:
                # Check if we expect enough PV for both (or have excess now)
                # This is where the predictive power comes in.
                # If remaining PV is sufficient to cover needs, we can be more flexible.
                if remaining_pv_today_kwh >= total_energy_needed_today: # Simplified check
                    self.log("Predicting enough PV today to meet optimal goals. Prioritizing optimal charging/heating.")
                    if battery_needs_opt_charge:
                        battery_charge_current = 25
                    if boiler_needs_opt_temp:
                        if boiler_current_temp < min_boiler_temp: # If still below minimum, use both
                             boiler_relay_1_state = 'on'
                             boiler_relay_2_state = 'on'
                        elif boiler_current_temp < opt_boiler_temp: # If between min and optimal, use one
                            boiler_relay_1_state = 'on'
                            boiler_relay_2_state = 'off'
                    export_limit = 0 # Still prioritize self-use

                # If remaining PV might not be enough, but current PV is high and we are trying to catch a peak
                elif pv_current_power > (house_current_load + 2000) and current_grid_price < min_spot_price: # Arbitrary "high PV" threshold
                    self.log("High current PV, but not enough for all optimal needs. Charging battery/boiler to absorb PV.")
                    if battery_needs_opt_charge:
                        battery_charge_current = 25
                    if boiler_needs_opt_temp:
                        if boiler_current_temp < min_boiler_temp:
                             boiler_relay_1_state = 'on'
                             boiler_relay_2_state = 'on'
                        elif boiler_current_temp < opt_boiler_temp:
                            boiler_relay_1_state = 'on'
                            boiler_relay_2_state = 'off'
                    export_limit = 0 # Keep internal for now

                else:
                    self.log("PV production not sufficient or not peaked yet for optimal goals. No action on battery/boiler beyond self-use.")
                    battery_charge_current = 0
                    boiler_relay_1_state = 'off'
                    boiler_relay_2_state = 'off'
                    
        # Stage 3: Export to Grid (Energy Arbitrage)
        # Only export if optimal goals are met OR if current PV is very high and prices are also high
        # AND we are past a certain time (e.g., mid-day, after initial charging).
        
        # Check if current time is suitable for export (e.g., after 9 AM and before 6 PM for common peak prices)
        is_daytime_export_window = current_time_local.hour >= 9 and current_time_local.hour <= 18
        
        # Check for upcoming high price windows for planned export
        # Look for the highest price hour in the next 6 hours, for example
        future_high_price_hour = self.find_highest_price_hour(ote_hourly_prices, current_time_local, look_ahead_hours=6)
        
        # Condition to export:
        # 1. Price is above minimum threshold AND
        # 2. Battery is at optimal OR remaining PV is enough to reach optimal OR it's a very high PV hour
        # AND (it's within the main export window OR a significant future high price is approaching)
        
        if current_grid_price > min_spot_price:
            self.log("Current spot price is above minimum threshold.")
            # Scenario A: Optimal goals met, so maximize export
            if battery_soc_percent >= opt_batt_soc and boiler_current_temp >= opt_boiler_temp:
                self.log("Optimal battery and boiler levels reached. Maximizing export.")
                export_limit = 12200
                battery_charge_current = 0 # No charging from PV, push to grid
                boiler_relay_1_state = 'off'
                boiler_relay_2_state = 'off'
            # Scenario B: Not at optimal yet, but it's a high price, and we are expecting more PV later
            # OR we are near the highest predicted price hour for the day.
            elif (remaining_pv_today_kwh > required_battery_kwh + required_boiler_kwh + 1) or \
                 (future_high_price_hour is not None and future_high_price_hour == current_time_local.hour):
                self.log("High spot price, and either sufficient future PV or at peak price hour. Considering export with buffer.")
                # We can export a portion, but keep a buffer for self-sufficiency
                export_limit = 12200 # Allow export, let Solax manage the actual surplus
                battery_charge_current = 0 # Prioritize export over charging *at this moment*
                boiler_relay_1_state = 'off'
                boiler_relay_2_state = 'off'
            else:
                self.log("High spot price, but not enough PV or goals not met. Prioritizing self-consumption.")
                export_limit = 0
        else:
            self.log(f"Current spot price ({current_grid_price}) is below minimum threshold ({min_spot_price}). No export.")
            export_limit = 0 # Do not export if price is too low
            
            # If price is low, prioritize charging battery and boiler, if not already at optimal
            if battery_soc_percent < opt_batt_soc:
                 battery_charge_current = 25
            if boiler_current_temp < opt_boiler_temp:
                if boiler_current_temp < min_boiler_temp:
                     boiler_relay_1_state = 'on'
                     boiler_relay_2_state = 'on'
                elif boiler_current_temp < opt_boiler_temp:
                    boiler_relay_1_state = 'on'
                    boiler_relay_2_state = 'off'

        # --- Grid Import for Battery (Only if Critical) ---
        # User specified: do not use grid energy to charge batteries unless below 20%.
        if battery_soc_percent < 20 and current_time_local > sunset_time_local:
            self.log("Battery capacity critically low after sunset. Charging from grid if necessary.")
            battery_charge_current = 25 # Allow grid charging by setting max current
            # Note: The Solax inverter's self-use mode still dictates *how* it charges.
            # You might need to change inverter mode via service call if you want direct grid-to-battery charging.
            # Since the user stated "Charger Use Mode = Self Use Mode all the time",
            # this means the inverter will *not* pull from grid to charge battery unless it's for critical loads,
            # or if the mode is changed. Our control assumes it will only use PV for battery.
            # If critical grid charging is truly needed, the user might need to adjust inverter settings or this script.
            
        # --- Apply Actions ---
        self.log(f"Setting number.solax_battery_charge_max_current to {battery_charge_current}A")
        self.call_service("number/set_value", entity_id="number.solax_battery_charge_max_current", value=battery_charge_current)

        self.log(f"Setting number.solax_export_control_user_limit to {export_limit}W")
        self.call_service("number/set_value", entity_id="number.solax_export_control_user_limit", value=export_limit)

        self.log(f"Setting switch.boiler_relay_1 to {boiler_relay_1_state}, switch.boiler_relay_2 to {boiler_relay_2_state}")
        self.call_service(f"switch/turn_{boiler_relay_1_state}", entity_id="switch.boiler_relay_1")
        self.call_service(f"switch/turn_{boiler_relay_2_state}", entity_id="switch.boiler_relay_2")

        self.log(f"Optimization cycle finished. PV: {pv_current_power}W, Load: {house_current_load}W, Batt SoC: {battery_soc_percent}%, Boiler Temp: {boiler_current_temp}°C, Grid Price: {current_grid_price} CZK/MWh.")


    def get_remaining_forecast(self, forecast_data, current_time):
        """Calculates the sum of remaining PV production for the day from Solcast detailedForecast."""
        total_remaining = 0
        for entry in forecast_data:
            period_start = self.convert_ha_time_to_datetime(entry['period_start'])
            # Only consider future periods that are today
            if period_start > current_time and period_start.date() == current_time.date():
                total_remaining += entry['pv_estimate']
        return total_remaining
        
    def find_highest_price_hour(self, ote_hourly_prices, current_time, look_ahead_hours=24):
        """Finds the hour with the highest spot price in a given look-ahead window."""
        highest_price = -1
        highest_price_hour = None
        
        for i in range(look_ahead_hours):
            check_time = current_time + timedelta(hours=i)
            hour = check_time.hour
            price = ote_hourly_prices.get(hour)
            
            if price is not None and price > highest_price:
                highest_price = price
                highest_price_hour = hour
        return highest_price_hour
