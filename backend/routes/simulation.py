# backend/routes/simulation.py
"""
Simulation control endpoints
"""
import asyncio
from fastapi import APIRouter, HTTPException
from models import StartSimulationRequest, SimulationStatus, MessageResponse

# ✅ Import shared state — avoids circular import with main.py
import state

# Injected by main.py at startup
dual_sim_manager = None

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


async def _simulation_loop():
    """
    Steps both SUMO instances continuously while running.
    Respects state.simulation_speed multiplier set via /api/simulation/set_speed
    """
    print("▶ Simulation loop started")
    while dual_sim_manager and dual_sim_manager.is_running:
        try:
            dual_sim_manager.step()
        except Exception as e:
            print(f"⚠️  Step error: {e}")
            break

        # ✅ Respect speed multiplier from shared state
        # base 0.1s delay = 10 steps/sec at 1.0x speed
        delay = 0.1 / state.simulation_speed
        await asyncio.sleep(delay)

    print("■ Simulation loop stopped")


@router.post("/start", response_model=MessageResponse)
async def start_simulation(request: StartSimulationRequest):
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    if dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation already running")

    try:
        # Auto-launch: baseline always headless, RL gets GUI if sumo-gui available
        dual_sim_manager.gui_baseline = False
        dual_sim_manager.gui_rl = state.gui_preferences['rl']

        print(f"👁️  GUI state at start:")
        print(f"   • Baseline: headless")
        print(f"   • RL:       {'GUI (auto)' if dual_sim_manager.gui_rl else 'headless (sumo-gui not found)'}")

        # ✅ Do NOT override config_file here — already set correctly
        # by configure_network via NETWORK_CONFIGS in dual_sim_manager.
        # Overriding would reset complex_grid back to simple_intersection.

        dual_sim_manager.start()

        # Start the step loop as a background task
        asyncio.create_task(_simulation_loop())

        return MessageResponse(
            message="Simulations started successfully",
            success=True,
            data={
                "config_file": dual_sim_manager.config_file,
                "step_count": dual_sim_manager.step_count,
                "gui_baseline": dual_sim_manager.gui_baseline,
                "gui_rl": dual_sim_manager.gui_rl
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {str(e)}")


@router.post("/stop", response_model=MessageResponse)
async def stop_simulation():
    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")
    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")

    try:
        dual_sim_manager.stop()
        return MessageResponse(
            message="Simulations stopped successfully",
            success=True,
            data={"final_step": dual_sim_manager.step_count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop simulation: {str(e)}")


@router.get("/status", response_model=SimulationStatus)
async def get_status():
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