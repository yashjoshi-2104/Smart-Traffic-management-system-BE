# backend/controllers/manual_controller.py
"""
Manual Controller - User controls signal phases via UI
"""

from controllers.base_controller import SignalController


class ManualController(SignalController):
    """
    Manual traffic signal controller
    
    Allows user to set signal phases directly via API calls
    Default behavior: maintains current phase until changed
    """
    
    def __init__(self, tls_id="A0", initial_phase=0):
        """
        Initialize manual controller
        
        Args:
            tls_id (str): Traffic light ID
            initial_phase (int): Starting phase (default: 0)
        """
        super().__init__(tls_id)
        
        self.current_phase = initial_phase
        self.phase_history = []
    
    def get_action(self, state):
        """
        Return current manually-set phase
        
        Args:
            state (dict): Current traffic state (not used)
            
        Returns:
            int: Current phase index
        """
        self.step()
        return self.current_phase
    
    def set_phase(self, phase):
        """
        Manually set signal phase (called by API)
        
        Args:
            phase (int): Phase index to set
        """
        if phase < 0 or phase > 3:
            raise ValueError(f"Invalid phase {phase}. Must be 0-3.")
        
        old_phase = self.current_phase
        self.current_phase = phase
        
        # Record phase change
        self.phase_history.append({
            'step': self.step_count,
            'from_phase': old_phase,
            'to_phase': phase
        })
        
        print(f"🔧 Manual override: Phase {old_phase} → {phase}")
    
    def extend_phase(self, duration):
        """
        Extend current phase by duration (placeholder for future)
        
        Args:
            duration (int): Seconds to extend
        """
        print(f"⏱️  Extending phase {self.current_phase} by {duration}s")
        # This would be implemented with timing logic in future
    
    def reset(self):
        """Reset controller"""
        super().reset()
        self.current_phase = 0
        self.phase_history = []
    
    def get_phase_history(self):
        """
        Get history of manual phase changes
        
        Returns:
            list: Phase change history
        """
        return self.phase_history