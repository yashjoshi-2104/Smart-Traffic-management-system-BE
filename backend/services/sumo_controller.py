# backend/services/sumo_controller.py
"""
SumoController - Wrapper for controlling a single SUMO simulation instance
Provides high-level interface for starting, stepping, and querying SUMO via TraCI
"""

import os
import sys
import traci

# Add SUMO tools to path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)


class SumoController:
    """
    Controls a single SUMO simulation instance via TraCI
    
    Usage:
        # Option 1: Using config file (recommended)
        controller = SumoController(config_file="path/to/config.sumocfg")
        
        # Option 2: Using network + routes directly
        controller = SumoController(net_file="path/to/network.net.xml",
                                    route_file="path/to/routes.rou.xml")
        
        controller.start()
        
        for i in range(100):
            controller.step()
            state = controller.get_state()
            # Do something with state
        
        controller.close()
    """
    
    def __init__(self, config_file=None, net_file=None, route_file=None, port=8813, gui=False):
        """
        Initialize SUMO controller
        
        Args:
            config_file (str): Path to SUMO config file (.sumocfg) - preferred method
            net_file (str): Path to SUMO network file (.net.xml) - only if no config
            route_file (str): Path to route file (.rou.xml) - only if no config
            port (int): TraCI port (use different ports for multiple instances)
            gui (bool): Whether to show SUMO GUI (False = headless)
        """
        self.config_file = config_file
        self.net_file = net_file
        self.route_file = route_file
        self.port = port
        self.gui = gui
        
        self.is_running = False
        self.step_count = 0
        self.conn = None
        self.label = f"sim_{port}"
        
        # Validate inputs
        if not config_file and not (net_file and route_file):
            raise ValueError("Must provide either config_file OR (net_file AND route_file)")
        
    def start(self):
        """Start SUMO simulation"""
        if self.is_running:
            raise Exception("Simulation already running")
        
        # Choose binary (sumo-gui or sumo)
        sumo_binary = "sumo-gui" if self.gui else "sumo"
        
        # Build SUMO command
        if self.config_file:
            # Use config file (preferred - includes vehicle types, additional files, etc.)
            sumo_cmd = [
                sumo_binary,
                "-c", self.config_file,
                "--time-to-teleport", "-1",
                "--waiting-time-memory", "1000"
            ]
        else:
            # Use network + route files directly
            sumo_cmd = [
                sumo_binary,
                "-n", self.net_file,
                "-r", self.route_file,
                "--no-warnings",
                "--no-step-log",
                "--time-to-teleport", "-1",
                "--waiting-time-memory", "1000"
            ]
        
        # Start SUMO - port specified in traci.start(), not in sumo_cmd
        traci.start(sumo_cmd, port=self.port, label=self.label)
        self.conn = traci.getConnection(self.label)
        self.is_running = True
        self.step_count = 0
        
        print(f"✅ SUMO started on port {self.port} (label: {self.label})")
    
    def step(self):
        """Advance simulation by one time step (1 second)"""
        if not self.is_running:
            raise Exception("Simulation not running. Call start() first.")
        
        self.conn.simulationStep()
        self.step_count += 1
    
    def get_state(self):
        """
        Extract current traffic state
        
        Returns:
            dict: Current state including time, vehicles, etc.
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        vehicle_ids = self.conn.vehicle.getIDList()
        
        state = {
            'time': self.conn.simulation.getTime(),
            'step': self.step_count,
            'vehicle_count': len(vehicle_ids),
            'vehicles': list(vehicle_ids)
        }
        
        return state
    
    def get_detailed_state(self):
        """
        Extract detailed traffic state including vehicle positions, speeds, etc.
        
        Returns:
            dict: Detailed state with per-vehicle information
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        vehicle_ids = self.conn.vehicle.getIDList()
        
        # Get detailed info for each vehicle
        vehicles_detail = {}
        for vid in vehicle_ids:
            vehicles_detail[vid] = {
                'speed': self.conn.vehicle.getSpeed(vid),
                'position': self.conn.vehicle.getPosition(vid),
                'lane': self.conn.vehicle.getLaneID(vid),
                'waiting_time': self.conn.vehicle.getWaitingTime(vid)
            }
        
        state = {
            'time': self.conn.simulation.getTime(),
            'step': self.step_count,
            'vehicle_count': len(vehicle_ids),
            'vehicles': vehicles_detail
        }
        
        return state
    
    def get_traffic_light_ids(self):
        """
        Get list of traffic light IDs in the simulation
        
        Returns:
            list: Traffic light IDs
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        return list(self.conn.trafficlight.getIDList())
    
    def get_traffic_light_phase(self, tls_id):
        """
        Get current phase of a traffic light
        
        Args:
            tls_id (str): Traffic light ID
            
        Returns:
            int: Current phase index
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        return self.conn.trafficlight.getPhase(tls_id)
    
    def set_traffic_light_phase(self, tls_id, phase_index):
        """
        Set traffic light phase
        
        Args:
            tls_id (str): Traffic light ID
            phase_index (int): Phase index to set (0, 1, 2, 3, etc.)
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        self.conn.trafficlight.setPhase(tls_id, phase_index)
    
    def get_traffic_light_state(self, tls_id):
        """
        Get traffic light state string (e.g., 'GGGGrrrr')
        
        Args:
            tls_id (str): Traffic light ID
            
        Returns:
            str: State string (G=green, r=red, y=yellow)
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        return self.conn.trafficlight.getRedYellowGreenState(tls_id)
    
    def get_edge_vehicle_count(self, edge_id):
        """
        Get number of vehicles on a specific edge
        
        Args:
            edge_id (str): Edge ID
            
        Returns:
            int: Number of vehicles
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        return self.conn.edge.getLastStepVehicleNumber(edge_id)
    
    def get_lane_queue_length(self, lane_id):
        """
        Get queue length on a lane (vehicles stopped or very slow)
        
        Args:
            lane_id (str): Lane ID
            
        Returns:
            int: Number of halting vehicles
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        return self.conn.lane.getLastStepHaltingNumber(lane_id)
    
    def close(self):
        """Stop and close SUMO simulation"""
        if self.is_running:
            self.conn.close()
            self.is_running = False
            self.conn = None
            print(f"✅ SUMO stopped (port {self.port})")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.is_running:
            try:
                self.close()
            except:
                pass