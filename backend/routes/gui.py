# backend/routes/gui.py
"""
Instant SUMO GUI open endpoint
Relaunches a running headless SUMO instance as sumo-gui without stopping simulation
Includes pause + resync to prevent desynchronization
"""

import subprocess
import time
import traci
from fastapi import APIRouter, HTTPException
from models import GUIOpenRequest, MessageResponse

# Injected by main.py
dual_sim_manager = None

router = APIRouter(prefix="/api/simulation", tags=["gui"])


@router.post("/gui/open", response_model=MessageResponse)
async def open_gui_window(request: GUIOpenRequest):
    """
    Instantly open a SUMO-GUI window for a running simulation.

    Flow:
      1. Pause the simulation step loop
      2. Disconnect TraCI from the target sim
      3. Relaunch as sumo-gui on the same port
      4. Reconnect TraCI
      5. Fast-forward the relaunched sim to match the other sim's time
      6. Resume the step loop
    """

    if dual_sim_manager is None:
        raise HTTPException(status_code=500, detail="Simulation manager not initialized")

    if not dual_sim_manager.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running. Start it first.")

    target = request.target
    if target not in ("baseline", "rl"):
        raise HTTPException(status_code=400, detail='target must be "baseline" or "rl"')

    sumo_ctrl   = dual_sim_manager.baseline_sumo if target == "baseline" else dual_sim_manager.rl_sumo
    port        = sumo_ctrl.port
    config_file = dual_sim_manager.config_file

    print(f"\n👁️  Opening SUMO-GUI for {target} simulation (port {port})...")

    # ── Step 1: Pause the simulation loop ─────────────────────────────────────
    dual_sim_manager.paused = True
    print(f"   ⏸  Simulation loop paused")
    time.sleep(0.3)  # let any in-progress step() finish

    # ── Step 2: Disconnect TraCI ───────────────────────────────────────────────
    try:
        sumo_ctrl.conn.close()
        print(f"   ✅ TraCI disconnected from port {port}")
    except Exception as e:
        print(f"   ⚠️  TraCI disconnect warning: {e}")

    sumo_ctrl.is_running = False
    sumo_ctrl.conn       = None
    time.sleep(1.0)  # wait for port to free

    # ── Step 3: Launch sumo-gui on same port ──────────────────────────────────
    sumo_cmd = [
    "sumo-gui",
    "-c", config_file,
    "--remote-port", str(port),
    "--start",
    "--quit-on-end",
    "--delay", "100",   # visual delay only, doesn't affect step length
    ]

    try:
        subprocess.Popen(
            sumo_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE  # Windows: lets GUI render
        )
        print(f"   ✅ sumo-gui launched on port {port}")
    except Exception as e:
        dual_sim_manager.paused = False
        raise HTTPException(status_code=500, detail=f"Failed to launch sumo-gui: {str(e)}")

    time.sleep(3.0)  # wait for sumo-gui to initialize

    # ── Step 4: Reconnect TraCI ────────────────────────────────────────────────
    try:
        sumo_ctrl.conn       = traci.connect(port)
        sumo_ctrl.is_running = True
        print(f"   ✅ TraCI reconnected on port {port}")
    except Exception as e:
        dual_sim_manager.paused = False
        raise HTTPException(
            status_code=500,
            detail=f"sumo-gui launched but TraCI reconnect failed: {str(e)}"
        )

    # ── Step 5: Resync — fast-forward relaunched sim to match the other ────────
    try:
        if target == "rl":
            dual_sim_manager.resync_rl_to_baseline()
        else:
            _resync_baseline_to_rl()
    except Exception as e:
        print(f"   ⚠️  Resync warning: {e}")

    # ── Step 6: Update GUI flag and resume loop ────────────────────────────────
    if target == "baseline":
        dual_sim_manager.gui_baseline = True
    else:
        dual_sim_manager.gui_rl = True

    dual_sim_manager.paused = False
    print(f"   ▶  Simulation loop resumed")
    print(f"   ✅ {target.upper()} simulation now running in GUI mode\n")

    return MessageResponse(
        message=f"SUMO-GUI opened for {target} simulation",
        success=True,
        data={"target": target, "port": port, "gui": True}
    )


def _resync_baseline_to_rl():
    """Fast-forward baseline to match RL time (used when baseline GUI is opened)"""
    rl_time       = dual_sim_manager.rl_sumo.get_state()["time"]
    baseline_time = dual_sim_manager.baseline_sumo.get_state()["time"]

    if baseline_time >= rl_time:
        return

    print(f"   ⏩ Fast-forwarding Baseline {baseline_time:.1f}s → {rl_time:.1f}s...")
    steps = 0
    while dual_sim_manager.baseline_sumo.get_state()["time"] < rl_time:
        dual_sim_manager.baseline_sumo.step()
        steps += 1
    print(f"   ✅ Baseline resynced in {steps} steps")


@router.get("/gui/status")
async def get_gui_status():
    """Check which simulations have GUI windows open"""
    if not dual_sim_manager or not dual_sim_manager.is_running:
        return {"baseline": False, "rl": False, "running": False}

    return {
        "baseline": dual_sim_manager.gui_baseline,
        "rl":       dual_sim_manager.gui_rl,
        "running":  True
    }