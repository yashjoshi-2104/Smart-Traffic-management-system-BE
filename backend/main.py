# backend/main.py
"""
FastAPI main application
Real-time traffic simulation API with WebSocket support
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from services.dual_sim_manager import DualSimManager
from services.websocket_handler import ws_manager
from controllers import FixedTimeController, ManualController, RLController
import routes.simulation as simulation_routes
import routes.control as control_routes
import routes.metrics as metrics_routes
from config import API_HOST, API_PORT, CORS_ORIGINS, WS_BROADCAST_INTERVAL


# Global simulation manager
dual_sim_manager = None
simulation_task = None
baseline_controller = None
manual_controller = None
rl_controller = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("\n🚀 Starting Traffic Management API...")
    print("=" * 60)
    
    global dual_sim_manager, baseline_controller, manual_controller, rl_controller
    
    # Initialize simulation manager
    dual_sim_manager = DualSimManager()
    
    # Initialize controllers
    baseline_controller = FixedTimeController(
        tls_id="center",
        phase_durations=[30, 30, 10, 10]
    )
    manual_controller = ManualController(tls_id="center")
    rl_controller = RLController(tls_id="center")
    
    # Inject manager into route modules
    simulation_routes.dual_sim_manager = dual_sim_manager
    control_routes.dual_sim_manager = dual_sim_manager
    metrics_routes.dual_sim_manager = dual_sim_manager
    
    print("✅ Simulation manager initialized")
    print("✅ Controllers initialized")
    print(f"✅ API ready at http://{API_HOST}:{API_PORT}")
    print(f"✅ WebSocket ready at ws://{API_HOST}:{API_PORT}/ws")
    print(f"✅ Docs at http://{API_HOST}:{API_PORT}/docs")
    print("=" * 60 + "\n")
    
    yield
    
    # Shutdown
    print("\n🛑 Shutting down...")
    if dual_sim_manager and dual_sim_manager.is_running:
        dual_sim_manager.stop()
    print("✅ Cleanup complete\n")


# Create FastAPI app
app = FastAPI(
    title="Smart Traffic Management API",
    description="Real-time traffic simulation with baseline vs RL comparison",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(simulation_routes.router)
app.include_router(control_routes.router)
app.include_router(metrics_routes.router)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Smart Traffic Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "simulation_running": dual_sim_manager.is_running if dual_sim_manager else False
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time state updates
    
    Broadcasts simulation state every second when simulation is running
    """
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Wait for messages from client (for heartbeat/control)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                # Handle client messages if needed
            except asyncio.TimeoutError:
                pass
            
            # If simulation is running, broadcast state
            if dual_sim_manager and dual_sim_manager.is_running:
                try:
                    # Get current state
                    baseline_state, rl_state = dual_sim_manager.get_detailed_states()
                    
                    # Get metrics
                    metrics = dual_sim_manager.get_traffic_metrics()
                    
                    # Get traffic light states
                    tls_ids = dual_sim_manager.baseline_controller.get_traffic_light_ids()
                    tls_states = {}
                    
                    if tls_ids:
                        for tls_id in tls_ids:
                            tls_states[tls_id] = {
                                'baseline': dual_sim_manager.baseline_controller.get_traffic_light_phase(tls_id),
                                'rl': dual_sim_manager.rl_controller.get_traffic_light_phase(tls_id)
                            }
                    
                    # Broadcast update
                    await ws_manager.broadcast({
                        'type': 'state_update',
                        'timestamp': baseline_state['time'],
                        'step': dual_sim_manager.step_count,
                        'baseline': {
                            'vehicle_count': baseline_state['vehicle_count'],
                            'vehicles': baseline_state['vehicles']
                        },
                        'rl': {
                            'vehicle_count': rl_state['vehicle_count'],
                            'vehicles': rl_state['vehicles']
                        },
                        'metrics': metrics,
                        'traffic_lights': tls_states,
                        'rl_mode': dual_sim_manager.rl_mode
                    })
                
                except Exception as e:
                    print(f"⚠️  Error broadcasting state: {e}")
            
            # Sleep to control broadcast rate
            await asyncio.sleep(WS_BROADCAST_INTERVAL)
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️  WebSocket error: {e}")
        ws_manager.disconnect(websocket)


async def simulation_loop():
    """
    Background task to step simulation
    Runs when simulation is active
    """
    global dual_sim_manager, baseline_controller, manual_controller, rl_controller
    
    while dual_sim_manager and dual_sim_manager.is_running:
        try:
            # Get traffic light IDs
            tls_ids = dual_sim_manager.baseline_controller.get_traffic_light_ids()
            
            if tls_ids:
                tls_id = tls_ids[0]
                
                # Get baseline action from fixed-time controller
                baseline_state = dual_sim_manager.baseline_controller.get_state()
                baseline_action = baseline_controller.get_action(baseline_state)
                dual_sim_manager.baseline_controller.set_traffic_light_phase(tls_id, baseline_action)
                
                # Get RL action based on mode
                rl_state = dual_sim_manager.rl_controller.get_state()
                
                if dual_sim_manager.rl_mode == 'fixed':
                    # Use same fixed-time controller
                    rl_action = baseline_action
                elif dual_sim_manager.rl_mode == 'manual':
                    # Use manual controller
                    rl_action = manual_controller.get_action(rl_state)
                else:  # rl mode
                    # Use RL controller
                    rl_action = rl_controller.get_action(rl_state)
                
                dual_sim_manager.rl_controller.set_traffic_light_phase(tls_id, rl_action)
            
            # Step both simulations
            dual_sim_manager.step()
            
            # Control simulation speed
            await asyncio.sleep(0.1)  # 10 steps per second
        
        except Exception as e:
            print(f"⚠️  Simulation loop error: {e}")
            break


@app.post("/api/simulation/step")
async def manual_step():
    """Manually step simulation (for testing)"""
    if not dual_sim_manager or not dual_sim_manager.is_running:
        return {"success": False, "message": "Simulation not running"}
    
    try:
        # Step simulation (controllers will be applied by simulation_loop)
        baseline_state, rl_state = dual_sim_manager.step()
        
        return {
            "success": True,
            "step": dual_sim_manager.step_count,
            "baseline_vehicles": baseline_state['vehicle_count'],
            "rl_vehicles": rl_state['vehicle_count']
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )