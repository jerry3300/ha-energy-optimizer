import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime, timedelta
import json, pytz

PRAGUE = pytz.timezone("Europe/Prague")

def _parse_iso(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(PRAGUE).replace(tzinfo=None)
    except Exception:
        return None

class EnergyOptimizer(hass.Hass):

    def initialize(self):
        self.addon_opts = self._load_addon_options()
        self.args = {**self.addon_opts, **self.args}
        self.log("Energy Optimizer initializing")

        self.run_daily(self.generate_plan, datetime.strptime("00:10:00","%H:%M:%S").time())
        for e in [self.entities()["solcast_today"], self.entities()["solcast_tomorrow"], self.entities()["spot_price"]]:
            self.listen_state(self.generate_plan, e)
        self.run_every(self.runtime_tick, self.datetime() + timedelta(seconds=5), 5*60)

        self.plan = {}
        self.generate_plan({})

    def _load_addon_options(self):
        try:
            with open("/data/options.json","r") as f:
                return json.load(f)
        except Exception:
            return {}

    def entities(self):
        return self.args.get("entities", {})

    def f(self, entity, default=0.0):
        try:
            return float(self.get_state(entity) or default)
        except Exception:
            return float(default)

    # -- Data ingest --
    def solcast_hourly_kwh(self):
        attrs = None
        for e in [self.entities()["solcast_today"], self.entities()["solcast_tomorrow"]]:
            a = self.get_state(e, attribute="detailedForecast")
            if a:
                attrs = a
                break
        buckets = {}
        if attrs:
            for row in attrs:
                ts = _parse_iso(row.get("period_start"))
                if not ts: continue
                hour = ts.replace(minute=0, second=0, microsecond=0)
                val = float(row.get("pv_estimate", 0.0))
                buckets[hour] = buckets.get(hour, 0.0) + val
        return buckets

    def spot_price_hourly(self):
        attrs = self.get_state(self.entities()["spot_price"], attribute="all")
        buckets = {}
        if attrs and isinstance(attrs, dict) and "attributes" in attrs:
            for k, v in attrs["attributes"].items():
                ts = _parse_iso(str(k))
                if ts:
                    hour = ts.replace(minute=0,second=0,microsecond=0)
                    try:
                        buckets[hour] = float(v)
                    except:
                        pass
        return buckets

    # -- Planning --
    def generate_plan(self, kwargs):
        now = datetime.now()
        slot_min = int(self.args.get("slot_minutes", 15))
        ents = self.entities()

        sunset_iso = self.get_state(ents["sun"], attribute="next_setting")
        sunset = _parse_iso(sunset_iso) or now.replace(hour=20, minute=0, second=0, microsecond=0)

        min_soc = float(self.args.get("min_soc", 80))
        opt_soc = float(self.args.get("opt_soc", 100))
        min_boiler = float(self.args.get("min_boiler_temp", 55))
        opt_boiler = float(self.args.get("opt_boiler_temp", 70))
        price_min = float(self.args.get("min_export_price", 300))

        cap_kwh = float(self.args.get("battery_capacity_kwh", 12))
        liters = float(self.args.get("boiler_liters", 120))
        kwh_per_c = liters*1.163/1000.0

        soc = self.f(ents["battery_soc"], 50)
        batt_need_min = max(0.0, (min_soc - soc)/100.0*cap_kwh)
        batt_need_opt = max(0.0, (opt_soc - soc)/100.0*cap_kwh)

        t_now = self.f(ents["boiler_temp"], 50)
        boil_need_min = max(0.0, (min_boiler - t_now)*kwh_per_c)
        boil_need_opt = max(0.0, (opt_boiler - t_now)*kwh_per_c)

        pv_hourly = self.solcast_hourly_kwh()
        price_hourly = self.spot_price_hourly()

        # Build slots
        slots = []
        t = now.replace(second=0, microsecond=0)
        if t.minute % slot_min != 0:
            t += timedelta(minutes=(slot_min - (t.minute % slot_min)))
        while t < sunset:
            hour = t.replace(minute=0, second=0, microsecond=0)
            price = price_hourly.get(hour, 0.0)
            pv_kwh_slot = pv_hourly.get(hour, 0.0) * (slot_min/60.0)

            action = {"at": t.isoformat(timespec="minutes")}
            if soc < 20.0:
                action.update({"export_limit": 0, "batt_a": int(self.args.get("battery_charge_current", 25)/2), "boiler": 0})
            else:
                if price >= price_min:
                    action.update({"export_limit": 12200, "batt_a": 0, "boiler": 0})
                else:
                    action["export_limit"] = 0
                    if batt_need_min > 0:
                        action["batt_a"] = int(self.args.get("battery_charge_current", 25))
                        batt_need_min -= pv_kwh_slot
                    elif boil_need_min > 0:
                        action["boiler"] = 800 if pv_kwh_slot >= 0.8 else 0
                        boil_need_min -= pv_kwh_slot
                    else:
                        action.update({"batt_a": 0, "boiler": 0})
            slots.append(action)
            t += timedelta(minutes=slot_min)

        self.plan = {"generated": now.isoformat(timespec="seconds"), "slots": slots}
        self.log(f"Plan generated: {len(slots)} slots")

    # -- Runtime enforcement --
    def runtime_tick(self, kwargs):
        if not self.plan: return
        now = datetime.now().replace(second=0, microsecond=0)
        active = None
        for s in self.plan["slots"]:
            ts = _parse_iso(s["at"])
            if ts and ts <= now:
                active = s
            if ts and ts > now:
                break
        if not active: return

        ents = self.entities()
        import_w = self.f(ents["grid_import"], 0)*1000.0
        limit_w = float(active.get("max_grid_import_w", self.args.get("max_grid_import_w", 100)))
        boiler = int(active.get("boiler", 0) or 0)
        if import_w > limit_w:
            boiler = 0
            batt_a = 0
            export = 0
        else:
            batt_a = int(active.get("batt_a", 0) or 0)
            export = int(active.get("export_limit", 0) or 0)

        self.call_service("number/set_value", entity_id=ents["export_limit"], value=export)
        self.call_service("number/set_value", entity_id=ents["batt_charge_limit"], value=batt_a)

        if boiler >= 1600:
            self.call_service("switch/turn_on", entity_id=ents["boiler_relay_1"])
            self.call_service("switch/turn_on", entity_id=ents["boiler_relay_2"])
        elif boiler >= 800:
            self.call_service("switch/turn_on", entity_id=ents["boiler_relay_1"])
            self.call_service("switch/turn_off", entity_id=ents["boiler_relay_2"])
        else:
            self.call_service("switch/turn_off", entity_id=ents["boiler_relay_1"])
            self.call_service("switch/turn_off", entity_id=ents["boiler_relay_2"])

        self.log(f"Applied slot at {now}: exp={export}W batt={batt_a}A boiler={boiler}W")
