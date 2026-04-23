#!/usr/bin/env python3
"""
Simple Intersection DDQN Training Script — GPU Ready
=====================================================
Network : single_tls_intersection
TLS ID  : center
Edges   : north_in, south_in, east_in, west_in
Lanes   : north_in_0, south_in_0, east_in_0, west_in_0

SETUP (for GPU machine):
  1. Edit SUMO_BASE_PATH below to match your machine
  2. Run from DDQN_Training_Package/backend/:
       python rl/train_simple.py
"""

import os
import sys
import torch
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from rl.ddqn_agent import DDQNAgent
from rl.replay_buffer import ReplayBuffer
from services.sumo_controller import SumoController
from ml.ddqn_controller import DDQNController

# ============================================================================
# SET THIS to the absolute path of your DDQN_Training_Package/sumo folder
# ============================================================================
SUMO_BASE_PATH = r"C:\Users\Nimish\Downloads\DDQN_Training_Package\DDQN_Training_Package\sumo"
# Linux example : SUMO_BASE_PATH = "/home/yourname/DDQN_Training_Package/sumo"
# ============================================================================

CONFIG = {
    'network':          'single_tls_intersection',
    'config_file':      os.path.join(SUMO_BASE_PATH, 'configs', 'tls_test.sumocfg'),
    'tls_id':           'center',
    'edges': {
        'north': 'north_in',
        'south': 'south_in',
        'east':  'east_in',
        'west':  'west_in',
    },
    'lanes': {
        'north': 'north_in_0',
        'south': 'south_in_0',
        'east':  'east_in_0',
        'west':  'west_in_0',
    },
    'port':             8817,
    'episodes':         3000,
    'max_steps':        600,
    'state_dim':        25,
    'action_dim':       4,
    'batch_size':       128,
    'buffer_capacity':  100000,
    'epsilon_start':    1.0,
    'epsilon_end':      0.01,
    'epsilon_decay':    0.9985,  # faster decay for simpler problem — hits 0.01 around ep 3000
    'lr':               0.0005,
    'gamma':            0.99,
    'target_update_freq': 100,
    'save_path':        'ml/ddqn_simple.pth',
    'checkpoint_dir':   'rl/checkpoints_simple',
    'checkpoint_every': 500,
    'print_every':      10,
}


