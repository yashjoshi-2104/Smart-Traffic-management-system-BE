"""
Fixed-Time Controller - Traditional traffic signal timing
"""


class FixedTimeController:
    """
    Fixed-time traffic signal controller.
    Cycles through phases with predetermined durations.
    Supports custom phase cycles for networks with more than 4 phases (e.g. urban arterial B1).
    """

    def __init__(self, tls_id, green_time=30, yellow_time=3, cycle=None):
        """
        Initialize fixed-time controller.

        Args:
            tls_id:     Traffic light system ID
            green_time: Default green phase duration (seconds) — used only if cycle=None
            yellow_time:Default yellow phase duration (seconds) — used only if cycle=None
            cycle:      Optional list of (phase_index, duration) tuples.
                        If None, defaults to simple 4-phase N/S + E/W cycle.
        """
        self.tls_id      = tls_id
        self.green_time  = green_time
        self.yellow_time = yellow_time

        # Use provided cycle or fall back to simple 4-phase default
        self.cycle = cycle if cycle else [
            (0, green_time),    # N/S Green
            (1, yellow_time),   # N/S Yellow
            (2, green_time),    # E/W Green
            (3, yellow_time),   # E/W Yellow
        ]

        self.current_phase = self.cycle[0][0]
        self.time_in_phase = 0
        self.cycle_index   = 0

    def get_action(self):
        """
        Get next phase based on fixed timing.

        Returns:
            Phase index to apply to SUMO
        """
        phase, duration = self.cycle[self.cycle_index]
        self.time_in_phase += 1

        if self.time_in_phase >= duration:
            self.cycle_index   = (self.cycle_index + 1) % len(self.cycle)
            self.time_in_phase = 0
            phase, _           = self.cycle[self.cycle_index]

        self.current_phase = phase
        return phase

    def reset(self):
        self.current_phase = self.cycle[0][0]
        self.time_in_phase = 0
        self.cycle_index   = 0

    def get_traffic_light_ids(self):
        return [self.tls_id]

    def get_traffic_light_phase(self, tls_id):
        return self.current_phase