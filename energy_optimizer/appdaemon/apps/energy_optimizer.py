import appdaemon.plugins.hass.hassapi as hass

class EnergyOptimizer(hass.Hass):
    def initialize(self):
        # Load config options from apps.yaml
        self.period = int(self.args.get("optimization_period", 300))  # default 5 min
        self.battery_charge_current = int(self.args.get("battery_charge_current", 25))
        self.min_soc = int(self.args.get("min_soc", 80))
        self.target_soc = int(self.args.get("target_soc", 100))
        self.boiler_temp_min = int(self.args.get("boiler_temp_min", 55))
        self.boiler_temp_opt = int(self.args.get("boiler_temp_optimal", 70))
        self.min_spot_price = float(self.args.get("min_spot_price", 300))

        self.log("Energy Optimizer initialized with settings: {}".format(self.args))

        # Run periodically
        self.run_every(self.optimize_energy, "now", self.period)

    def optimize_energy(self, kwargs):
        try:
            soc = float(self.get_state("sensor.solax_battery_capacity") or 0)
            pv_power = float(self.get_state("sensor.solax_pv_power_total") or 0)
            house_load = float(self.get_state("sensor.solax_house_load") or 0)
            spot_price = float(self.get_state("sensor.current_spot_electricity_price") or 0)
            boiler_temp = float(self.get_state("sensor.boiler_temp") or 0)

            self.log(f"SoC={soc}%, PV={pv_power}W, Load={house_load}W, Spot={spot_price}, Boiler={boiler_temp}°C")

            surplus = pv_power - house_load
            if surplus < 0:
                surplus = 0

            # --- Battery control ---
            if soc < self.min_soc:
                # Always charge battery until minimum SoC
                self.call_service("number/set_value",
                                  entity_id="number.solax_battery_charge_max_current",
                                  value=self.battery_charge_current)
                self.log("Battery below min SoC → charging.")
            elif soc < self.target_soc and surplus > 0:
                self.call_service("number/set_value",
                                  entity_id="number.solax_battery_charge_max_current",
                                  value=self.battery_charge_current)
                self.log("Battery charging towards target SoC.")
            else:
                self.call_service("number/set_value",
                                  entity_id="number.solax_battery_charge_max_current",
                                  value=0)
                self.log("Battery charging paused (target SoC reached or no surplus).")

            # --- Boiler control ---
            if boiler_temp < self.boiler_temp_min and surplus >= 800:
                self.turn_on("switch.boiler_relay_1")
                if surplus >= 1600:
                    self.turn_on("switch.boiler_relay_2")
                else:
                    self.turn_off("switch.boiler_relay_2")
                self.log("Boiler heating (below min).")
            elif boiler_temp < self.boiler_temp_opt and surplus >= 800:
                self.turn_on("switch.boiler_relay_1")
                if surplus >= 1600:
                    self.turn_on("switch.boiler_relay_2")
                else:
                    self.turn_off("switch.boiler_relay_2")
                self.log("Boiler heating (towards optimal).")
            else:
                self.turn_off("switch.boiler_relay_1")
                self.turn_off("switch.boiler_relay_2")
                self.log("Boiler heating off (temperature reached).")

            # --- Grid export control ---
            if surplus > 0:
                if spot_price >= self.min_spot_price:
                    limit = min(int(surplus), 12200)
                    self.call_service("number/set_value",
                                      entity_id="number.solax_export_control_user_limit",
                                      value=limit)
                    self.log(f"Exporting {limit} W to grid (spot price OK).")
                else:
                    self.call_service("number/set_value",
                                      entity_id="number.solax_export_control_user_limit",
                                      value=0)
                    self.log("Spot price too low → no grid export.")
            else:
                self.call_service("number/set_value",
                                  entity_id="number.solax_export_control_user_limit",
                                  value=0)
                self.log("No surplus → no grid export.")

        except Exception as e:
            self.error(f"Error in optimization: {e}")
