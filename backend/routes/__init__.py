# backend/routes/__init__.py
from routes.simulation import router as simulation_router
from routes.control import router as control_router
from routes.metrics import router as metrics_router

__all__ = [
    'simulation_router',
    'control_router',
    'metrics_router'
]