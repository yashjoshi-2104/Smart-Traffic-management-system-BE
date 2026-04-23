# backend/state.py
"""
Shared application state
Imported by both main.py and routes/* to avoid circular dependencies
"""

import shutil

# Auto-detect if sumo-gui is available
_sumo_gui_available = shutil.which('sumo-gui') is not None

# GUI preferences — RL always gets GUI if available, baseline always headless
gui_preferences = {
    'baseline': False,
    'rl': _sumo_gui_available   # Auto-launch GUI for RL if sumo-gui exists
}

# Simulation speed multiplier
simulation_speed = 1.0