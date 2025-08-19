# Home Energy Optimizer (AppDaemon)

This repository provides a Home Assistant **add-on** that bundles AppDaemon and a custom optimizer app for **Solax X3-Hybrid-G4**, **Solcast forecasts**, and **OTE spot prices**.

## Features
- Predictive scheduler (15-min slots)
- Ensures minimum battery SoC (≥ 80%) and boiler temperature (≥ 60 °C) by sunset
- Maximizes export at high spot prices
- Respects inverter **Self Use Mode** (no battery-to-grid arbitrage)
- Grid import guard
- Historical weekday/weekend load profile

## Installation
1. In Home Assistant → **Settings → Add-ons → Add-on Store**.  
2. Click **⋮ → Repositories** and add:  