def print_gpu_info():
    if torch.cuda.is_available():
        print(f"   GPU : {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("   Device: CPU (no GPU detected — training will be slow)")


def train():
    start_time = datetime.now()

    print("=" * 80)
    print("SIMPLE INTERSECTION DDQN TRAINING")
    print("=" * 80)
    print(f"Network    : {CONFIG['network']}")
    print(f"Port       : {CONFIG['port']}")
    print(f"Episodes   : {CONFIG['episodes']}")
    print(f"Max steps  : {CONFIG['max_steps']}")
    print(f"Batch size : {CONFIG['batch_size']}")
    print(f"e decay    : {CONFIG['epsilon_decay']} (once per episode, hits 0.01 ~ep 3000)")
    print(f"Save to    : {CONFIG['save_path']}")
    print_gpu_info()
    print("=" * 80 + "\n")

    if not os.path.exists(CONFIG['config_file']):
        print(f"SUMO config not found: {CONFIG['config_file']}")
        print("Please update SUMO_BASE_PATH at the top of this file.")
        sys.exit(1)

    os.makedirs(CONFIG['checkpoint_dir'], exist_ok=True)
    os.makedirs('ml', exist_ok=True)

    agent = DDQNAgent(
        state_dim=CONFIG['state_dim'],
        action_dim=CONFIG['action_dim'],
        lr=CONFIG['lr'],
        gamma=CONFIG['gamma'],
        epsilon_start=CONFIG['epsilon_start'],
        epsilon_end=CONFIG['epsilon_end'],
        epsilon_decay=CONFIG['epsilon_decay'],
        target_update_freq=CONFIG['target_update_freq'],
    )

    buffer          = ReplayBuffer(capacity=CONFIG['buffer_capacity'])
    episode_rewards = []
    episode_waits   = []
    best_avg_wait   = float('inf')
    loss            = 0

    for episode in range(CONFIG['episodes']):
        try:
            sumo = SumoController(
                config_file=CONFIG['config_file'],
                port=CONFIG['port'],
                gui=False
            )
            sumo.start()
            sumo.set_manual_control(CONFIG['tls_id'])

            controller = DDQNController(
                sumo_controller=sumo,
                model_path="SKIP_LOAD",
                tls_id=CONFIG['tls_id'],
                edges=CONFIG['edges'],
                lanes=CONFIG['lanes'],
            )
            controller.agent = agent

            episode_reward     = 0
            episode_wait_times = []

            for step in range(CONFIG['max_steps']):
                try:
                    state  = controller._get_state()
                    action = agent.select_action(state)

                    sumo.set_traffic_light_phase(CONFIG['tls_id'], action)
                    sumo.step()

                    next_state = controller._get_state()

                    detailed = sumo.get_detailed_state()
                    vehicles = detailed.get('vehicles', {})

                    if vehicles:
                        avg_wait = sum(v['waiting_time'] for v in vehicles.values()) / len(vehicles)
                        reward   = -avg_wait / 10.0
                    else:
                        avg_wait = 0.0
                        reward   = 0.0

                    episode_reward += reward
                    episode_wait_times.append(avg_wait)
                    buffer.push(state, action, reward, next_state, False)

                    if len(buffer) >= CONFIG['batch_size']:
                        batch = buffer.sample(CONFIG['batch_size'])
                        loss  = agent.train(batch)

                except Exception as e:
                    print(f"  Step {step} error: {e}")
                    break

            sumo.close()

            # ── Decay epsilon ONCE per episode (not per step) ──────────────
            agent.decay_epsilon()

            avg_wait = np.mean(episode_wait_times) if episode_wait_times else 0.0
            episode_rewards.append(episode_reward)
            episode_waits.append(avg_wait)

            if episode % agent.target_update_freq == 0:
                agent.update_target_network()

            if (episode + 1) % CONFIG['checkpoint_every'] == 0:
                ckpt = f"{CONFIG['checkpoint_dir']}/episode_{episode+1}.pth"
                torch.save({
                    'episode':               episode + 1,
                    'policy_net_state_dict': agent.policy_net.state_dict(),
                    'target_net_state_dict': agent.target_net.state_dict(),
                    'optimizer_state_dict':  agent.optimizer.state_dict(),
                    'epsilon':               agent.epsilon,
                    'episode_rewards':       episode_rewards,
                    'episode_waits':         episode_waits,
                }, ckpt)
                print(f"   Checkpoint saved: {ckpt}")

            if avg_wait < best_avg_wait and avg_wait > 0:
                best_avg_wait = avg_wait
                torch.save({
                    'policy_net_state_dict': agent.policy_net.state_dict(),
                    'target_net_state_dict': agent.target_net.state_dict(),
                    'optimizer_state_dict':  agent.optimizer.state_dict(),
                    'epsilon':               agent.epsilon,
                    'episode':               episode + 1,
                    'best_avg_wait':         best_avg_wait,
                }, CONFIG['save_path'])

            if (episode + 1) % CONFIG['print_every'] == 0:
                recent    = episode_waits[-100:] if len(episode_waits) >= 100 else episode_waits
                elapsed   = (datetime.now() - start_time).total_seconds()
                eta_hours = ((CONFIG['episodes'] - (episode + 1)) * (elapsed / (episode + 1))) / 3600
                print(f"Ep {episode+1:>6}/{CONFIG['episodes']} | "
                      f"e={agent.epsilon:.4f} | "
                      f"buf={len(buffer):>6} | "
                      f"loss={loss if isinstance(loss, (int, float)) else 0:.4f} | "
                      f"avg_wait={np.mean(recent):>6.2f}s | "
                      f"best={best_avg_wait:>6.2f}s | "
                      f"ETA={eta_hours:.1f}h")

        except Exception as e:
            print(f"Episode {episode+1} failed: {e}")
            try:
                sumo.close()
            except Exception:
                pass
            continue

    print()
    print("=" * 80)
    print("TRAINING COMPLETE - SIMPLE INTERSECTION")
    print(f"Best avg wait : {best_avg_wait:.2f}s")
    print(f"Final model   : {CONFIG['save_path']}")
    print("=" * 80)


if __name__ == '__main__':
    train()