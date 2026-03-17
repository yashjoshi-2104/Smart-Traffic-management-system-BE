# backend/routes/simulation.py
"""
Simulation control endpoints
"""

from fastapi import APIRouter, HTTPException
from models import StartSimulationRequest, SimulationStatus, MessageResponse

# Will be set by main.py
dual_sim_manager = None

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.post("/start", response_model=MessageResponse)
async def start_simulation(request: StartSimulationRequest):
    """Start both baseline and RL simulations"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    if dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation already running")
    
    try:
        # Start simulations
        dual_sim_manager.config_file = request.config_file
        dual_sim_manager.start()
        
        return MessageResponse(
            message="Simulations started successfully",
            success=True,
            data={
                "config_file": request.config_file,
                "step_count": dual_sim_manager.step_count
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {str(e)}")


@router.post("/stop", response_model=MessageResponse)
async def stop_simulation():
    """Stop both simulations"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    try:
        dual_sim_manager.stop()
        
        return MessageResponse(
            message="Simulations stopped successfully",
            success=True,
            data={
                "final_step": dual_sim_manager.step_count
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop simulation: {str(e)}")


@router.get("/status", response_model=SimulationStatus)
async def get_status():
    """Get current simulation status"""
    
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    
    sync_status = {}
    if dual_sim_manager.is_running:
        sync_status = dual_sim_manager.get_sync_status()
    
    return SimulationStatus(
        is_running=dual_sim_manager.is_running,
        step_count=dual_sim_manager.step_count,
        rl_mode=dual_sim_manager.rl_mode,
        sync_status=sync_status
    )