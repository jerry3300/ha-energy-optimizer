import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta

class EnergyOptimizer(hass.Hass):

    def initialize(self):
        self.period = int(self.args.get("optimization_period", 300))
        self.batt_curr = int(self.args.get("battery_charge_current", 25))
        self.min_soc = int(self.args.get("min_soc", 80))
        self.opt_soc = int(self.args.get("opt_soc", 100))
        self.min_bt = int(self.args.get("min_boiler_temp", 55))
        self.opt_bt = int(self.args.get("opt_boiler_temp", 70))
        self.min_price = float(self.args.get("min_spot_price", 300))
        self.min_grid_soc = int(self.args.get("min_grid_charge_soc", 20))

        self.log("Energy Optimizer initialized with period={}s".format(self.period))
        self.run_every(self.optimize_cycle, "now", self.period)

    # --- Helpers
    def _f(self, v, d=0.0):
        try:
            return float(v)
        except:
            return d

    def _state(self, entity, d=None):
        s = self.get_state(entity)
        if s is None or s == "unknown" or s == "unavailable":
            return d
        return s

    def _number_set(self, entity, value):
        self.call_service("number/set_value", entity_id=entity, value=value)

    def _switch(self, entity, on):
        self.call_service(f"switch/turn_{'on' if on else 'off'}", entity_id=entity)

    # --- Main control loop
    def optimize_cycle(self, kwargs):
        try:
            soc = self._f(self._state("sensor.solax_battery_capacity"))
            batt_v = self._f(self._state("sensor.solax_battery_voltage_charge"), 240.0)
            boiler_t = self._f(self._state("sensor.boiler_temp"))
            pv_now = self._f(self._state("sensor.solax_pv_power_total"))
            house = self._f(self._state("sensor.solax_house_load"))
            spot = self._f(self._state("sensor.current_spot_electricity_price"))
            surplus = max(0.0, pv_now - house)

            # Boiler staged control (0/800/1600)
            if boiler_t < self.min_bt:
                # heat aggressively if we have surplus; if not, allow grid but stop at 55-60C
                if surplus >= 1600:
                    self._switch("switch.boiler_relay_1", True)
                    self._switch("switch.boiler_relay_2", True)
                elif surplus >= 800:
                    self._switch("switch.boiler_relay_1", True)
                    self._switch("switch.boiler_relay_2", False)
                else:
                    # not enough PV - allow grid only until ~55C
                    if boiler_t < 55:
                        self._switch("switch.boiler_relay_1", True)
                        self._switch("switch.boiler_relay_2", False)
                    else:
                        self._switch("switch.boiler_relay_1", False)
                        self._switch("switch.boiler_relay_2", False)
            elif boiler_t < self.opt_bt:
                if surplus >= 800 and spot < self.min_price:
                    self._switch("switch.boiler_relay_1", True)
                    self._switch("switch.boiler_relay_2", surplus >= 1600)
                else:
                    self._switch("switch.boiler_relay_1", False)
                    self._switch("switch.boiler_relay_2", False)
            else:
                self._switch("switch.boiler_relay_1", False)
                self._switch("switch.boiler_relay_2", False)

            # Battery charging current (0–25A). No grid arbitrage; keep self-consumption.
            target_current = 0
            if soc < self.opt_soc and surplus > 0:
                # I = P/V; clamp to configured max
                target_current = min(self.batt_curr, int(surplus / max(batt_v,1) * 1000))
            elif soc < self.min_grid_soc:
                # emergency: allow small grid charge to 20% to protect battery
                target_current = min(5, self.batt_curr)
            self._number_set("number.solax_battery_charge_max_current", target_current)

            # Grid export control – only when price high and we have surplus after needs
            export_limit = 0
            if soc >= self.min_soc and spot >= self.min_price and surplus > 0:
                export_limit = int(surplus)
            self._number_set("number.solax_export_control_user_limit", export_limit)

            self.log(f"SoC={soc:.1f}% PV={pv_now:.0f}W Load={house:.0f}W Surplus={surplus:.0f}W Spot={spot:.1f} "
                     f"Boiler={boiler_t:.1f}C Ibat={target_current}A Export={export_limit}W")

        except Exception as e:
            self.log(f"Optimization error: {e}", level="ERROR")
