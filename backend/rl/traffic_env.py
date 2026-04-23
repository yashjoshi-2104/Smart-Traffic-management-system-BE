"""
TrafficEnv - Gym Environment for Traffic Signal Control with DDQN

State Space (14 values):
- Queue lengths (N, S, E, W) = 4 values
- Average waiting times (N, S, E, W) = 4 values
- Average speeds (N, S, E, W) = 4 values
- Current phase (0-3) = 1 value
- Time in phase = 1 value

Action Space (4 actions):
- 0: Phase 0 (N/S Green, E/W Red)
- 1: Phase 1 (N/S Yellow, E/W Red)
- 2: Phase 2 (E/W Green, N/S Red)
- 3: Phase 3 (E/W Yellow, N/S Red)

Reward:
Complex reward = -waiting_time - (0.1 × queue_length) + (0.5 × throughput) - (1.0 × phase_change_penalty)
"""

import gym
from gym import spaces
import numpy as np
from typing import Dict, Tuple, Any


class TrafficEnv(gym.Env):
    """
    Gym environment for traffic signal control using SUMO
    """
    
    def __init__(self, sumo_controller, tls_id="center"):
        """
        Initialize the traffic environment
        
        Args:
            sumo_controller: Instance of SumoController
            tls_id: Traffic light system ID (default: "center")
        """
        super(TrafficEnv, self).__init__()
        
        self.sumo = sumo_controller
        self.tls_id = tls_id
        
        # Edge IDs for state extraction
        self.edges = {
            'north': 'north_in',
            'south': 'south_in',
            'east': 'east_in',
            'west': 'west_in'
        }
        
        # Lane IDs for queue detection (SUMO naming: edge_id + "_0" for lane index)
        self.lanes = {
            'north': 'north_in_0',
            'south': 'south_in_0',
            'east': 'east_in_0',
            'west': 'west_in_0'
        }
        
        # Define action and observation spaces
        self.action_space = spaces.Discrete(4)  # 4 phases (0, 1, 2, 3)
        
        # State: 14 values (all normalized to roughly 0-1 range)
        # [queue_N, queue_S, queue_E, queue_W,
        #  wait_N, wait_S, wait_E, wait_W,
        #  speed_N, speed_S, speed_E, speed_W,
        #  phase, time_in_phase]
        self.observation_space = spaces.Box(
            low=0, 
            high=100,  # We'll normalize later
            shape=(14,), 
            dtype=np.float32
        )
        
        # State variables
        self.current_phase = 0
        self.time_in_phase = 0
        self.last_action = 0
        self.step_count = 0
        self.episode_count = 0
        
        # For reward calculation
        self.last_total_waiting_time = 0
        self.last_vehicles_passed = 0
        
        # Normalization constants (adjust based on your traffic)
        self.MAX_QUEUE = 20  # Max expected queue length
        self.MAX_WAIT = 60   # Max expected waiting time (seconds)
        self.MAX_SPEED = 15  # Max speed in m/s
        self.MAX_TIME_IN_PHASE = 60  # Max time in one phase
        
        # Reward weights (from your specification)
        self.WAIT_WEIGHT = -1.0
        self.QUEUE_WEIGHT = -0.1
        self.THROUGHPUT_WEIGHT = 0.5
        self.PHASE_CHANGE_PENALTY = -1.0
        
    def reset(self) -> np.ndarray:
        """
        Reset the environment to initial state
        
        Returns:
            Initial state observation
        """
        # Reset internal variables
        self.current_phase = 0
        self.time_in_phase = 0
        self.last_action = 0
        self.step_count = 0
        self.episode_count += 1
        
        # Set initial phase
        if self.sumo.is_running:
            self.sumo.set_traffic_light_phase(self.tls_id, self.current_phase)
        
        # Initialize reward tracking
        self.last_total_waiting_time = self._get_total_waiting_time()
        self.last_vehicles_passed = self._get_vehicles_passed()
        
        # Get initial state
        state = self._get_state()
        
        return state
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment
        
        Args:
            action: Action to take (0-3 for phases)
            
        Returns:
            observation: Next state
            reward: Reward for this step
            done: Whether episode is finished
            info: Additional information
        """
        # Apply action (change phase)
        phase_changed = (action != self.current_phase)
        self.current_phase = action
        self.sumo.set_traffic_light_phase(self.tls_id, self.current_phase)
        
        # Step the simulation
        self.sumo.step()
        self.step_count += 1
        self.time_in_phase += 1
        
        # Reset time in phase if phase changed
        if phase_changed:
            self.time_in_phase = 0
        
        # Get next state
        next_state = self._get_state()
        
        # Calculate reward
        reward = self._calculate_reward(phase_changed)
        
        # Check if episode is done (we'll control this externally)
        done = False  # Infinite episode, controlled by training script
        
        # Additional info for debugging/logging
        info = {
            'step': self.step_count,
            'phase': self.current_phase,
            'time_in_phase': self.time_in_phase,
            'total_waiting_time': self._get_total_waiting_time(),
            'vehicles_passed': self._get_vehicles_passed(),
            'phase_changed': phase_changed
        }
        
        # Update tracking variables
        self.last_action = action
        
        return next_state, reward, done, info
    
    def _get_state(self) -> np.ndarray:
        """
        Extract current state from SUMO simulation
        
        Returns:
            State vector (14 values, normalized)
        """
        # Extract queue lengths per direction
        queue_north = self._get_queue_length('north')
        queue_south = self._get_queue_length('south')
        queue_east = self._get_queue_length('east')
        queue_west = self._get_queue_length('west')
        
        # Extract average waiting times per direction
        wait_north = self._get_avg_waiting_time('north')
        wait_south = self._get_avg_waiting_time('south')
        wait_east = self._get_avg_waiting_time('east')
        wait_west = self._get_avg_waiting_time('west')
        
        # Extract average speeds per direction
        speed_north = self._get_avg_speed('north')
        speed_south = self._get_avg_speed('south')
        speed_east = self._get_avg_speed('east')
        speed_west = self._get_avg_speed('west')
        
        # Normalize values to roughly 0-1 range
        state = np.array([
            queue_north / self.MAX_QUEUE,
            queue_south / self.MAX_QUEUE,
            queue_east / self.MAX_QUEUE,
            queue_west / self.MAX_QUEUE,
            
            wait_north / self.MAX_WAIT,
            wait_south / self.MAX_WAIT,
            wait_east / self.MAX_WAIT,
            wait_west / self.MAX_WAIT,
            
            speed_north / self.MAX_SPEED,
            speed_south / self.MAX_SPEED,
            speed_east / self.MAX_SPEED,
            speed_west / self.MAX_SPEED,
            
            self.current_phase / 3.0,  # Normalize 0-3 to 0-1
            self.time_in_phase / self.MAX_TIME_IN_PHASE
        ], dtype=np.float32)
        
        # Clip to ensure values stay in valid range
        state = np.clip(state, 0, 1)
        
        return state
    
    def _calculate_reward(self, phase_changed: bool) -> float:
        """
        Calculate reward based on current traffic state
        
        Complex reward = -waiting_time - (0.1 × queue_length) + (0.5 × throughput) - (1.0 × phase_change)
        
        Args:
            phase_changed: Whether phase was changed this step
            
        Returns:
            Reward value (higher is better)
        """
        # Component 1: Waiting time penalty (lower is better)
        current_waiting_time = self._get_total_waiting_time()
        wait_penalty = self.WAIT_WEIGHT * current_waiting_time
        
        # Component 2: Queue length penalty (lower is better)
        total_queue = sum([
            self._get_queue_length('north'),
            self._get_queue_length('south'),
            self._get_queue_length('east'),
            self._get_queue_length('west')
        ])
        queue_penalty = self.QUEUE_WEIGHT * total_queue
        
        # Component 3: Throughput reward (higher is better)
        current_vehicles_passed = self._get_vehicles_passed()
        vehicles_passed_this_step = current_vehicles_passed - self.last_vehicles_passed
        throughput_reward = self.THROUGHPUT_WEIGHT * vehicles_passed_this_step
        
        # Component 4: Phase change penalty (discourage too-frequent changes)
        phase_change_penalty = self.PHASE_CHANGE_PENALTY if phase_changed else 0.0
        
        # Total reward
        total_reward = (
            wait_penalty + 
            queue_penalty + 
            throughput_reward + 
            phase_change_penalty
        )
        
        # Update tracking
        self.last_total_waiting_time = current_waiting_time
        self.last_vehicles_passed = current_vehicles_passed
        
        return total_reward
    
    # Helper methods for state extraction
    
    def _get_queue_length(self, direction: str) -> int:
        """Get queue length for a specific direction"""
        try:
            lane_id = self.lanes[direction]
            return self.sumo.get_lane_queue_length(lane_id)
        except:
            return 0
    
    def _get_avg_waiting_time(self, direction: str) -> float:
        """Get average waiting time for a specific direction"""
        try:
            edge_id = self.edges[direction]
            return self.sumo.get_average_waiting_time_by_edge(edge_id)
        except:
            return 0.0
    
    def _get_avg_speed(self, direction: str) -> float:
        """Get average speed for a specific direction"""
        try:
            edge_id = self.edges[direction]
            return self.sumo.get_average_speed_by_edge(edge_id)
        except:
            return 0.0
    
    def _get_total_waiting_time(self) -> float:
        """Get total waiting time across all vehicles"""
        try:
            return self.sumo.get_total_waiting_time()
        except:
            return 0.0
    
    def _get_vehicles_passed(self) -> int:
        """Get number of vehicles that completed their journey"""
        try:
            return self.sumo.get_total_vehicles_passed()
        except:
            return 0
    
    def render(self, mode='human'):
        """
        Render the environment (optional)
        For SUMO, this is handled by SUMO-GUI
        """
        pass
    
    def close(self):
        """
        Clean up resources
        """
        if self.sumo and self.sumo.is_running:
            self.sumo.close()