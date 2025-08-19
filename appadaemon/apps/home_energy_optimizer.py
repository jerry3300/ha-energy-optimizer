import appdaemon.plugins.hass.hassapi as hass
import datetime
import statistics

class HomeEnergyOptimizer(hass.Hass):

    def initialize(self):
        """Initialize optimizer with default parameters."""
        # --- User parameters ---
        self.optimization_interval = 15  # minutes
        self.battery_max_current = 25  # A
        self.battery_min_soc = 80  # %
        self.battery_opt_soc = 100  # %
        self.boiler_min_temp = 55  # °C
        self.boiler_opt_temp = 70  # °C
        self.min_spot_price = 300  # CZK/MWh
        self.max_export_limit = 12200  # W
        self.history_days = 28  # For historical load average

        # Schedule periodic optimization
        self.run_every(self.optimize_energy, "now", self.optimization_interval * 60)

    def optimize_energy(self, kwargs):
        """Main optimization logic every interval."""
        now = datetime.datetime.now()
        today_weekday = now.weekday()  # 0 = Monday

        # --- Current states ---
        soc = float(self.get_state("sensor.solax_battery_capacity", default=0))
        boiler_temp = float(self.get_state("sensor.boiler_temp", default=25))
        pv_power = float(self.get_state("sensor.solax_pv_power_total", default=0))

        # --- Forecasts ---
        pv_forecast_attr = self.get_state("sensor.solcast_pv_forecast_forecast_today")
        spot_prices_attr = self.get_state("sensor.current_spot_electricity_price", attribute="all")
        spot_prices = self.extract_spot_prices(spot_prices_attr)

        # --- Predict home load using historical profile ---
        predicted_load = self.predict_home_load(today_weekday)

        # --- Extract PV forecast ---
        pv_forecast_hours = self.extract_pv_forecast(pv_forecast_attr)

        # --- Extract sunrise/sunset ---
        sun_next_set = self.get_state("sun.sun", attribute="next_setting")
        sun_next_rise = self.get_state("sun.sun", attribute="next_rising")

        # --- Compute optimized schedules ---
        battery_schedule, boiler_schedule, grid_schedule = self.compute_optimized_schedule(
            pv_forecast_hours, spot_prices, predicted_load, soc, boiler_temp, sun_next_set, sun_next_rise
        )

        # --- Apply current interval settings ---
        current_hour = now.hour
        self.call_service("number/set_value", entity_id="number.solax_battery_charge_max_current",
                          value=battery_schedule.get(current_hour, 0))

        # Boiler control
        boiler_power = boiler_schedule.get(current_hour, 0)
        if boiler_power == 0:
            self.turn_off("switch.boiler_relay_1")
            self.turn_off("switch.boiler_relay_2")
        elif boiler_power == 800:
            self.turn_on("switch.boiler_relay_1")
            self.turn_off("switch.boiler_relay_2")
        else:
            self.turn_on("switch.boiler_relay_1")
            self.turn_on("switch.boiler_relay_2")

        # Grid export control
        self.call_service("number/set_value", entity_id="number.solax_export_control_user_limit",
                          value=grid_schedule.get(current_hour, 0))

        self.log(f"[Hour {current_hour}] Battery: {battery_schedule.get(current_hour, 0)}A | "
                 f"Boiler: {boiler_power}W | Grid export: {grid_schedule.get(current_hour, 0)}W")

    def extract_spot_prices(self, spot_prices_attr):
        """Extract hourly spot prices from entity attributes."""
        prices = {}
        if spot_prices_attr and "attributes" in spot_prices_attr:
            for k, v in spot_prices_attr["attributes"].items():
                hour = datetime.datetime.fromisoformat(k).hour
                prices[hour] = float(v)
        return prices

    def extract_pv_forecast(self, pv_forecast_attr):
        """Extract hourly PV forecast in W."""
        forecast = [0]*24
        if pv_forecast_attr and "attributes" in pv_forecast_attr:
            detailed = pv_forecast_attr["attributes"].get("detailedForecast", [])
            for h, item in enumerate(detailed[:24]):
                forecast[h] = float(item.get("pv_estimate", 0))*1000
        return forecast

    def predict_home_load(self, weekday):
        """Predict next 24h home load using historical averages."""
        # Fetch last 4 weeks of history for this weekday
        hourly_avg = [0]*24
        for h in range(24):
            try:
                history = self.get_history("sensor.solax_house_load", start_days_ago=28)
                # Compute average load for this hour and same weekday
                values = [v["state"] for v in history if v["hour"] == h and v["weekday"] == weekday]
                if values:
                    hourly_avg[h] = statistics.mean(values)
            except:
                hourly_avg[h] = 0
        return hourly_avg

    def compute_optimized_schedule(self, pv_forecast, spot_prices, predicted_load, soc, boiler_temp, sunset, sunrise):
        """Compute battery, boiler, and grid schedules with advanced optimization."""
        battery_schedule = {}
        boiler_schedule = {}
        grid_schedule = {}

        for hour in range(24):
            pv_surplus = max(0, pv_forecast[hour] - predicted_load[hour])
            price = spot_prices.get(hour, 0)

            # Battery charge logic
            if soc < self.battery_opt_soc and pv_surplus > 0 and price < self.min_spot_price:
                battery_schedule[hour] = self.battery_max_current
                soc += 1
            else:
                battery_schedule[hour] = 0

            # Boiler logic
            if boiler_temp < self.boiler_opt_temp and pv_surplus > 0 and price < self.min_spot_price:
                if boiler_temp < self.boiler_min_temp:
                    boiler_schedule[hour] = 1600
                    boiler_temp += 2
                else:
                    boiler_schedule[hour] = 800
                    boiler_temp += 1
            else:
                boiler_schedule[hour] = 0

            # Grid export logic
            if price >= self.min_spot_price:
                grid_schedule[hour] = min(pv_surplus, self.max_export_limit)
            else:
                grid_schedule[hour] = 0

        return battery_schedule, boiler_schedule, grid_schedule
