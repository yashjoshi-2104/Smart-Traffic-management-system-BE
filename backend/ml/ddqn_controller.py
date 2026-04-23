"""
DDQN Controller - Trained RL Model for Traffic Signal Control

Integrates trained DDQN model with the backend SUMO controller.
Uses universal 25-value state (matches train_universal.py).
"""

import os
import numpy as np
from typing import Optional, Dict

from .ddqn_agent import DDQNAgent


class DDQNController:
    """
    Controller that uses trained DDQN model for traffic signal control.
    Supports any network topology via injected edge/lane configuration.
    State dim: 25 (universal — matches train_universal.py)

    Phase mapping for B1 (urban arterial — 8 phases):
        Agent action 0 → SUMO phase 0  (N/S left-turn green)
        Agent action 1 → SUMO phase 2  (N/S straight green)
        Agent action 2 → SUMO phase 4  (E/W left-turn green)
        Agent action 3 → SUMO phase 6  (E/W straight green)
    Yellow phases (1, 3, 5, 7) are handled by SUMO automatically
    when the controller holds a green phase long enough.

    For simple intersection (4 phases), PHASE_MAP is identity (0→0,1→1,2→2,3→3).
    """

    def __init__(
        self,
        sumo_controller,
        model_path: Optional[str] = None,
        tls_id: str = "center",
        edges: Optional[Dict[str, str]] = None,
        lanes: Optional[Dict[str, str]] = None,
        phase_map: Optional[Dict[int, int]] = None,
    ):
        self.sumo   = sumo_controller
        self.tls_id = tls_id

        self.edges = edges or {
            'north': 'north_in',
            'south': 'south_in',
            'east':  'east_in',
            'west':  'west_in',
        }
        self.lanes = lanes or {
            'north': 'north_in_0',
            'south': 'south_in_0',
            'east':  'east_in_0',
            'west':  'west_in_0',
        }

        # Phase map: agent action (0-3) → actual SUMO phase index
        # Default is identity (simple intersection has 4 phases: 0,1,2,3)
        # For urban arterial B1 (8 phases), dual_sim_manager passes {0:0,1:2,2:4,3:6}
        self.PHASE_MAP = phase_map if phase_map else {0: 0, 1: 1, 2: 2, 3: 3}

        # Normalization constants (must match train_universal.py)
        self.MAX_QUEUE         = 20
        self.MAX_WAIT          = 60.0
        self.MAX_SPEED         = 15.0
        self.MAX_TIME_IN_PHASE = 60.0
        self.MAX_VEHICLES      = 1000.0
        self.MAX_TOTAL_WAIT    = 100.0

        # State tracking (always in agent action space 0-3)
        self.current_phase   = 0
        self.time_in_phase   = 0
        self.step_count      = 0
        self.MIN_PHASE_STEPS = 10    # Hold each phase at least 10 steps
        self.MAX_PHASE_STEPS = 45    # Force switch after 45 steps
        self.STARVATION_LIMIT = 60   # Max steps any phase can be skipped
        self.last_phase_step = {0: 0, 1: 0, 2: 0, 3: 0}

        # Initialize DDQN agent — 25-value state, 4 actions
        print("🤖 Initializing DDQN agent (state_dim=25)...")
        self.agent = DDQNAgent(
            state_dim=25,
            action_dim=4,
            lr=0.0005,
            gamma=0.99,
            epsilon_start=0.0,
            epsilon_end=0.0,
            epsilon_decay=1.0,
        )

        # Resolve model path
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "ddqn_final.pth")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"❌ Trained model not found at: {model_path}\n"
                f"Please copy the trained .pth file to backend/ml/ after training completes."
            )

        print(f"📂 Loading model from: {model_path}")
        self.agent.load(model_path)
        self.agent.set_eval_mode()
        print("✅ DDQN Controller ready (25-value state)!")
        print(f"   Phase map: {self.PHASE_MAP}")

    # ── Inference ─────────────────────────────────────────────────────────────

    def get_action(self) -> int:
        """
        Get next action from trained DDQN model.
        Returns actual SUMO phase index (mapped from agent action 0-3).
        """
        self.time_in_phase += 1
        self.step_count    += 1

        # Track when current phase last ran
        self.last_phase_step[self.current_phase] = self.step_count

        # Check for starving phase (not run in STARVATION_LIMIT steps)
        starving_phase = None
        max_skipped    = 0
        for phase in range(4):
            if phase == self.current_phase:
                continue
            steps_since = self.step_count - self.last_phase_step[phase]
            if steps_since > self.STARVATION_LIMIT and steps_since > max_skipped:
                max_skipped    = steps_since
                starving_phase = phase

        # Force switch to starving phase
        if starving_phase is not None:
            self.current_phase = starving_phase
            self.time_in_phase = 0
            return self.PHASE_MAP.get(self.current_phase, self.current_phase)

        # Force switch after max steps
        if self.time_in_phase >= self.MAX_PHASE_STEPS:
            state      = self._get_state()
            new_action = self.agent.select_action(state, training=False)
            if new_action in (0, 1, 2, 3) and new_action != self.current_phase:
                self.current_phase = new_action
            else:
                self.current_phase = min(
                    [p for p in range(4) if p != self.current_phase],
                    key=lambda p: self.last_phase_step[p]
                )
            self.time_in_phase = 0
            return self.PHASE_MAP.get(self.current_phase, self.current_phase)

        # Normal operation: query agent after minimum phase duration
        if self.time_in_phase >= self.MIN_PHASE_STEPS:
            state      = self._get_state()
            new_action = self.agent.select_action(state, training=False)
            if new_action in (0, 1, 2, 3) and new_action != self.current_phase:
                self.current_phase = new_action
                self.time_in_phase = 0

        # ── KEY FIX: map agent action to actual SUMO phase index ─────────────
        return self.PHASE_MAP.get(self.current_phase, self.current_phase)

    def reset(self):
        self.current_phase   = 0
        self.time_in_phase   = 0
        self.step_count      = 0
        self.last_phase_step = {0: 0, 1: 0, 2: 0, 3: 0}

    # ── State extraction (25 values, matches train_universal.py) ─────────────

    def _get_state(self) -> np.ndarray:
        directions = ['north', 'south', 'east', 'west']

        # Local (18 values)
        queues      = [self._get_queue(d)     for d in directions]
        waits       = [self._get_wait(d)      for d in directions]
        speeds      = [self._get_speed(d)     for d in directions]
        emergencies = [self._get_emergency(d) for d in directions]

        # Neighbor context (4 values)
        try:
            conn    = self.sumo.conn
            all_tls = conn.trafficlight.getIDList()
            nq, nw, ns = [], [], []
            for tid in all_tls:
                if tid == self.tls_id:
                    continue
                for lane in conn.trafficlight.getControlledLanes(tid)[:2]:
                    nq.append(conn.lane.getLastStepHaltingNumber(lane))
                    nw.append(conn.lane.getWaitingTime(lane))
                    ns.append(conn.lane.getLastStepMeanSpeed(lane))
            avg_nq = float(np.mean(nq)) if nq else 0.0
            avg_nw = float(np.mean(nw)) if nw else 0.0
            avg_ns = float(np.mean(ns)) if ns else 0.0
            nc     = min(len(all_tls) - 1, 9) / 9.0
        except Exception:
            avg_nq = avg_nw = avg_ns = nc = 0.0

        # Global (3 values)
        try:
            conn    = self.sumo.conn
            vids    = conn.vehicle.getIDList()
            total_v = len(vids)
            avg_spd = float(np.mean([conn.vehicle.getSpeed(v) for v in vids])) if vids else 0.0
            tot_w   = sum(conn.vehicle.getWaitingTime(v) for v in vids)
        except Exception:
            total_v = 0
            avg_spd = 0.0
            tot_w   = 0.0

        state = np.array([
            *[q / self.MAX_QUEUE for q in queues],                                      # 4
            *[w / self.MAX_WAIT  for w in waits],                                       # 4
            *[s / self.MAX_SPEED for s in speeds],                                      # 4
            *emergencies,                                                                # 4
            self.current_phase / 3.0,                                                   # 1
            min(self.time_in_phase, self.MAX_TIME_IN_PHASE) / self.MAX_TIME_IN_PHASE,  # 1
            avg_nq / self.MAX_QUEUE,                                                    # 1
            avg_nw / self.MAX_WAIT,                                                     # 1
            avg_ns / self.MAX_SPEED,                                                    # 1
            nc,                                                                         # 1
            total_v / self.MAX_VEHICLES,                                                # 1
            avg_spd / self.MAX_SPEED,                                                   # 1
            tot_w   / self.MAX_TOTAL_WAIT,                                              # 1
        ], dtype=np.float32)                                                            # = 25 total

        return np.clip(state, 0.0, 1.0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_queue(self, direction: str) -> float:
        try:
            return float(self.sumo.get_lane_queue_length(self.lanes[direction]))
        except Exception:
            return 0.0

    def _get_wait(self, direction: str) -> float:
        try:
            return float(self.sumo.get_average_waiting_time_by_edge(self.edges[direction]))
        except Exception:
            return 0.0

    def _get_speed(self, direction: str) -> float:
        try:
            return float(self.sumo.get_average_speed_by_edge(self.edges[direction]))
        except Exception:
            return 0.0

    def _get_emergency(self, direction: str) -> float:
        try:
            conn = self.sumo.conn
            vids = conn.edge.getLastStepVehicleIDs(self.edges[direction])
            for v in vids:
                if conn.vehicle.getTypeID(v) == "emergency":
                    return 1.0
            return 0.0
        except Exception:
            return 0.0