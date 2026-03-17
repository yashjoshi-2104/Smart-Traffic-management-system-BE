# backend/routes/control.py
"""
Traffic signal control endpoints
"""

from fastapi import APIRouter, HTTPException
from models import SetModeRequest, ManualPhaseRequest, MessageResponse

# Will be set by main.py
dual_sim_manager = None

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/set_mode", response_model=MessageResponse)
async def set_control_mode(request: SetModeRequest):
    """Set RL simulation control mode"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    try:
        dual_sim_manager.set_rl_mode(request.mode)
        
        return MessageResponse(
            message=f"Control mode set to: {request.mode}",
            success=True,
            data={"mode": request.mode}
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set mode: {str(e)}")


@router.post("/manual_phase", response_model=MessageResponse)
async def set_manual_phase(request: ManualPhaseRequest):
    """Manually set signal phase (when in manual mode)"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    try:
        dual_sim_manager.apply_manual_control(request.tls_id, request.phase)
        
        return MessageResponse(
            message=f"Phase set to {request.phase} for {request.tls_id}",
            success=True,
            data={
                "tls_id": request.tls_id,
                "phase": request.phase
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set phase: {str(e)}")


@router.get("/traffic_lights")
async def get_traffic_lights():
    """Get list of traffic lights in simulation"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    try:
        tls_ids = dual_sim_manager.baseline_controller.get_traffic_light_ids()
        
        return {
            "success": True,
            "traffic_lights": tls_ids,
            "count": len(tls_ids)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traffic lights: {str(e)}")