# backend/controllers/base_controller.py
"""
Base controller class - defines interface for all signal controllers
"""

from abc import ABC, abstractmethod


class SignalController(ABC):
    """
    Abstract base class for traffic signal controllers
    
    All controllers must implement get_action() method
    """
    
    def __init__(self, tls_id="A0"):
        """
        Initialize controller
        
        Args:
            tls_id (str): Traffic light ID to control
        """
        self.tls_id = tls_id
        self.step_count = 0
    
    @abstractmethod
    def get_action(self, state):
        """
        Decide which signal phase to activate
        
        Args:
            state (dict): Current traffic state from SUMO
            
        Returns:
            int: Phase index (0, 1, 2, 3, etc.)
        """
        pass
    
    def reset(self):
        """Reset controller state"""
        self.step_count = 0
    
    def step(self):
        """Increment step counter"""
        self.step_count += 1