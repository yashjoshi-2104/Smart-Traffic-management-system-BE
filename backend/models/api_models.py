# backend/models/api_models.py
"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel
from typing import Optional, Dict, List, Any


# Request Models
class StartSimulationRequest(BaseModel):
    """Request to start simulation"""
    config_file: Optional[str] = None  # ✅ No default — network config managed by DualSimManager


class SetModeRequest(BaseModel):
    """Request to change control mode"""
    mode: str  # 'fixed', 'manual', or 'rl'


class ManualPhaseRequest(BaseModel):
    """Request to manually set signal phase"""
    tls_id: str
    phase: int


class GUIOpenRequest(BaseModel):
    """Request to instantly open SUMO-GUI for a running simulation"""
    target: str  # 'baseline' or 'rl'


# Response Models
class SimulationStatus(BaseModel):
    """Current simulation status"""
    is_running: bool
    step_count: int
    rl_mode: str
    sync_status: Dict[str, Any]


class TrafficState(BaseModel):
    """Current traffic state"""
    baseline: Dict[str, Any]
    rl: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Traffic metrics comparison"""
    baseline: Dict[str, Any]
    rl: Dict[str, Any]
    comparison: Dict[str, Any]


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool
    data: Optional[Dict[str, Any]] = None