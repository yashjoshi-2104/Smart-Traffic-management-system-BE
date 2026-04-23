"""
Manual Controller - User-controlled traffic signals
"""


class ManualController:
    """
    Manual traffic signal controller
    Phase is set externally by user input
    """
    
    def __init__(self, tls_id):
        """
        Initialize manual controller
        
        Args:
            tls_id: Traffic light system ID
        """
        self.tls_id = tls_id
        self.current_phase = 0
    
    def get_action(self):
        """
        Get current phase (set by user)
        
        Returns:
            Current phase (0-3)
        """
        return self.current_phase
    
    def set_phase(self, phase):
        """
        Set phase manually
        
        Args:
            phase: Phase to set (0-3)
        """
        if 0 <= phase <= 3:
            self.current_phase = phase
        else:
            raise ValueError(f"Invalid phase: {phase}. Must be 0-3")
    
    def get_traffic_light_ids(self):
        """Return list of traffic light IDs"""
        return [self.tls_id] 
    
    def get_traffic_light_phase(self, tls_id):
        """Get current phase"""
        return self.current_phase   