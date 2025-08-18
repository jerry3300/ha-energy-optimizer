# HA Energy Optimizer (AppDaemon add-on)

Optimizes Solax hybrid inverter battery charging, boiler heating, and grid export using Solcast PV forecast, historic house load, and OTE spot prices — all inside Home Assistant.

## Highlights
- Charge battery to min/opt SoC before sunset
- Boiler heat control in 0/800/1600 W steps
- Export to grid only when spot price is high
- 7‑day history–based hourly load profile
- Planned vs. Actual export tracking with ApexCharts
- Built-in UI config for key parameters
- Designed for: Solax X3-Hybrid-G4, Home Assistant, Solcast, OTE CZ prices

## Dependencies
- Home Assistant (Supervisor)
- Solax integration/add-on (entities: `sensor.solax_*`, `number.solax_*`, `switch.boiler_*`)
- Solcast add-on (`sensor.solcast_*`)
- OTE CZ spot price integration (`sensor.current_spot_electricity_price`)
- ApexCharts card in Lovelace

## Install
1. Add this repo as an **Add-on Repository** in Home Assistant.
2. Install **Energy Optimizer** add-on.
3. Start the add-on (it runs AppDaemon internally).
4. Import sensors and dashboards from `/config/energy_optimizer` (created on first run).

---
