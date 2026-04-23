"""
RL Controller using trained DDQN agent
"""

import os
import numpy as np
import torch
from rl.ddqn_agent import DQN


class RLController:
    def __init__(self, tls_id, model_path=None):
        """
        Initialize RL Controller
        
        Args:
            tls_id: Traffic light system ID
            model_path: Path to trained model (optional)
        """
        self.tls_id = tls_id
        self.state_dim = 14
        self.action_dim = 4
        self.current_phase = 0
        self.time_in_phase = 0
        
        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model
        self.model = DQN(self.state_dim, self.action_dim).to(self.device)
        if model_path and os.path.exists(model_path):
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['policy_net_state_dict'])
            self.model.eval()
            print(f"✅ RL model loaded from {model_path}")
            self.has_model = True
        else:
            print(f"⚠️  No model found - using random actions")
            self.has_model = False
        
        # Edge/lane IDs
        self.edges = {
            'north': 'north_in',
            'south': 'south_in',
            'east': 'east_in',
            'west': 'west_in'
        }
        self.lanes = {
            'north': 'north_in_0',
            'south': 'south_in_0',
            'east': 'east_in_0',
            'west': 'west_in_0'
        }
    
    def get_action(self, sumo_controller):
        """
        Get next action from RL agent
        
        Args:
            sumo_controller: SumoController instance
            
        Returns:
            Phase to apply (0-3)
        """
        # Extract state
        state = self._extract_state(sumo_controller)
        
        # Get action from model
        if self.has_model:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                q_values = self.model(state_tensor)
                action = q_values.argmax().item()
        else:
            # Random action if no model
            action = np.random.randint(0, self.action_dim)
        
        # Update tracking
        if action != self.current_phase:
            self.time_in_phase = 0
        else:
            self.time_in_phase += 1
        
        self.current_phase = action
        return action
    
    def _extract_state(self, sumo):
        """Extract 14-value state from SUMO"""
        # Queue lengths
        queue_n = self._get_queue(sumo, 'north')
        queue_s = self._get_queue(sumo, 'south')
        queue_e = self._get_queue(sumo, 'east')
        queue_w = self._get_queue(sumo, 'west')
        
        # Waiting times
        wait_n = self._get_wait(sumo, 'north')
        wait_s = self._get_wait(sumo, 'south')
        wait_e = self._get_wait(sumo, 'east')
        wait_w = self._get_wait(sumo, 'west')
        
        # Speeds
        speed_n = self._get_speed(sumo, 'north')
        speed_s = self._get_speed(sumo, 'south')
        speed_e = self._get_speed(sumo, 'east')
        speed_w = self._get_speed(sumo, 'west')
        
        # Normalize
        state = np.array([
            queue_n / 20.0,
            queue_s / 20.0,
            queue_e / 20.0,
            queue_w / 20.0,
            wait_n / 60.0,
            wait_s / 60.0,
            wait_e / 60.0,
            wait_w / 60.0,
            speed_n / 15.0,
            speed_s / 15.0,
            speed_e / 15.0,
            speed_w / 15.0,
            self.current_phase / 3.0,
            self.time_in_phase / 60.0
        ], dtype=np.float32)
        
        return np.clip(state, 0, 1)
    
    def _get_queue(self, sumo, direction):
        try:
            return sumo.get_lane_queue_length(self.lanes[direction])
        except:
            return 0
    
    def _get_wait(self, sumo, direction):
        try:
            return sumo.get_average_waiting_time_by_edge(self.edges[direction])
        except:
            return 0.0
    
    def _get_speed(self, sumo, direction):
        try:
            return sumo.get_average_speed_by_edge(self.edges[direction])
        except:
            return 0.0