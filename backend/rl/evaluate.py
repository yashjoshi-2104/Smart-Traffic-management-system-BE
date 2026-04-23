"""
Evaluation Script — Universal DDQN vs Fixed-Time Baseline
Runs both controllers on both networks, collects metrics, saves CSV + summary.

Usage (from backend/ directory):
    python rl/evaluate.py
    python rl/evaluate.py --model ml/ddqn_final.pth --episodes 10
"""

import os
import sys
import csv
import argparse
import time
import numpy as np

# ── Path setup ────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))   # backend/rl/
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)                   # backend/
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, SCRIPT_DIR)

from services.sumo_controller import SumoController
from ddqn_agent import DDQNAgent


# ── Network configs ───────────────────────────────────────────────────────────
NETWORKS = [
    {
        "name":      "simple_intersection",
        "config":    "../sumo/configs/tls_test.sumocfg",
        "tls_id":    "center",
        "port":      8817,
        "edges": {
            "north": "north_in", "south": "south_in",
            "east":  "east_in",  "west":  "west_in",
        },
        "lanes": {
            "north": "north_in_0", "south": "south_in_0",
            "east":  "east_in_0",  "west":  "west_in_0",
        },
    },
    {
        "name":      "urban_arterial",
        "config":    "../sumo/configs/urban_arterial.sumocfg",
        "tls_id":    "B1",
        "port":      8818,
        "edges": {
            "north": "B2B1", "south": "A1B1",
            "east":  "C1B1", "west":  "B0B1",
        },
        "lanes": {
            "north": "B2B1_0", "south": "A1B1_0",
            "east":  "C1B1_0", "west":  "B0B1_0",
        },
    },
]

# ── Normalization (must match training) ───────────────────────────────────────
MAX_QUEUE      = 20
MAX_WAIT       = 60.0
MAX_SPEED      = 15.0
MAX_TIME       = 60.0
MAX_VEHICLES   = 1000.0
MAX_TOTAL_WAIT = 100.0

EVAL_STEPS     = 500    # Steps per episode
WARMUP_STEPS   = 50     # Skip first N steps before recording


# ── State extractor ───────────────────────────────────────────────────────────

def get_state(sumo, net, current_phase, time_in_phase):
    directions = ["north", "south", "east", "west"]
    edges = net["edges"]
    lanes = net["lanes"]
    tls_id = net["tls_id"]

    def queue(d):
        try: return float(sumo.conn.lane.getLastStepHaltingNumber(lanes[d]))
        except: return 0.0

    def wait(d):
        try:
            vids = sumo.conn.edge.getLastStepVehicleIDs(edges[d])
            return float(np.mean([sumo.conn.vehicle.getWaitingTime(v) for v in vids])) if vids else 0.0
        except: return 0.0

    def speed(d):
        try: return float(sumo.conn.edge.getLastStepMeanSpeed(edges[d]))
        except: return 0.0

    def emergency(d):
        try:
            vids = sumo.conn.edge.getLastStepVehicleIDs(edges[d])
            return 1.0 if any(sumo.conn.vehicle.getTypeID(v) == "emergency" for v in vids) else 0.0
        except: return 0.0

    # Neighbor context
    try:
        all_tls = sumo.conn.trafficlight.getIDList()
        nq, nw, ns = [], [], []
        for tid in all_tls:
            if tid == tls_id: continue
            for lane in sumo.conn.trafficlight.getControlledLanes(tid)[:2]:
                nq.append(sumo.conn.lane.getLastStepHaltingNumber(lane))
                nw.append(sumo.conn.lane.getWaitingTime(lane))
                ns.append(sumo.conn.lane.getLastStepMeanSpeed(lane))
        avg_nq = float(np.mean(nq)) if nq else 0.0
        avg_nw = float(np.mean(nw)) if nw else 0.0
        avg_ns = float(np.mean(ns)) if ns else 0.0
        nc     = min(len(all_tls) - 1, 9) / 9.0
    except:
        avg_nq = avg_nw = avg_ns = nc = 0.0

    # Global
    try:
        vids    = sumo.conn.vehicle.getIDList()
        total_v = len(vids)
        avg_spd = float(np.mean([sumo.conn.vehicle.getSpeed(v) for v in vids])) if vids else 0.0
        tot_w   = sum(sumo.conn.vehicle.getWaitingTime(v) for v in vids)
    except:
        total_v = 0; avg_spd = 0.0; tot_w = 0.0

    state = np.array([
        *[queue(d)     / MAX_QUEUE for d in directions],
        *[wait(d)      / MAX_WAIT  for d in directions],
        *[speed(d)     / MAX_SPEED for d in directions],
        *[emergency(d)             for d in directions],
        current_phase / 3.0,
        min(time_in_phase, MAX_TIME) / MAX_TIME,
        avg_nq / MAX_QUEUE,
        avg_nw / MAX_WAIT,
        avg_ns / MAX_SPEED,
        nc,
        total_v / MAX_VEHICLES,
        avg_spd / MAX_SPEED,
        tot_w   / MAX_TOTAL_WAIT,
    ], dtype=np.float32)

    return np.clip(state, 0.0, 1.0)


