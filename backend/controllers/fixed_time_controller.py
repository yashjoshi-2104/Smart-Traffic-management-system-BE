# backend/controllers/fixed_time_controller.py
"""
Fixed-Time Controller - Traditional traffic signal control
Cycles through phases with predetermined durations
"""

from controllers.base_controller import SignalController


class FixedTimeController(SignalController):
    """
    Fixed-time traffic signal controller
    
    Cycles through signal phases with fixed durations:
    - Phase 0: North-South green (30 seconds)
    - Phase 1: East-West green (30 seconds)
    - Phase 2: North-South left turn (10 seconds)
    - Phase 3: East-West left turn (10 seconds)
    
    Total cycle: 80 seconds
    """
    
    def __init__(self, tls_id="A0", phase_durations=None):
        """
        Initialize fixed-time controller
        
        Args:
            tls_id (str): Traffic light ID
            phase_durations (list): Duration in seconds for each phase
                                   Default: [30, 30, 10, 10]
        """
        super().__init__(tls_id)
        
        # Phase durations (in seconds)
        if phase_durations is None:
            self.phase_durations = [30, 30, 10, 10]  # N-S, E-W, N-S left, E-W left
        else:
            self.phase_durations = phase_durations
        
        # Current phase
        self.current_phase = 0
        self.time_in_phase = 0
        
        # Total phases
        self.num_phases = len(self.phase_durations)
    
    def get_action(self, state):
        """
        Get next signal phase based on fixed timing
        
        Args:
            state (dict): Current traffic state (not used in fixed-time)
            
        Returns:
            int: Phase index
        """
        # Increment time in current phase
        self.time_in_phase += 1
        
        # Check if it's time to switch phase
        if self.time_in_phase >= self.phase_durations[self.current_phase]:
            # Switch to next phase
            self.current_phase = (self.current_phase + 1) % self.num_phases
            self.time_in_phase = 0
        
        self.step()
        
        return self.current_phase
    
    def reset(self):
        """Reset to initial state"""
        super().reset()
        self.current_phase = 0
        self.time_in_phase = 0
    
    def get_phase_info(self):
        """
        Get current phase information
        
        Returns:
            dict: Phase info
        """
        return {
            'current_phase': self.current_phase,
            'time_in_phase': self.time_in_phase,
            'time_remaining': self.phase_durations[self.current_phase] - self.time_in_phase,
            'phase_duration': self.phase_durations[self.current_phase]
        }