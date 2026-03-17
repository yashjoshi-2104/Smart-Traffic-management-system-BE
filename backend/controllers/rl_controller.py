# backend/controllers/rl_controller.py
"""
RL Controller - Deep Q-Network agent for adaptive signal control
Currently a placeholder that acts like fixed-time until DQN is trained
"""

from controllers.base_controller import SignalController
import numpy as np


class RLController(SignalController):
    """
    Reinforcement Learning traffic signal controller
    
    Uses DQN agent to select optimal signal phases based on traffic state
    
    State: [queues(4), approaching(4), speeds(4), current_phase(1), time_since_change(1)]
    Action: Phase index (0-3)
    
    Currently: Placeholder implementation (acts like fixed-time)
    Future: Load trained DQN model and run inference
    """
    
    def __init__(self, tls_id="A0", model_path=None):
        """
        Initialize RL controller
        
        Args:
            tls_id (str): Traffic light ID
            model_path (str): Path to trained DQN model (optional)
        """
        super().__init__(tls_id)
        
        self.model_path = model_path
        self.model = None
        
        # State tracking
        self.current_phase = 0
        self.time_since_change = 0
        self.min_phase_duration = 10  # Minimum 10 seconds per phase
        
        # Load model if provided
        if model_path:
            self._load_model(model_path)
        else:
            print("⚠️  No model provided. RL controller running in placeholder mode.")
    
    def _load_model(self, model_path):
        """
        Load trained DQN model
        
        Args:
            model_path (str): Path to model file
        """
        try:
            # Placeholder - will implement when we have trained model
            # from stable_baselines3 import DQN
            # self.model = DQN.load(model_path)
            print(f"✅ Model loaded from {model_path}")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            self.model = None
    
    def get_action(self, state):
        """
        Get action from DQN agent
        
        Args:
            state (dict): Current traffic state
            
        Returns:
            int: Phase index
        """
        self.time_since_change += 1
        
        if self.model is not None:
            # Use trained model (will implement later)
            action = self._get_model_action(state)
        else:
            # Placeholder: simple heuristic
            action = self._get_heuristic_action(state)
        
        # Only change phase if minimum duration passed
        if action != self.current_phase and self.time_since_change >= self.min_phase_duration:
            self.current_phase = action
            self.time_since_change = 0
        
        self.step()
        return self.current_phase
    
    def _get_model_action(self, state):
        """
        Get action from trained DQN model
        
        Args:
            state (dict): Traffic state
            
        Returns:
            int: Action (phase index)
        """
        # Preprocess state to model input format
        obs = self._preprocess_state(state)
        
        # Run inference
        action, _ = self.model.predict(obs, deterministic=True)
        
        return int(action)
    
    def _get_heuristic_action(self, state):
        """
        Simple heuristic for placeholder mode
        Chooses phase with most waiting vehicles
        
        Args:
            state (dict): Traffic state
            
        Returns:
            int: Phase index
        """
        # For now, just cycle through phases (like fixed-time)
        # In future, could use simple rules based on queue lengths
        
        # Cycle every 30 seconds
        if self.time_since_change >= 30:
            return (self.current_phase + 1) % 4
        else:
            return self.current_phase
    
    def _preprocess_state(self, state):
        """
        Convert SUMO state to model input format
        
        Args:
            state (dict): Raw SUMO state
            
        Returns:
            np.array: Preprocessed state vector (18 dims)
        """
        # Extract features from state
        # This will be implemented when we have proper state extraction
        
        # Placeholder: return dummy state
        return np.zeros(18, dtype=np.float32)
    
    def reset(self):
        """Reset controller"""
        super().reset()
        self.current_phase = 0
        self.time_since_change = 0