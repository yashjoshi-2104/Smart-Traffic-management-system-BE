# backend/routes/metrics.py
"""
Traffic metrics endpoints
"""

from fastapi import APIRouter, HTTPException
from models import MetricsResponse, TrafficState

# Will be set by main.py
dual_sim_manager = None

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/current", response_model=MetricsResponse)
async def get_current_metrics():
    """Get current traffic metrics for both simulations"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    try:
        metrics = dual_sim_manager.get_traffic_metrics()
        return MetricsResponse(**metrics)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/state", response_model=TrafficState)
async def get_current_state():
    """Get current traffic state for both simulations"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    try:
        baseline_state, rl_state = dual_sim_manager.get_detailed_states()
        
        return TrafficState(
            baseline=baseline_state,
            rl=rl_state
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get state: {str(e)}")