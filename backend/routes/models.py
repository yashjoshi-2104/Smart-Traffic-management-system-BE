# backend/models.py
"""
Pydantic models for request/response validation
"""

from typing import Any, Optional
from pydantic import BaseModel


# ── Simulation ────────────────────────────────────────────────────────────────

class StartSimulationRequest(BaseModel):
    config_file: Optional[str] = None


class SimulationStatus(BaseModel):
    is_running: bool
    step_count: int
    rl_mode: str
    sync_status: dict


# ── GUI ───────────────────────────────────────────────────────────────────────

class GUIEnableRequest(BaseModel):
    baseline: bool = False
    rl: bool = False


class GUIOpenRequest(BaseModel):
    target: str  # "baseline" | "rl"


# ── Shared response ───────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool
    data: Optional[Any] = None