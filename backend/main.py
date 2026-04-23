# backend/main.py
"""
FastAPI main application
Real-time traffic simulation API with WebSocket support
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.dual_sim_manager import DualSimManager
from services.websocket_handler import ws_manager
import routes.simulation as simulation_routes
import routes.control as control_routes
import routes.metrics as metrics_routes
import routes.gui as gui_routes
from config import API_HOST, API_PORT, WS_BROADCAST_INTERVAL
import state


class SpeedRequest(BaseModel):
    speed: float


class NetworkConfigRequest(BaseModel):
    network: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🚀 Starting Traffic Management API...")
    print("=" * 60)

    global dual_sim_manager

    dual_sim_manager = DualSimManager(
        network_name="simple_intersection",
        rl_model_path=None,
        gui_baseline=False,
        gui_rl=state.gui_preferences['rl']
    )

    simulation_routes.dual_sim_manager = dual_sim_manager
    control_routes.dual_sim_manager    = dual_sim_manager
    metrics_routes.dual_sim_manager    = dual_sim_manager
    gui_routes.dual_sim_manager        = dual_sim_manager

    print("✅ Simulation manager initialized")
    print(f"✅ API ready at http://{API_HOST}:{API_PORT}")
    print(f"✅ WebSocket ready at ws://{API_HOST}:{API_PORT}/ws")
    print(f"✅ Docs at http://{API_HOST}:{API_PORT}/docs")
    print("=" * 60 + "\n")

    yield

    print("\n🛑 Shutting down...")
    if dual_sim_manager and dual_sim_manager.is_running:
        dual_sim_manager.stop()
    print("✅ Cleanup complete\n")


app = FastAPI(
    title="Smart Traffic Management API",
    description="Real-time dual simulation — D-DQN RL agent vs Fixed-time baseline",
    version="1.0.0",
    lifespan=lifespan
)

dual_sim_manager = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_routes.router)
app.include_router(control_routes.router)
app.include_router(metrics_routes.router)
app.include_router(gui_routes.router)


@app.get("/")
async def root():
    return {
        "message": "Smart Traffic Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "simulation_running": dual_sim_manager.is_running if dual_sim_manager else False
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass

            if dual_sim_manager and dual_sim_manager.is_running:
                try:
                    baseline_state, rl_state = dual_sim_manager.get_detailed_states()
                    metrics        = dual_sim_manager.get_traffic_metrics()
                    emergency_status = dual_sim_manager.get_emergency_status()

                    tls_phases = {}
                    for tid in dual_sim_manager.all_tls_ids:
                        try:
                            tls_phases[tid] = {
                                'baseline': dual_sim_manager.baseline_sumo.get_traffic_light_phase(tid),
                                'rl':       dual_sim_manager.rl_sumo.get_traffic_light_phase(tid)
                            }
                        except Exception:
                            pass

                    await ws_manager.broadcast({
                        'type':          'state_update',
                        'timestamp':     baseline_state.get('time', 0),
                        'step':          dual_sim_manager.step_count,
                        'baseline':      {
                            'vehicle_count': baseline_state.get('vehicle_count', 0),
                            'vehicles':      baseline_state.get('vehicles', [])
                        },
                        'rl':            {
                            'vehicle_count': rl_state.get('vehicle_count', 0),
                            'vehicles':      rl_state.get('vehicles', [])
                        },
                        'metrics':       metrics,
                        'traffic_lights': tls_phases,
                        'rl_mode':       'rl',   # always RL — mode selector removed
                        'emergency':     emergency_status
                    })

                except Exception as e:
                    print(f"⚠️  Broadcast error: {e}")

            await asyncio.sleep(WS_BROADCAST_INTERVAL)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️  WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.post("/api/simulation/set_speed")
async def set_simulation_speed(request: SpeedRequest):
    speed = max(0.1, min(5.0, request.speed))
    state.simulation_speed = speed
    return {"success": True, "speed": state.simulation_speed}


@app.get("/api/simulation/speed")
async def get_simulation_speed():
    return {"speed": state.simulation_speed}


@app.post("/api/simulation/configure")
async def configure_network(request: NetworkConfigRequest):
    global dual_sim_manager

    valid_networks = ["simple_intersection", "urban_arterial", "complex_grid_3x3"]
    if request.network not in valid_networks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid network. Must be one of: {valid_networks}"
        )

    if dual_sim_manager and dual_sim_manager.is_running:
        dual_sim_manager.stop()

    try:
        dual_sim_manager = DualSimManager(
            rl_model_path=None,
            network_name=request.network,
            gui_baseline=False,
            gui_rl=state.gui_preferences['rl']
        )
        simulation_routes.dual_sim_manager = dual_sim_manager
        control_routes.dual_sim_manager    = dual_sim_manager
        metrics_routes.dual_sim_manager    = dual_sim_manager
        gui_routes.dual_sim_manager        = dual_sim_manager

        return {
            "status":  "success",
            "network": request.network,
            "message": f"Network configured to: {request.network}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure network: {str(e)}")


@app.get("/api/simulation/networks")
async def get_available_networks():
    return {
        "networks": [
            {
                "id":            "simple_intersection",
                "name":          "Simple Intersection",
                "description":   "Single 4-way intersection",
                "intersections": 1,
                "complexity":    "Simple"
            },
            {
                "id":            "urban_arterial",
                "name":          "Urban Arterial (NGSIM)",
                "description":   "3-intersection arterial calibrated from NGSIM US-101 data",
                "intersections": 5,
                "complexity":    "Urban"
            },
        ],
        "current": dual_sim_manager.network_name if dual_sim_manager else "simple_intersection"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True, log_level="info")