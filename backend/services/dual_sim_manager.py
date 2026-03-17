# backend/services/dual_sim_manager.py
"""
DualSimManager - Orchestrates two parallel SUMO simulations
One baseline (fixed-time control), one with RL/manual control
"""

import time
from services.sumo_controller import SumoController


class DualSimManager:
    """
    Manages two parallel SUMO simulations for real-time comparison
    
    Usage:
        manager = DualSimManager(
            config_file="../sumo/configs/backend_test.sumocfg"
        )
        
        manager.start()
        
        for i in range(100):
            baseline_state, rl_state = manager.step()
            # Broadcast to frontend, apply controls, etc.
        
        manager.stop()
    """
    
    def __init__(self, config_file=None, net_file=None, route_file=None):
        """
        Initialize dual simulation manager
        
        Args:
            config_file (str): SUMO config file path (preferred)
            net_file (str): Network file (if not using config)
            route_file (str): Route file (if not using config)
        """
        self.config_file = config_file
        self.net_file = net_file
        self.route_file = route_file
        
        # Two controllers - different ports
        self.baseline_controller = None
        self.rl_controller = None
        
        self.is_running = False
        self.step_count = 0
        
        # Control mode for RL simulation
        self.rl_mode = 'fixed'  # 'fixed', 'manual', or 'rl'
        
    def start(self):
        """Start both SUMO simulations"""
        if self.is_running:
            raise Exception("Simulations already running")
        
        print("\n🚀 Starting Dual Simulation Manager...")
        print("=" * 60)
        
        # Create baseline controller (port 8813)
        if self.config_file:
            self.baseline_controller = SumoController(
                config_file=self.config_file,
                port=8813,
                gui=False
            )
        else:
            self.baseline_controller = SumoController(
                net_file=self.net_file,
                route_file=self.route_file,
                port=8813,
                gui=False
            )
        
        # Create RL controller (port 8814)
        if self.config_file:
            self.rl_controller = SumoController(
                config_file=self.config_file,
                port=8814,
                gui=False
            )
        else:
            self.rl_controller = SumoController(
                net_file=self.net_file,
                route_file=self.route_file,
                port=8814,
                gui=False
            )
        
        # Start both
        print("\n📌 Starting baseline simulation (fixed-time control)...")
        self.baseline_controller.start()
        
        print("\n📌 Starting RL simulation (adaptive control)...")
        self.rl_controller.start()
        
        self.is_running = True
        self.step_count = 0
        
        print("\n✅ Both simulations started successfully!")
        print("=" * 60)
    
    def step(self):
        """
        Step both simulations in sync
        
        Returns:
            tuple: (baseline_state, rl_state)
        """
        if not self.is_running:
            raise Exception("Simulations not running. Call start() first.")
        
        # Step both simulations
        self.baseline_controller.step()
        self.rl_controller.step()
        
        # Check synchronization
        baseline_time = self.baseline_controller.get_state()['time']
        rl_time = self.rl_controller.get_state()['time']
        
        time_diff = abs(baseline_time - rl_time)
        
        if time_diff > 0.1:  # More than 100ms difference
            print(f"⚠️  WARNING: Simulations desynchronized!")
            print(f"   Baseline: {baseline_time:.2f}s, RL: {rl_time:.2f}s")
            print(f"   Difference: {time_diff:.3f}s")
            
            # Resync by stepping the slower one
            if baseline_time < rl_time:
                print("   Catching up baseline...")
                while self.baseline_controller.get_state()['time'] < rl_time:
                    self.baseline_controller.step()
            else:
                print("   Catching up RL...")
                while self.rl_controller.get_state()['time'] < baseline_time:
                    self.rl_controller.step()
        
        # Get states from both
        baseline_state = self.baseline_controller.get_state()
        rl_state = self.rl_controller.get_state()
        
        self.step_count += 1
        
        return baseline_state, rl_state
    
    def get_detailed_states(self):
        """
        Get detailed states from both simulations
        
        Returns:
            tuple: (baseline_detailed_state, rl_detailed_state)
        """
        if not self.is_running:
            raise Exception("Simulations not running")
        
        baseline_state = self.baseline_controller.get_detailed_state()
        rl_state = self.rl_controller.get_detailed_state()
        
        return baseline_state, rl_state
    
    def get_traffic_metrics(self):
        """
        Compute traffic metrics for both simulations
        
        Returns:
            dict: Metrics for both simulations
        """
        if not self.is_running:
            raise Exception("Simulations not running")
        
        # Get detailed states
        baseline_state = self.baseline_controller.get_detailed_state()
        rl_state = self.rl_controller.get_detailed_state()
        
        # Compute metrics for baseline
        baseline_metrics = self._compute_metrics(baseline_state)
        
        # Compute metrics for RL
        rl_metrics = self._compute_metrics(rl_state)
        
        return {
            'baseline': baseline_metrics,
            'rl': rl_metrics,
            'comparison': {
                'waiting_time_improvement': (
                    (baseline_metrics['avg_waiting_time'] - rl_metrics['avg_waiting_time']) 
                    / baseline_metrics['avg_waiting_time'] * 100
                    if baseline_metrics['avg_waiting_time'] > 0 else 0
                ),
                'speed_improvement': (
                    (rl_metrics['avg_speed'] - baseline_metrics['avg_speed']) 
                    / baseline_metrics['avg_speed'] * 100
                    if baseline_metrics['avg_speed'] > 0 else 0
                )
            }
        }
    
    def _compute_metrics(self, state):
        """
        Compute traffic metrics from state
        
        Args:
            state (dict): Detailed state from controller
            
        Returns:
            dict: Computed metrics
        """
        vehicles = state['vehicles']
        
        if not vehicles:
            return {
                'vehicle_count': 0,
                'avg_speed': 0,
                'avg_waiting_time': 0,
                'total_waiting_time': 0,
                'stopped_vehicles': 0
            }
        
        total_speed = 0
        total_waiting_time = 0
        stopped_count = 0
        
        for vid, vdata in vehicles.items():
            total_speed += vdata['speed']
            total_waiting_time += vdata['waiting_time']
            
            if vdata['speed'] < 0.1:  # Vehicle is stopped
                stopped_count += 1
        
        vehicle_count = len(vehicles)
        
        return {
            'vehicle_count': vehicle_count,
            'avg_speed': total_speed / vehicle_count,
            'avg_waiting_time': total_waiting_time / vehicle_count,
            'total_waiting_time': total_waiting_time,
            'stopped_vehicles': stopped_count,
            'stopped_percentage': (stopped_count / vehicle_count * 100) if vehicle_count > 0 else 0
        }
    
    def set_rl_mode(self, mode):
        """
        Set control mode for RL simulation
        
        Args:
            mode (str): 'fixed', 'manual', or 'rl'
        """
        valid_modes = ['fixed', 'manual', 'rl']
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode. Must be one of: {valid_modes}")
        
        self.rl_mode = mode
        print(f"✅ RL simulation mode set to: {mode}")
    
    def apply_manual_control(self, tls_id, phase):
        """
        Apply manual control to RL simulation
        
        Args:
            tls_id (str): Traffic light ID
            phase (int): Phase index
        """
        if not self.is_running:
            raise Exception("Simulations not running")
        
        if self.rl_mode != 'manual':
            print("⚠️  Warning: RL mode is not 'manual'")
        
        self.rl_controller.set_traffic_light_phase(tls_id, phase)
    
    def stop(self):
        """Stop both simulations"""
        if not self.is_running:
            return
        
        print("\n🛑 Stopping simulations...")
        
        if self.baseline_controller:
            self.baseline_controller.close()
        
        if self.rl_controller:
            self.rl_controller.close()
        
        self.is_running = False
        
        print("✅ Both simulations stopped")
    
    def get_sync_status(self):
        """
        Check if both simulations are synchronized
        
        Returns:
            dict: Synchronization status
        """
        if not self.is_running:
            return {'synchronized': False, 'reason': 'Not running'}
        
        baseline_time = self.baseline_controller.get_state()['time']
        rl_time = self.rl_controller.get_state()['time']
        
        time_diff = abs(baseline_time - rl_time)
        
        return {
            'synchronized': time_diff < 0.1,
            'baseline_time': baseline_time,
            'rl_time': rl_time,
            'time_difference': time_diff
        }
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.is_running:
            try:
                self.stop()
            except:
                pass