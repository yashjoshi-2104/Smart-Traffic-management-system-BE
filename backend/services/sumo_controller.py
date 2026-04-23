# backend/services/sumo_controller.py
"""
SumoController - Wrapper for controlling a single SUMO simulation instance
Provides high-level interface for starting, stepping, and querying SUMO via TraCI
"""

import os
import sys
import subprocess
import time
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
        controller = SumoController(config_file="path/to/config.sumocfg", gui=True)
        
        # Option 2: Using network + routes directly
        controller = SumoController(net_file="path/to/network.net.xml",
                                    route_file="path/to/routes.rou.xml",
                                    gui=False)
        
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
            print(f"⚠️  Simulation already running on port {self.port}")
            return
        
        # Choose SUMO binary
        sumo_binary = "sumo-gui" if self.gui else "sumo"
        
        # Build command
        if self.config_file:
            sumo_cmd = [sumo_binary, "-c", self.config_file, "--remote-port", str(self.port)]
        else:
            sumo_cmd = [
                sumo_binary,
                "--net-file", self.net_file,
                "--route-files", self.route_file,
                "--remote-port", str(self.port)
            ]
        
        # Add GUI-specific options
        if self.gui:
            sumo_cmd.extend([
                "--start",  # Auto-start simulation
                "--quit-on-end",  # Close window when simulation ends
                "--step-length", "0.1",  # Smooth animation
                "--delay", "50",  # Delay between steps (ms) for visibility
            ])
        
        # Start SUMO process
        print(f"🚀 Starting SUMO ({'GUI' if self.gui else 'headless'}) on port {self.port}...")
        subprocess.Popen(sumo_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for SUMO to initialize
        time.sleep(3 if self.gui else 2)
        
        # Connect via TraCI
        try:
            self.conn = traci.connect(self.port)
            self.is_running = True
            print(f"✅ SUMO connected on port {self.port}")
        except Exception as e:
            print(f"❌ Failed to connect to SUMO on port {self.port}: {e}")
            raise
    
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
            veh_type = self.conn.vehicle.getTypeID(vid)
            vehicles_detail[vid] = {
                'speed': self.conn.vehicle.getSpeed(vid),
                'position': self.conn.vehicle.getPosition(vid),
                'lane': self.conn.vehicle.getLaneID(vid),
                'waiting_time': self.conn.vehicle.getWaitingTime(vid),
                'type': veh_type,
                'is_emergency': veh_type == "emergency"
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
    
    def set_manual_control(self, tls_id):
        """
        Enable manual control of traffic light
        Keep the program but allow manual phase setting
        
        Args:
            tls_id (str): Traffic light ID
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        print(f"🚦 Traffic light {tls_id} ready for manual control")
    
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
    
    def get_average_waiting_time_by_edge(self, edge_id):
        """
        Get average waiting time for vehicles on an edge
        
        Args:
            edge_id (str): Edge ID
            
        Returns:
            float: Average waiting time in seconds
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        vehicle_ids = self.conn.edge.getLastStepVehicleIDs(edge_id)
        if not vehicle_ids:
            return 0.0
        
        total_wait = sum(self.conn.vehicle.getWaitingTime(vid) for vid in vehicle_ids)
        return total_wait / len(vehicle_ids)
    
    def get_average_speed_by_edge(self, edge_id):
        """
        Get average speed for vehicles on an edge
        
        Args:
            edge_id (str): Edge ID
            
        Returns:
            float: Average speed in m/s
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        vehicle_ids = self.conn.edge.getLastStepVehicleIDs(edge_id)
        if not vehicle_ids:
            return 0.0
        
        total_speed = sum(self.conn.vehicle.getSpeed(vid) for vid in vehicle_ids)
        return total_speed / len(vehicle_ids)
    
    def get_total_waiting_time(self):
        """
        Get total waiting time across all vehicles
        
        Returns:
            float: Total waiting time in seconds
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        vehicle_ids = self.conn.vehicle.getIDList()
        if not vehicle_ids:
            return 0.0
        
        return sum(self.conn.vehicle.getWaitingTime(vid) for vid in vehicle_ids)
    
    def get_total_vehicles_passed(self):
        """
        Get count of vehicles that have completed their journey
        
        Returns:
            int: Number of vehicles that completed journey
        """
        if not self.is_running:
            raise Exception("Simulation not running")
        
        return self.conn.simulation.getArrivedNumber()     
    
    def get_emergency_vehicles_by_direction(self):
        """
        Count emergency vehicles per direction
        
        Returns:
            dict: Emergency count per direction {"north": 0, "south": 0, "east": 0, "west": 0}
        """
        if not self.is_running:
            return {"north": 0, "south": 0, "east": 0, "west": 0}
        
        emergency_count = {"north": 0, "south": 0, "east": 0, "west": 0}
        
        for veh_id in self.conn.vehicle.getIDList():
            try:
                veh_type = self.conn.vehicle.getTypeID(veh_id)
                if veh_type == "emergency":
                    lane = self.conn.vehicle.getLaneID(veh_id)
                    
                    if "north_in" in lane:
                        emergency_count["north"] += 1
                    elif "south_in" in lane:
                        emergency_count["south"] += 1
                    elif "east_in" in lane:
                        emergency_count["east"] += 1
                    elif "west_in" in lane:
                        emergency_count["west"] += 1
            except:
                continue
        
        return emergency_count
    
    def get_emergency_vehicles(self):
        """
        Get list of all emergency vehicles with their info
        
        Returns:
            list: List of emergency vehicle dicts
        """
        if not self.is_running:
            return []
        
        emergency_vehicles = []
        
        for veh_id in self.conn.vehicle.getIDList():
            try:
                veh_type = self.conn.vehicle.getTypeID(veh_id)
                if veh_type == "emergency":
                    pos = self.conn.vehicle.getPosition(veh_id)
                    emergency_vehicles.append({
                        "id": veh_id,
                        "position": pos,
                        "speed": self.conn.vehicle.getSpeed(veh_id),
                        "lane": self.conn.vehicle.getLaneID(veh_id),
                        "waiting_time": self.conn.vehicle.getWaitingTime(veh_id)
                    })
            except:
                continue
        
        return emergency_vehicles
    
    def has_emergency_vehicles(self):
        """
        Quick check if any emergency vehicles exist in simulation
        
        Returns:
            bool: True if emergency vehicles present
        """
        if not self.is_running:
            return False
        
        for veh_id in self.conn.vehicle.getIDList():
            try:
                if self.conn.vehicle.getTypeID(veh_id) == "emergency":
                    return True
            except:
                continue
        
        return False   
    
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