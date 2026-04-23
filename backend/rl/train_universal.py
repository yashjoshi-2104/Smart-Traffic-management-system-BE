"""
Universal DDQN Training Script
Trains one model on both simple_intersection AND urban_arterial simultaneously.
Run from: backend/ directory

Usage:
    cd backend
    python ../rl/train_universal.py
    python ../rl/train_universal.py --resume ../rl/checkpoints/ddqn_ep5000.pth
"""

import os
import sys
import time
import random
import argparse
import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
# Script lives in backend/rl/ — backend root is one level up
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))   # backend/rl/
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)                   # backend/
RL_DIR      = SCRIPT_DIR                                    # backend/rl/

sys.path.insert(0, BACKEND_DIR)   # so 'services' is importable
sys.path.insert(0, RL_DIR)        # so 'rl.ddqn_agent' is importable

from services.sumo_controller import SumoController
from ddqn_agent import DDQNAgent
from replay_buffer import ReplayBuffer


# ── Config ────────────────────────────────────────────────────────────────────

class Config:
    # Training
    NUM_EPISODES        = 500
    MAX_STEPS           = 500       # 1 hour sim time per episode
    WARMUP_STEPS        = 50        # Skip first 300 steps before recording metrics

    # Agent
    STATE_DIM           = 25         # Universal 25-value state
    ACTION_DIM          = 4          # 4 TLS phases
    LR                  = 0.0005
    GAMMA               = 0.99
    EPSILON_START       = 1.0
    EPSILON_END         = 0.05
    EPSILON_DECAY       = 0.996     # Decays to 0.05 over ~750 episodes
    TARGET_UPDATE_FREQ  = 1000       # Steps between target network updates

    # Replay buffer
    BUFFER_CAPACITY     = 50000
    BATCH_SIZE          = 64
    MIN_BUFFER_SIZE     = 1000       # Start training after this many samples

    # Checkpoints
    CHECKPOINT_FREQ     = 200       # Save every N episodes
    CHECKPOINT_DIR      = "../rl/checkpoints"
    FINAL_MODEL_PATH    = "ml/ddqn_simple.pth"  # Where backend loads from

    # Networks (50/50 split each episode)
    NETWORKS = [
    {
        "name":        "simple_intersection",
        "config":      "../sumo/configs/tls_test.sumocfg",
        "tls_id":      "center",
        "port_base":   8815,
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
]

    # Normalization
    MAX_QUEUE         = 20
    MAX_WAIT          = 60.0
    MAX_SPEED         = 15.0
    MAX_TIME_IN_PHASE = 60.0
    MAX_VEHICLES      = 1000.0
    MAX_TOTAL_WAIT    = 100.0

    # Reward weights
    W_WAIT      = -0.01
    W_QUEUE     = -0.005
    W_STOPPED   = -0.003
    W_EMERGENCY = +0.02


# ── State extractor ───────────────────────────────────────────────────────────

class StateExtractor:
    """
    Extracts universal 25-value state from SUMO via TraCI.
    Network-agnostic: configured via edges/lanes dicts from NETWORK_CONFIGS.
    """

    def __init__(self, sumo: SumoController, net_cfg: dict, cfg: Config):
        self.sumo   = sumo
        self.edges  = net_cfg["edges"]
        self.lanes  = net_cfg["lanes"]
        self.tls_id = net_cfg["tls_id"]
        self.cfg    = cfg

    def get_state(self, current_phase: int, time_in_phase: int) -> np.ndarray:
        directions = ["north", "south", "east", "west"]

        # ── Local (18 values) ─────────────────────────────────────────────
        queues = [self._queue(d)  for d in directions]
        waits  = [self._wait(d)   for d in directions]
        speeds = [self._speed(d)  for d in directions]
        emergencies = [self._emergency(d) for d in directions]

        # ── Neighbor context (4 values) ───────────────────────────────────
        try:
            all_tls = self.sumo.conn.trafficlight.getIDList()
            neighbor_queues, neighbor_waits, neighbor_speeds = [], [], []
            for tid in all_tls:
                if tid == self.tls_id:
                    continue
                controlled = self.sumo.conn.trafficlight.getControlledLanes(tid)
                for lane in controlled[:2]:  # Sample first 2 lanes per TLS
                    neighbor_queues.append(
                        self.sumo.conn.lane.getLastStepHaltingNumber(lane))
                    neighbor_waits.append(
                        self.sumo.conn.lane.getWaitingTime(lane))
                    neighbor_speeds.append(
                        self.sumo.conn.lane.getLastStepMeanSpeed(lane))
            avg_nq = np.mean(neighbor_queues) if neighbor_queues else 0.0
            avg_nw = np.mean(neighbor_waits)  if neighbor_waits  else 0.0
            avg_ns = np.mean(neighbor_speeds) if neighbor_speeds else 0.0
            nc     = min(len(all_tls) - 1, 9) / 9.0
        except Exception:
            avg_nq, avg_nw, avg_ns, nc = 0.0, 0.0, 0.0, 0.0

        # ── Global (3 values) ─────────────────────────────────────────────
        try:
            vids         = self.sumo.conn.vehicle.getIDList()
            total_veh    = len(vids)
            avg_net_spd  = (np.mean([self.sumo.conn.vehicle.getSpeed(v)
                                     for v in vids]) if vids else 0.0)
            total_wait   = sum(self.sumo.conn.vehicle.getWaitingTime(v)
                               for v in vids)
        except Exception:
            total_veh, avg_net_spd, total_wait = 0, 0.0, 0.0

        # ── Assemble & normalise ───────────────────────────────────────────
        cfg = self.cfg
        state = np.array([
            # Local queues (4)
            *[q / cfg.MAX_QUEUE for q in queues],
            # Local waits (4)
            *[w / cfg.MAX_WAIT  for w in waits],
            # Local speeds (4)
            *[s / cfg.MAX_SPEED for s in speeds],
            # Emergency flags (4)
            *emergencies,
            # Phase info (2)
            current_phase / 3.0,
            min(time_in_phase, cfg.MAX_TIME_IN_PHASE) / cfg.MAX_TIME_IN_PHASE,
            # Neighbour context (4)
            avg_nq / cfg.MAX_QUEUE,
            avg_nw / cfg.MAX_WAIT,
            avg_ns / cfg.MAX_SPEED,
            nc,
            # Global (3)
            total_veh   / cfg.MAX_VEHICLES,
            avg_net_spd / cfg.MAX_SPEED,
            total_wait  / cfg.MAX_TOTAL_WAIT,
        ], dtype=np.float32)

        return np.clip(state, 0.0, 1.0)

    # ── Helpers ───────────────────────────────────────────────────────────
    def _queue(self, direction: str) -> float:
        try:
            return self.sumo.conn.lane.getLastStepHaltingNumber(
                self.lanes[direction])
        except Exception:
            return 0.0

    def _wait(self, direction: str) -> float:
        try:
            vids = self.sumo.conn.edge.getLastStepVehicleIDs(
                self.edges[direction])
            if not vids:
                return 0.0
            return np.mean([self.sumo.conn.vehicle.getWaitingTime(v)
                            for v in vids])
        except Exception:
            return 0.0

    def _speed(self, direction: str) -> float:
        try:
            return self.sumo.conn.edge.getLastStepMeanSpeed(
                self.edges[direction])
        except Exception:
            return 0.0

    def _emergency(self, direction: str) -> float:
        try:
            vids = self.sumo.conn.edge.getLastStepVehicleIDs(
                self.edges[direction])
            for v in vids:
                if self.sumo.conn.vehicle.getTypeID(v) == "emergency":
                    return 1.0
            return 0.0
        except Exception:
            return 0.0


# ── Reward function ───────────────────────────────────────────────────────────

def compute_reward(sumo: SumoController, cfg: Config) -> float:
    try:
        vids = sumo.conn.vehicle.getIDList()
        if not vids:
            return 0.0

        total_wait    = sum(sumo.conn.vehicle.getWaitingTime(v) for v in vids)
        avg_wait      = total_wait / len(vids)

        stopped       = sum(1 for v in vids
                            if sumo.conn.vehicle.getSpeed(v) < 0.1)
        stopped_frac  = stopped / len(vids)

        total_queue   = sum(sumo.conn.lane.getLastStepHaltingNumber(l)
                            for l in sumo.conn.lane.getIDList()
                            if not l.startswith(":"))

        # Emergency bonus
        emerg_bonus = 0.0
        for v in vids:
            if sumo.conn.vehicle.getTypeID(v) == "emergency":
                if sumo.conn.vehicle.getWaitingTime(v) < 5.0:
                    emerg_bonus += cfg.W_EMERGENCY

        reward = (cfg.W_WAIT    * avg_wait
                + cfg.W_QUEUE   * total_queue
                + cfg.W_STOPPED * stopped_frac
                + emerg_bonus)
        return float(reward)
    except Exception:
        return 0.0


# ── Training loop ─────────────────────────────────────────────────────────────

def run_episode(sumo: SumoController, extractor: StateExtractor,
                agent: DDQNAgent, buffer: ReplayBuffer,
                cfg: Config, episode: int) -> dict:
    """Run one training episode. Returns metrics dict."""

    tls_id = extractor.tls_id
    current_phase = 0
    time_in_phase = 0

    # Reset simulation by closing and restarting
    if sumo.is_running:
        sumo.close()
    sumo.start()
    sumo.set_manual_control(tls_id)
    sumo.set_traffic_light_phase(tls_id, current_phase)

    state = extractor.get_state(current_phase, time_in_phase)

    total_reward  = 0.0
    total_loss    = 0.0
    loss_count    = 0
    total_wait    = 0.0
    metric_steps  = 0

    for step in range(cfg.MAX_STEPS):
        # Select action
        action = agent.select_action(state, training=True)

        # Apply to SUMO
        if action != current_phase:
            time_in_phase = 0
            current_phase = action
        else:
            time_in_phase += 1

        sumo.set_traffic_light_phase(tls_id, current_phase)
        sumo.step()

        # Get next state and reward
        next_state = extractor.get_state(current_phase, time_in_phase)
        reward     = compute_reward(sumo, cfg)

        # Store experience
        buffer.push(state, action, reward, next_state, False)

        # Train if ready
        if len(buffer) >= cfg.MIN_BUFFER_SIZE and buffer.is_ready(cfg.BATCH_SIZE):
            batch = buffer.sample(cfg.BATCH_SIZE)
            loss  = agent.train(batch)
            total_loss += loss
            loss_count += 1

        state        = next_state
        total_reward += reward

        # Collect metrics after warmup
        if step >= cfg.WARMUP_STEPS:
            try:
                vids = sumo.conn.vehicle.getIDList()
                if vids:
                    total_wait += sum(sumo.conn.vehicle.getWaitingTime(v)
                                      for v in vids) / len(vids)
                    metric_steps += 1
            except Exception:
                pass

    avg_wait = total_wait / metric_steps if metric_steps > 0 else 0.0
    avg_loss = total_loss / loss_count   if loss_count  > 0 else 0.0

    return {
        "reward":   total_reward,
        "avg_wait": avg_wait,
        "avg_loss": avg_loss,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()

    cfg = Config()
    os.makedirs(cfg.CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(cfg.FINAL_MODEL_PATH), exist_ok=True)

    # ── Agent + Buffer ────────────────────────────────────────────────────
    agent = DDQNAgent(
        state_dim          = cfg.STATE_DIM,
        action_dim         = cfg.ACTION_DIM,
        lr                 = cfg.LR,
        gamma              = cfg.GAMMA,
        epsilon_start      = cfg.EPSILON_START,
        epsilon_end        = cfg.EPSILON_END,
        epsilon_decay      = cfg.EPSILON_DECAY,
        target_update_freq = cfg.TARGET_UPDATE_FREQ,
    )
    buffer       = ReplayBuffer(capacity=cfg.BUFFER_CAPACITY)
    start_ep     = 0

    if args.resume and os.path.exists(args.resume):
        agent.load(args.resume)
        print(f"✅ Resumed from {args.resume}")
        # Try to parse episode number from filename
        try:
            start_ep = int(args.resume.split("ep")[-1].split(".")[0])
        except Exception:
            start_ep = 0

    print("\n" + "="*60)
    print("🏋️  UNIVERSAL DDQN TRAINING")
    print("="*60)
    print(f"Episodes:    {cfg.NUM_EPISODES}")
    print(f"State dim:   {cfg.STATE_DIM} (universal)")
    print(f"Networks:    {[n['name'] for n in cfg.NETWORKS]}")
    print(f"Device:      {agent.device}")
    print(f"Start ep:    {start_ep}")
    print("="*60 + "\n")

    # Metrics tracking
    rewards_by_network = {n["name"]: [] for n in cfg.NETWORKS}
    waits_by_network   = {n["name"]: [] for n in cfg.NETWORKS}
    start_time         = time.time()

    for episode in range(start_ep, cfg.NUM_EPISODES):
        # Pick network randomly (50/50)
        net_cfg = random.choice(cfg.NETWORKS)

        # Create SUMO controller for this episode
        sumo = SumoController(
            config_file = net_cfg["config"],
            port        = net_cfg["port_base"],
            gui         = False,
        )
        extractor = StateExtractor(sumo, net_cfg, cfg)

        try:
            metrics = run_episode(sumo, extractor, agent, buffer, cfg, episode)
        except Exception as e:
            print(f"⚠️  Episode {episode} error ({net_cfg['name']}): {e}")
            metrics = {"reward": 0.0, "avg_wait": 0.0, "avg_loss": 0.0}
        finally:
            if sumo.is_running:
                sumo.close()

        # Store metrics
        rewards_by_network[net_cfg["name"]].append(metrics["reward"])
        waits_by_network[net_cfg["name"]].append(metrics["avg_wait"])

        # Decay epsilon once per episode
        agent.decay_epsilon()

        # ── Logging every 100 episodes ────────────────────────────────────
        if (episode + 1) % 100 == 0:
            elapsed      = time.time() - start_time
            eps_done     = episode - start_ep + 1
            eps_per_sec  = eps_done / elapsed if elapsed > 0 else 1
            remaining    = (cfg.NUM_EPISODES - episode - 1) / eps_per_sec
            eta_h        = remaining / 3600

            lines = [f"\nEp {episode+1}/{cfg.NUM_EPISODES} | "
                     f"ε={agent.epsilon:.3f} | "
                     f"buf={len(buffer)} | "
                     f"loss={metrics['avg_loss']:.4f} | "
                     f"ETA={eta_h:.1f}h"]

            for net in cfg.NETWORKS:
                name   = net["name"]
                recent = waits_by_network[name][-50:] if waits_by_network[name] else [0]
                lines.append(f"  {name}: avg_wait={np.mean(recent):.2f}s "
                             f"({len(waits_by_network[name])} eps)")
            print("\n".join(lines))

        # ── Checkpoint ────────────────────────────────────────────────────
        if (episode + 1) % cfg.CHECKPOINT_FREQ == 0:
            path = os.path.join(cfg.CHECKPOINT_DIR,
                                f"ddqn_ep{episode+1}.pth")
            agent.save(path)

    # ── Final save ────────────────────────────────────────────────────────
    agent.save(cfg.FINAL_MODEL_PATH)
    print(f"\n✅ Training complete. Model saved to {cfg.FINAL_MODEL_PATH}")


if __name__ == "__main__":
    main()