# ── Metric collection ─────────────────────────────────────────────────────────

def collect_step_metrics(sumo):
    try:
        vids = sumo.conn.vehicle.getIDList()
        if not vids:
            return {"avg_wait": 0.0, "avg_speed": 0.0, "queue": 0,
                    "stopped": 0, "vehicle_count": 0, "emerg_wait": 0.0}

        avg_wait  = float(np.mean([sumo.conn.vehicle.getWaitingTime(v) for v in vids]))
        avg_speed = float(np.mean([sumo.conn.vehicle.getSpeed(v) for v in vids]))
        stopped   = sum(1 for v in vids if sumo.conn.vehicle.getSpeed(v) < 0.1)
        queue     = sum(sumo.conn.lane.getLastStepHaltingNumber(l)
                        for l in sumo.conn.lane.getIDList()
                        if not l.startswith(":"))

        # Emergency vehicle waiting time
        emerg_waits = [sumo.conn.vehicle.getWaitingTime(v) for v in vids
                       if sumo.conn.vehicle.getTypeID(v) == "emergency"]
        emerg_wait = float(np.mean(emerg_waits)) if emerg_waits else 0.0

        return {
            "avg_wait":      avg_wait,
            "avg_speed":     avg_speed,
            "queue":         queue,
            "stopped":       stopped,
            "vehicle_count": len(vids),
            "emerg_wait":    emerg_wait,
        }
    except:
        return {"avg_wait": 0.0, "avg_speed": 0.0, "queue": 0,
                "stopped": 0, "vehicle_count": 0, "emerg_wait": 0.0}


# ── Run one episode ───────────────────────────────────────────────────────────

def run_episode(sumo, net, agent=None):
    """
    Run one episode.
    agent=None → fixed-time baseline (no phase changes, SUMO uses its own TLS logic)
    agent=DDQNAgent → RL controller
    """
    tls_id = net["tls_id"]

    if sumo.is_running:
        sumo.close()
    sumo.start()

    if agent is not None:
        sumo.set_manual_control(tls_id)

    current_phase = 0
    time_in_phase = 0

    all_metrics = []

    for step in range(EVAL_STEPS):
        if agent is not None:
            state  = get_state(sumo, net, current_phase, time_in_phase)
            action = agent.select_action(state, training=False)

            if action != current_phase:
                time_in_phase = 0
                current_phase = action
            else:
                time_in_phase += 1

            sumo.set_traffic_light_phase(tls_id, current_phase)

        sumo.step()

        if step >= WARMUP_STEPS:
            all_metrics.append(collect_step_metrics(sumo))

    sumo.close()

    if not all_metrics:
        return {}

    return {
        "avg_wait":      float(np.mean([m["avg_wait"]      for m in all_metrics])),
        "avg_speed":     float(np.mean([m["avg_speed"]      for m in all_metrics])),
        "avg_queue":     float(np.mean([m["queue"]          for m in all_metrics])),
        "avg_stopped":   float(np.mean([m["stopped"]        for m in all_metrics])),
        "avg_vehicles":  float(np.mean([m["vehicle_count"]  for m in all_metrics])),
        "avg_emerg_wait":float(np.mean([m["emerg_wait"]     for m in all_metrics])),
        "peak_wait":     float(np.max( [m["avg_wait"]       for m in all_metrics])),
        "peak_queue":    float(np.max( [m["queue"]          for m in all_metrics])),
    }


