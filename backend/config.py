# backend/config.py
"""
Configuration settings for the backend
"""

import os

# SUMO Configuration
DEFAULT_CONFIG_FILE = "../sumo/configs/tls_test.sumocfg"
DEFAULT_NETWORK_FILE = "../sumo/networks/single_tls_intersection.net.xml"
DEFAULT_ROUTE_FILE = "../sumo/routes/tls_test_traffic.rou.xml"

# Server Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# WebSocket Configuration
WS_BROADCAST_INTERVAL = 1.0  # Broadcast state every 1 second

# Simulation Configuration
SIMULATION_STEP_DURATION = 1.0  # 1 second per step