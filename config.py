# config.py
# Default parameters for the simulation, which can be configured from the dashboard's UI.

DEFAULT_PARAMS = {
    "NUM_TRUCKS": 2,
    "DAILY_WORK_HOURS": 8.0,
    "ECOSTATION_WORK_HOURS": 8.0,  # New: Waste accumulates only during these hours.
    "AVG_SPEED_KMH": 35.0,
    "SERVICE_TIME_MIN": 25.0,
    "UNLOADING_TIME_MIN": 40.0,
    "ROAD_NETWORK_FACTOR": 1.3,
    "CAPACITY_TRIGGER_PERCENT": 0.85,
    "SIMULATION_DAYS": 75
}

# Style configuration for the dashboard, inspired by the user's example.
# You can change these colors to match your brand.
STYLE_CONFIG = {
    "theme": {
        "primaryColor": "#0047AB", # A professional blue
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F0F2F6",
        "textColor": "#1a1a1a",
        "font": "sans serif"
    }
}