# ── Main evaluation ───────────────────────────────────────────────────────────

def evaluate(model_path: str, num_episodes: int = 5):
    print("\n" + "="*65)
    print("📊  DDQN EVALUATION — Baseline vs RL Agent")
    print("="*65)
    print(f"Model:    {model_path}")
    print(f"Episodes: {num_episodes} per network per controller")
    print(f"Steps:    {EVAL_STEPS} per episode (warmup {WARMUP_STEPS})")
    print("="*65 + "\n")

    # Load trained agent
    print("🤖 Loading DDQN agent...")
    agent = DDQNAgent(
        state_dim=25, action_dim=4,
        lr=0.0005, gamma=0.99,
        epsilon_start=0.0, epsilon_end=0.0, epsilon_decay=1.0,
    )
    agent.load(model_path)
    agent.set_eval_mode()
    print("✅ Agent loaded\n")

    # Results storage
    all_results = []
    summary     = {}

    for net in NETWORKS:
        name = net["name"]
        print(f"\n{'─'*50}")
        print(f"🌐 Network: {name}")
        print(f"{'─'*50}")

        baseline_results = []
        rl_results       = []

        sumo = SumoController(
            config_file=net["config"],
            port=net["port"],
            gui=False,
        )

        # ── Baseline episodes ──────────────────────────────────────────────
        print(f"\n[BASELINE] Running {num_episodes} episodes...")
        for ep in range(num_episodes):
            metrics = run_episode(sumo, net, agent=None)
            baseline_results.append(metrics)
            print(f"  ep{ep+1}: wait={metrics.get('avg_wait',0):.2f}s  "
                  f"speed={metrics.get('avg_speed',0):.2f}m/s  "
                  f"queue={metrics.get('avg_queue',0):.1f}  "
                  f"emerg_wait={metrics.get('avg_emerg_wait',0):.2f}s")

        # ── RL episodes ────────────────────────────────────────────────────
        print(f"\n[RL AGENT] Running {num_episodes} episodes...")
        for ep in range(num_episodes):
            metrics = run_episode(sumo, net, agent=agent)
            rl_results.append(metrics)
            print(f"  ep{ep+1}: wait={metrics.get('avg_wait',0):.2f}s  "
                  f"speed={metrics.get('avg_speed',0):.2f}m/s  "
                  f"queue={metrics.get('avg_queue',0):.1f}  "
                  f"emerg_wait={metrics.get('avg_emerg_wait',0):.2f}s")

        # ── Aggregate ──────────────────────────────────────────────────────
        def mean_key(results, key):
            vals = [r.get(key, 0) for r in results if r]
            return float(np.mean(vals)) if vals else 0.0

        keys = ["avg_wait", "avg_speed", "avg_queue", "avg_stopped",
                "avg_vehicles", "avg_emerg_wait", "peak_wait", "peak_queue"]

        b_agg = {k: mean_key(baseline_results, k) for k in keys}
        r_agg = {k: mean_key(rl_results,       k) for k in keys}

        summary[name] = {"baseline": b_agg, "rl": r_agg}

        # Store per-episode rows for CSV
        for ep in range(num_episodes):
            row = {"network": name, "episode": ep + 1}
            for k in keys:
                row[f"baseline_{k}"] = baseline_results[ep].get(k, 0) if ep < len(baseline_results) else 0
                row[f"rl_{k}"]       = rl_results[ep].get(k, 0)       if ep < len(rl_results)       else 0
            all_results.append(row)

        # ── Print network summary ──────────────────────────────────────────
        def pct(b, r, lower_better=True):
            if b == 0: return "—"
            p = ((r - b) / b) * 100
            sign = "↓" if lower_better else "↑"
            good = (p < 0) if lower_better else (p > 0)
            arrow = f"{sign} {abs(p):.1f}%"
            tag = "✅" if good else "❌"
            return f"{arrow} {tag}"

        print(f"\n{'─'*50}")
        print(f"  SUMMARY — {name}")
        print(f"{'─'*50}")
        print(f"  {'Metric':<22} {'Baseline':>10} {'RL Agent':>10}  {'Delta':>14}")
        print(f"  {'─'*22} {'─'*10} {'─'*10}  {'─'*14}")
        print(f"  {'Avg wait (s)':<22} {b_agg['avg_wait']:>10.2f} {r_agg['avg_wait']:>10.2f}  {pct(b_agg['avg_wait'], r_agg['avg_wait']):>14}")
        print(f"  {'Avg speed (m/s)':<22} {b_agg['avg_speed']:>10.2f} {r_agg['avg_speed']:>10.2f}  {pct(b_agg['avg_speed'], r_agg['avg_speed'], False):>14}")
        print(f"  {'Avg queue (veh)':<22} {b_agg['avg_queue']:>10.1f} {r_agg['avg_queue']:>10.1f}  {pct(b_agg['avg_queue'], r_agg['avg_queue']):>14}")
        print(f"  {'Peak wait (s)':<22} {b_agg['peak_wait']:>10.2f} {r_agg['peak_wait']:>10.2f}  {pct(b_agg['peak_wait'], r_agg['peak_wait']):>14}")
        print(f"  {'Emerg wait (s)':<22} {b_agg['avg_emerg_wait']:>10.2f} {r_agg['avg_emerg_wait']:>10.2f}  {pct(b_agg['avg_emerg_wait'], r_agg['avg_emerg_wait']):>14}")

    # ── Save CSV ───────────────────────────────────────────────────────────────
    out_dir = os.path.join(BACKEND_DIR, "rl", "logs")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "evaluation_results.csv")

    if all_results:
        fieldnames = list(all_results[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_results)
        print(f"\n💾 CSV saved to: {csv_path}")

    # ── Final cross-network summary ────────────────────────────────────────────
    print("\n" + "="*65)
    print("🏆  FINAL CROSS-NETWORK SUMMARY")
    print("="*65)

    all_b_waits, all_r_waits   = [], []
    all_b_speeds, all_r_speeds = [], []
    all_b_emerg, all_r_emerg   = [], []

    for name, res in summary.items():
        b, r = res["baseline"], res["rl"]
        all_b_waits.append(b["avg_wait"]);   all_r_waits.append(r["avg_wait"])
        all_b_speeds.append(b["avg_speed"]); all_r_speeds.append(r["avg_speed"])
        all_b_emerg.append(b["avg_emerg_wait"]); all_r_emerg.append(r["avg_emerg_wait"])

    def overall_improvement(b_list, r_list, lower_better=True):
        b = np.mean(b_list); r = np.mean(r_list)
        if b == 0: return 0.0
        pct = ((r - b) / b) * 100
        return -pct if lower_better else pct

    print(f"\n  Overall waiting time improvement:   {overall_improvement(all_b_waits, all_r_waits):.1f}%")
    print(f"  Overall speed improvement:          {overall_improvement(all_b_speeds, all_r_speeds, False):.1f}%")
    print(f"  Overall emergency wait improvement: {overall_improvement(all_b_emerg, all_r_emerg):.1f}%")
    print(f"\n  Results saved to: {csv_path}")
    print("="*65 + "\n")

    return summary


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evaluate trained DDQN vs baseline")
    parser.add_argument("--model",    type=str, default="../backend/ml/ddqn_final.pth",
                        help="Path to trained model .pth file")
    parser.add_argument("--episodes", type=int, default=5,
                        help="Number of evaluation episodes per network (default: 5)")
    args = parser.parse_args()

    model_path = os.path.abspath(
        os.path.join(BACKEND_DIR, args.model) if not os.path.isabs(args.model)
        else args.model
    )

    if not os.path.exists(model_path):
        # Try default location
        default = os.path.join(BACKEND_DIR, "ml", "ddqn_final.pth")
        if os.path.exists(default):
            model_path = default
        else:
            print(f"❌ Model not found at: {model_path}")
            print(f"   Also tried: {default}")
            print("   Run training first: python rl/train_universal.py")
            sys.exit(1)

    evaluate(model_path, num_episodes=args.episodes)


if __name__ == "__main__":
    main()