# backend/services/dual_sim_manager.py
"""
DualSimManager - Orchestrates two parallel SUMO simulations
One baseline (fixed-time control), one with RL/manual control

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMERGENCY VEHICLE HANDLING — IMPLEMENTATION NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Problem identified:
  Urban arterial network has internal gateway nodes between
  intersections — SUMO generates intermediate junction edges
  such as A1B1.230.00 and C1B1.230.00. These gateway junctions
  operate as priority junctions with their own internal signal
  logic that cannot be overridden via TraCI.

  Emergency vehicles approaching B1 from A1 or C1 would enter
  the gateway edge and stop permanently because:
    1. A1B1 lane 0 connects to A1B1.230.00 lane 0 (OK)
    2. A1B1.230.00 lane 0 connects to B1C1 lane 0 (OK in XML)
    3. BUT the gateway junction blocks the vehicle when
       B1's controlled phase does not align at that exact step

  The vehicle reports speed=0, speedMode=0000000 (our override
  applied), but SUMO's junction model holds it regardless because
  the gateway is a priority junction — not a TLS junction.
  TraCI setSpeed cannot override priority junction blocking.

  Additionally vehicles spawning on A0A1 (one edge before A1)
  were not being detected by the EW substring matching since
  A0A1 does not contain "A1B1" or "C1B1". Same applies to
  C2C1 for the eastbound direction.

  Phase mapping must be network-aware:
    Simple intersection has 4 phases (0-3):
      NS green = phase 0, EW green = phase 2
    Urban arterial B1 has 8 phases (0-7):
      NS green = phase 0, EW green = phase 4
  Sending phase 4 to simple intersection causes a fatal SUMO
  error: "phase index 4 not in allowed range [0,3]".

Solution implemented:
  1. Network-aware phase mapping — each network has its own
     direction→phase lookup so phase indices are always valid.

  2. Extended direction detection to include A0A1 and C2C1
     as EW approach edges using substring matching.

  3. When an emergency vehicle is detected with speed < 0.5 m/s
     on a gateway approach edge, the system uses TraCI moveTo()
     to teleport the vehicle directly onto the correct outgoing
     edge past the gateway, at position 20m from edge start.

  Teleport targets (urban arterial only):
    A1B1 / A1B1.230.00  →  teleport to B1C1 lane 0 pos 20m
    C1B1 / C1B1.230.00  →  teleport to B1A1 lane 0 pos 20m
    A0A1                →  teleport to A1B1 lane 0 pos 20m
    C2C1                →  teleport to C1B1 lane 0 pos 20m

  After teleport, normal setSpeedMode + setSpeed resumes and
  the vehicle continues its route naturally from there.

Academic documentation:
  The gateway node limitation is a known constraint of SUMO's
  junction model where internal priority junctions between
  intersections cannot have their signal logic overridden via
  TraCI. The teleport solution provides a practical workaround
  that preserves emergency vehicle priority behavior while
  avoiding network redesign. This approach is documented as
  an engineering tradeoff — the vehicle's physical traversal
  of the gateway edge is skipped, but its end-to-end journey
  time and network clearing behavior remain realistic.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from services.sumo_controller import SumoController
from controllers.fixed_time import FixedTimeController
from controllers.manual import ManualController


# ── Network configuration map ─────────────────────────────────────────────────
NETWORK_CONFIGS = {
    "simple_intersection": {
        "config_file": "../sumo/configs/tls_test.sumocfg",
        "tls_id": "center",
        "all_tls_ids": ["center"],
        "edges": {
            "north": "north_in",
            "south": "south_in",
            "east":  "east_in",
            "west":  "west_in",
        },
        "lanes": {
            "north": "north_in_0",
            "south": "south_in_0",
            "east":  "east_in_0",
            "west":  "west_in_0",
        },
    },
    "complex_grid_3x3": {
        "config_file": "../sumo/configs/complex_grid_3x3.sumocfg",
        "tls_id": "B1",
        "all_tls_ids": ["A1", "B0", "B1", "B2", "C1"],
        "edges": {
            "north": "B2B1",
            "south": "A1B1",
            "east":  "C1B1",
            "west":  "B0B1",
        },
        "lanes": {
            "north": "B2B1_0",
            "south": "A1B1_0",
            "east":  "C1B1_0",
            "west":  "B0B1_0",
        },
    },
    "urban_arterial": {
        "config_file": "../sumo/configs/urban_arterial.sumocfg",
        "tls_id": "B1",
        "all_tls_ids": ["A1", "B0", "B1", "B2", "C1"],
        "edges": {
            "north": "B2B1",
            "south": "A1B1",
            "east":  "C1B1",
            "west":  "B0B1",
        },
        "lanes": {
            "north": "B2B1_0",
            "south": "A1B1_0",
            "east":  "C1B1_0",
            "west":  "B0B1_0",
        },
    },
}

# ── B1 urban arterial full 8-phase cycle ──────────────────────────────────────
B1_URBAN_CYCLE = [
    (0, 33), (1, 3),
    (2, 6),  (3, 3),
    (4, 33), (5, 3),
    (6, 6),  (7, 3),
]

# Agent actions (0-3) → actual SUMO green phase indices for B1
B1_PHASE_MAP = {0: 0, 1: 2, 2: 4, 3: 6}

# ── Network-aware emergency direction → phase mapping ─────────────────────────
# Simple intersection: 4 phases total (0-3)
#   phase 0 = NS green, phase 2 = EW green
# Urban arterial B1: 8 phases total (0-7)
#   phase 0 = NS left-turn green, phase 4 = EW left-turn green
# CRITICAL: Never send a phase index outside the network's phase count
EMERGENCY_DIRECTION_PHASE = {
    "simple_intersection": {"NS": 0, "EW": 2},
    "urban_arterial":      {"NS": 0, "EW": 4},
    "complex_grid_3x3":    {"NS": 0, "EW": 2},  # fallback — same as simple
}

# Gateway teleport map (urban arterial only):
# When emergency vehicle stuck (speed<0.5) on these edges → teleport forward
# Format: substring_to_match → (target_edge, target_lane, target_pos_m)
GATEWAY_TELEPORT_MAP = {
    "A1B1": ("B1C1", 0, 20.0),   # W→E main approach → past B1 onto B1C1
    "C1B1": ("B1A1", 0, 20.0),   # E→W main approach → past B1 onto B1A1
    "A0A1": ("A1B1", 0, 20.0),   # W→E outer edge → move onto A1B1
    "C2C1": ("C1B1", 0, 20.0),   # E→W outer edge → move onto C1B1
}


def _detect_emergency_direction(road: str):
    """
    Detect approach direction using substring matching.
    Handles main edges, gateway edges (A1B1.230.00), and
    outer approach edges (A0A1, C2C1).
    Returns "NS", "EW", or None if not a recognized approach edge.
    """
    if "A1B1" in road or "C1B1" in road or "A0A1" in road or "C2C1" in road:
        return "EW"
    elif "B2B1" in road or "B0B1" in road:
        return "NS"
    elif "north_in" in road or "south_in" in road:
        return "NS"
    elif "east_in" in road or "west_in" in road:
        return "EW"
    return None


class DualSimManager:
    """
    Manages two parallel SUMO simulations for real-time comparison.

    Emergency vehicle priority flow (per step):
      1. Scan all vehicles for type == "emergency"
      2. Keep vehicle moving (setSpeedMode=0, setSpeed=12)
      3. If vehicle stuck at gateway (speed<0.5) → teleport past it
         (urban arterial only — simple intersection has no gateways)
      4. Detect approach direction via substring road ID matching
      5. Look up correct phase for THIS network (not hardcoded)
      6. Force phase BEFORE sim step — overrides all controllers
      7. Normal controller resumes when no emergency detected
    """

    def __init__(
        self,
        config_file=None,
        net_file=None,
        route_file=None,
        tls_id=None,
        rl_model_path=None,
        network_name="simple_intersection",
        gui_baseline=False,
        gui_rl=False,
    ):
        net_cfg = NETWORK_CONFIGS.get(network_name, NETWORK_CONFIGS["simple_intersection"])

        self.network_name = network_name
        self.config_file  = config_file or net_cfg["config_file"]
        self.tls_id       = tls_id      or net_cfg["tls_id"]
        self.all_tls_ids  = net_cfg.get("all_tls_ids", [self.tls_id])
        self.edges        = net_cfg.get("edges", {})
        self.lanes        = net_cfg.get("lanes", {})

        self.net_file     = net_file
        self.route_file   = route_file
        self.gui_baseline = gui_baseline
        self.gui_rl       = gui_rl

        self.baseline_sumo = None
        self.rl_sumo       = None

        self.baseline_controller    = None
        self.rl_fixed_controller    = None
        self.rl_manual_controller   = None
        self.rl_agent_controller    = None

        self.is_running        = False
        self.step_count        = 0
        self.rl_mode           = "fixed"
        self.rl_model_path     = rl_model_path
        self.has_trained_model = False

        self.neighbor_phase_steps = {}
        self.neighbor_phases      = {}
        self._neighbor_logics     = {}

        # Emergency override state — tracked independently per sim
        self._baseline_emergency_active = False
        self._baseline_forced_phase     = None
        self._rl_emergency_active       = False
        self._rl_forced_phase           = None

        # Track teleported vehicles to avoid repeated teleports
        self._baseline_teleported = set()
        self._rl_teleported       = set()

        self.paused = False

    # ── Start ─────────────────────────────────────────────────────────────────
    def start(self):
        if self.is_running:
            raise Exception("Simulations already running")

        print("\n🚀 Starting Dual Simulation Manager...")
        print(f"   Network : {self.network_name}")
        print(f"   TLS ID  : {self.tls_id}")
        print(f"   Config  : {self.config_file}")
        print("=" * 60)

        self.baseline_sumo = SumoController(
            config_file=self.config_file,
            port=8813,
            gui=self.gui_baseline
        ) if self.config_file else SumoController(
            net_file=self.net_file,
            route_file=self.route_file,
            port=8813,
            gui=self.gui_baseline
        )

        self.rl_sumo = SumoController(
            config_file=self.config_file,
            port=8814,
            gui=self.gui_rl
        ) if self.config_file else SumoController(
            net_file=self.net_file,
            route_file=self.route_file,
            port=8814,
            gui=self.gui_rl
        )

        print(f"\n📌 Starting baseline simulation ({'GUI' if self.gui_baseline else 'headless'})...")
        self.baseline_sumo.start()

        print(f"\n📌 Starting RL simulation ({'GUI' if self.gui_rl else 'headless'})...")
        self.rl_sumo.start()

        self.baseline_sumo.set_manual_control(self.tls_id)
        self.rl_sumo.set_manual_control(self.tls_id)

        for tid in self.all_tls_ids:
            if tid != self.tls_id:
                self.neighbor_phase_steps[tid] = 0
                self.neighbor_phases[tid]      = 0
                try:
                    logics = self.baseline_sumo.conn.trafficlight.getAllProgramLogics(tid)
                    self._neighbor_logics[tid] = [
                        int(ph.duration) for ph in logics[0].phases
                    ]
                    print(f"  🔄 Neighbor '{tid}': {len(self._neighbor_logics[tid])} phases "
                          f"— durations {self._neighbor_logics[tid]}")
                except Exception as e:
                    self._neighbor_logics[tid] = [38, 3, 6, 3, 37, 3]
                    print(f"  ⚠️  Neighbor '{tid}': fallback durations. ({e})")

        print("\n🎮 Initializing controllers...")

        if self.network_name == "urban_arterial":
            self.baseline_controller = FixedTimeController(
                self.tls_id, cycle=B1_URBAN_CYCLE
            )
            self.rl_fixed_controller = FixedTimeController(
                self.tls_id, cycle=B1_URBAN_CYCLE
            )
            print("  ✅ Baseline: FixedTimeController (8-phase B1 cycle)")
        else:
            self.baseline_controller = FixedTimeController(self.tls_id)
            self.rl_fixed_controller = FixedTimeController(self.tls_id)
            print("  ✅ Baseline: FixedTimeController (4-phase default cycle)")

        self.rl_manual_controller = ManualController(self.tls_id)

        try:
            from ml.ddqn_controller import DDQNController

            if self.network_name == "simple_intersection":
                model_path = "ml/ddqn_simple.pth"
                phase_map  = None
            elif self.network_name == "urban_arterial":
                model_path = "ml/ddqn_urban.pth"
                phase_map  = B1_PHASE_MAP
            else:
                model_path = self.rl_model_path
                phase_map  = None

            print(f"  📂 Loading model: {model_path} for {self.network_name}")

            self.rl_agent_controller = DDQNController(
                sumo_controller=self.rl_sumo,
                model_path=model_path,
                tls_id=self.tls_id,
                edges=self.edges,
                lanes=self.lanes,
                phase_map=phase_map,
            )
            self.has_trained_model = True
            print("  ✅ RL: DDQN Controller loaded")
        except Exception as e:
            print(f"  ⚠️  No trained model — using fixed fallback. Error: {e}")
            self.rl_agent_controller = None
            self.has_trained_model   = False

        print(f"  ✅ RL: Controllers ready (mode: {self.rl_mode})")

        self.is_running           = True
        self.step_count           = 0
        self.paused               = False
        self._baseline_teleported = set()
        self._rl_teleported       = set()
        self._baseline_emergency_active = False
        self._baseline_forced_phase     = None
        self._rl_emergency_active       = False
        self._rl_forced_phase           = None

        print("\n✅ Both simulations started successfully!")
        print("=" * 60)

    # ── Emergency detection + gateway teleport ────────────────────────────────
    def _check_emergency(self, sumo, teleported_set):
        """
        Per-step emergency vehicle handling:

        1. Scan all vehicles for type == "emergency"
        2. Apply speed override (setSpeedMode=0, setSpeed=12)
        3. Gateway teleport (urban_arterial only):
           If vehicle stuck (speed<0.5) on gateway approach edge
           and not already teleported → moveTo() outgoing edge
        4. Detect direction via substring matching on road ID
        5. Look up forced phase from EMERGENCY_DIRECTION_PHASE
           using self.network_name as key — prevents sending
           invalid phase indices to wrong network type
        6. Return (emergency_active, forced_phase)
        """
        emergency_active = False
        forced_phase     = None

        try:
            conn = sumo.conn
            vids = conn.vehicle.getIDList()

            # Clean up teleported set — remove vehicles no longer in sim
            teleported_set.intersection_update(set(vids))

            for v in vids:
                try:
                    if conn.vehicle.getTypeID(v) != "emergency":
                        continue

                    road  = conn.vehicle.getRoadID(v)
                    speed = conn.vehicle.getSpeed(v)

                    # ── Keep vehicle moving at stable speed ───────────────────
                    conn.vehicle.setSpeedMode(v, 0)
                    conn.vehicle.setSpeed(v, 12.0)

                    # ── Gateway teleport (urban arterial only) ────────────────
                    # Simple intersection has no gateway nodes so teleport
                    # is skipped entirely for that network.
                    if self.network_name == "urban_arterial" and \
                            speed < 0.5 and v not in teleported_set:
                        for gateway_key, (target_edge, target_lane, target_pos) \
                                in GATEWAY_TELEPORT_MAP.items():
                            if gateway_key in road:
                                try:
                                    lane_id = f"{target_edge}_{target_lane}"
                                    conn.vehicle.moveTo(v, lane_id, target_pos)
                                    teleported_set.add(v)
                                    print(
                                        f"🚑 GATEWAY TELEPORT | {v} | "
                                        f"stuck on '{road}' → "
                                        f"moved to '{target_edge}' "
                                        f"lane {target_lane} pos {target_pos}m"
                                    )
                                except Exception as te:
                                    print(f"⚠️  Teleport failed for {v}: {te}")
                                break

                    # ── Direction detection ───────────────────────────────────
                    direction = _detect_emergency_direction(road)
                    if direction is not None:
                        emergency_active = True

                        # Network-aware phase lookup — prevents invalid phase
                        # index errors (e.g. phase 4 sent to simple intersection
                        # which only has phases 0-3)
                        network_phases = EMERGENCY_DIRECTION_PHASE.get(
                            self.network_name,
                            {"NS": 0, "EW": 2}  # safe fallback
                        )
                        forced_phase = network_phases.get(direction)
                        break

                except Exception:
                    continue

        except Exception:
            pass

        return emergency_active, forced_phase

    # ── Neighbor TLS driver ───────────────────────────────────────────────────
    def _step_neighbor_tls(self, sumo):
        """
        Drive all non-primary intersections through their full phase cycle.
        Uses actual phase durations cached from SUMO at startup.
        Ensures E/W phases are reached — neighbors have 6 phases not 4.
        """
        for tid in self.all_tls_ids:
            if tid == self.tls_id:
                continue

            steps      = self.neighbor_phase_steps.get(tid, 0)
            phase      = self.neighbor_phases.get(tid, 0)
            durations  = self._neighbor_logics.get(tid, [38, 3, 6, 3, 37, 3])
            num_phases = len(durations)
            duration   = durations[phase] if phase < num_phases else 33

            if steps >= duration:
                phase = (phase + 1) % num_phases
                self.neighbor_phases[tid]      = phase
                self.neighbor_phase_steps[tid] = 0
            else:
                self.neighbor_phase_steps[tid] = steps + 1

            try:
                sumo.conn.trafficlight.setPhase(tid, phase)
            except Exception:
                pass

    # ── Step ──────────────────────────────────────────────────────────────────
    def step(self):
        if not self.is_running:
            raise Exception("Simulations not running. Call start() first.")

        if self.paused:
            return self.baseline_sumo.get_state(), self.rl_sumo.get_state()

        # ── STEP 1: Emergency check BEFORE any phase is set ───────────────────
        self._baseline_emergency_active, self._baseline_forced_phase = \
            self._check_emergency(self.baseline_sumo, self._baseline_teleported)

        self._rl_emergency_active, self._rl_forced_phase = \
            self._check_emergency(self.rl_sumo, self._rl_teleported)

        # ── STEP 2: Baseline phase — emergency overrides fixed-time ───────────
        if self._baseline_emergency_active and self._baseline_forced_phase is not None:
            baseline_phase = self._baseline_forced_phase
        else:
            baseline_phase = self.baseline_controller.get_action()

        # ── STEP 3: RL phase — emergency overrides all controller modes ───────
        if self._rl_emergency_active and self._rl_forced_phase is not None:
            rl_phase = self._rl_forced_phase
        else:
            if self.rl_mode == "fixed":
                rl_phase = self.rl_fixed_controller.get_action()
            elif self.rl_mode == "manual":
                rl_phase = self.rl_manual_controller.get_action()
            elif self.rl_mode == "rl":
                if self.has_trained_model and self.rl_agent_controller:
                    rl_phase = self.rl_agent_controller.get_action()
                else:
                    rl_phase = self.rl_fixed_controller.get_action()
            else:
                rl_phase = 0

        # ── STEP 4: Apply phases to primary TLS on both sims ──────────────────
        self.baseline_sumo.set_traffic_light_phase(self.tls_id, baseline_phase)
        self.rl_sumo.set_traffic_light_phase(self.tls_id, rl_phase)

        # ── STEP 5: Drive neighbor intersections through all their phases ──────
        self._step_neighbor_tls(self.baseline_sumo)
        self._step_neighbor_tls(self.rl_sumo)

        # ── STEP 6: Advance both simulations one step ─────────────────────────
        self.baseline_sumo.step()
        self.rl_sumo.step()

        # ── STEP 7: Sync check ────────────────────────────────────────────────
        baseline_time = self.baseline_sumo.get_state()["time"]
        rl_time       = self.rl_sumo.get_state()["time"]
        time_diff     = abs(baseline_time - rl_time)

        if time_diff > 0.1:
            print(f"⚠️  WARNING: Simulations desynchronized! Δ={time_diff:.3f}s")
            if baseline_time < rl_time:
                while self.baseline_sumo.get_state()["time"] < rl_time:
                    self.baseline_sumo.step()
            else:
                while self.rl_sumo.get_state()["time"] < baseline_time:
                    self.rl_sumo.step()

        self.step_count += 1
        return self.baseline_sumo.get_state(), self.rl_sumo.get_state()

    # ── Resync after GUI relaunch ─────────────────────────────────────────────
    def resync_rl_to_baseline(self):
        baseline_time = self.baseline_sumo.get_state()["time"]
        rl_time       = self.rl_sumo.get_state()["time"]
        if rl_time >= baseline_time:
            return
        print(f"   ⏩ Fast-forwarding RL from {rl_time:.1f}s → {baseline_time:.1f}s...")
        steps = 0
        while self.rl_sumo.get_state()["time"] < baseline_time:
            self.rl_sumo.step()
            steps += 1
        print(f"   ✅ RL resynced in {steps} steps")

    # ── Detailed states ───────────────────────────────────────────────────────
    def get_detailed_states(self):
        if not self.is_running:
            raise Exception("Simulations not running")

        baseline_state = self.baseline_sumo.get_detailed_state()
        rl_state       = self.rl_sumo.get_detailed_state()

        baseline_state['emergency'] = {
            'has_emergency': self.baseline_sumo.has_emergency_vehicles(),
            'by_direction':  self.baseline_sumo.get_emergency_vehicles_by_direction(),
            'vehicles':      self.baseline_sumo.get_emergency_vehicles()
        }
        rl_state['emergency'] = {
            'has_emergency': self.rl_sumo.has_emergency_vehicles(),
            'by_direction':  self.rl_sumo.get_emergency_vehicles_by_direction(),
            'vehicles':      self.rl_sumo.get_emergency_vehicles()
        }

        return baseline_state, rl_state

    # ── Metrics ───────────────────────────────────────────────────────────────
    def get_traffic_metrics(self):
        if not self.is_running:
            raise Exception("Simulations not running")

        baseline_state   = self.baseline_sumo.get_detailed_state()
        rl_state         = self.rl_sumo.get_detailed_state()
        baseline_metrics = self._compute_metrics(baseline_state)
        rl_metrics       = self._compute_metrics(rl_state)

        return {
            "baseline": baseline_metrics,
            "rl":       rl_metrics,
            "comparison": {
                "waiting_time_improvement": (
                    (baseline_metrics["avg_waiting_time"] - rl_metrics["avg_waiting_time"])
                    / baseline_metrics["avg_waiting_time"] * 100
                    if baseline_metrics["avg_waiting_time"] > 0 else 0
                ),
                "speed_improvement": (
                    (rl_metrics["avg_speed"] - baseline_metrics["avg_speed"])
                    / baseline_metrics["avg_speed"] * 100
                    if baseline_metrics["avg_speed"] > 0 else 0
                ),
            },
        }

    def _compute_metrics(self, state):
        vehicles = state["vehicles"]
        if not vehicles:
            return {
                "vehicle_count": 0, "avg_speed": 0,
                "avg_waiting_time": 0, "total_waiting_time": 0,
                "stopped_vehicles": 0
            }

        total_speed, total_wait, stopped = 0, 0, 0
        for vdata in vehicles.values():
            total_speed += vdata["speed"]
            total_wait  += vdata["waiting_time"]
            if vdata["speed"] < 0.1:
                stopped += 1

        n = len(vehicles)
        return {
            "vehicle_count":      n,
            "avg_speed":          total_speed / n,
            "avg_waiting_time":   total_wait  / n,
            "total_waiting_time": total_wait,
            "stopped_vehicles":   stopped,
            "stopped_percentage": stopped / n * 100,
        }

    # ── Control ───────────────────────────────────────────────────────────────
    def set_rl_mode(self, mode):
        valid = ["fixed", "manual", "rl"]
        if mode not in valid:
            raise ValueError(f"Invalid mode. Must be one of: {valid}")
        self.rl_mode = mode
        print(f"✅ RL simulation mode set to: {mode}")

    def apply_manual_control(self, phase):
        if not self.is_running:
            raise Exception("Simulations not running")
        self.rl_manual_controller.set_phase(phase)

    # ── Emergency status ──────────────────────────────────────────────────────
    def get_emergency_status(self):
        if not self.is_running:
            return {
                "baseline": {"has_emergency": False, "count": 0, "by_direction": {}},
                "rl":       {"has_emergency": False, "count": 0, "by_direction": {}},
            }

        b = self.baseline_sumo.get_emergency_vehicles_by_direction()
        r = self.rl_sumo.get_emergency_vehicles_by_direction()

        return {
            "baseline": {
                "has_emergency":   sum(b.values()) > 0,
                "count":           sum(b.values()),
                "by_direction":    b,
                "override_active": self._baseline_emergency_active,
                "forced_phase":    self._baseline_forced_phase,
            },
            "rl": {
                "has_emergency":   sum(r.values()) > 0,
                "count":           sum(r.values()),
                "by_direction":    r,
                "override_active": self._rl_emergency_active,
                "forced_phase":    self._rl_forced_phase,
            },
        }

    # ── Sync status ───────────────────────────────────────────────────────────
    def get_sync_status(self):
        if not self.is_running:
            return {"synchronized": False, "reason": "Not running"}

        bt   = self.baseline_sumo.get_state()["time"]
        rt   = self.rl_sumo.get_state()["time"]
        diff = abs(bt - rt)

        return {
            "synchronized":    diff < 0.1,
            "baseline_time":   bt,
            "rl_time":         rt,
            "time_difference": diff,
        }

    # ── Stop ──────────────────────────────────────────────────────────────────
    def stop(self):
        if not self.is_running:
            return
        print("\n🛑 Stopping simulations...")
        if self.baseline_sumo:
            self.baseline_sumo.close()
        if self.rl_sumo:
            self.rl_sumo.close()
        self.is_running = False
        print("✅ Both simulations stopped")

    def __del__(self):
        if self.is_running:
            try:
                self.stop()
            except Exception:
                pass