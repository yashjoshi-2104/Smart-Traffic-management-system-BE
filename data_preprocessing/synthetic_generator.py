# data_preprocessing/synthetic_generator.py
"""
Generate synthetic traffic patterns based on NGSIM statistics
For testing when real data isn't available or needs augmentation
"""

import random
import numpy as np


def generate_realistic_traffic(
    duration=300,
    flow_rate=0.3,  # vehicles per second
    output_file="../data/processed/synthetic_realistic.rou.xml"
):
    """
    Generate synthetic traffic with realistic patterns
    
    Args:
        duration: Simulation duration in seconds
        flow_rate: Average vehicles per second
        output_file: Output route file
    """
    print(f"🏭 Generating synthetic traffic...")
    print(f"   Duration: {duration}s")
    print(f"   Flow rate: {flow_rate} veh/s ({flow_rate*3600:.0f} veh/hour)")
    
    # Vehicle type distribution (from NGSIM)
    vehicle_types = [
        ('passenger', 0.85),  # 85% cars
        ('truck', 0.12),      # 12% trucks
        ('motorcycle', 0.03)  # 3% motorcycles
    ]
    
    vehicles = []
    current_time = 0
    vid = 0
    
    while current_time < duration:
        # Poisson arrival process
        inter_arrival = np.random.exponential(1.0 / flow_rate)
        current_time += inter_arrival
        
        if current_time >= duration:
            break
        
        # Select vehicle type
        rand = random.random()
        cumulative = 0
        vtype = 'passenger'
        
        for vt, prob in vehicle_types:
            cumulative += prob
            if rand <= cumulative:
                vtype = vt
                break
        
        vehicles.append({
            'id': vid,
            'type': vtype,
            'depart': current_time
        })
        
        vid += 1
    
    # Write route file
    with open(output_file, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<routes>\n\n')
        
        # Vehicle types
        f.write('    <vType id="passenger" accel="2.6" decel="4.5" sigma="0.5" ')
        f.write('length="5.0" maxSpeed="30.0"/>\n')
        f.write('    <vType id="truck" accel="1.3" decel="4.0" sigma="0.5" ')
        f.write('length="12.0" maxSpeed="25.0"/>\n')
        f.write('    <vType id="motorcycle" accel="3.0" decel="5.0" sigma="0.3" ')
        f.write('length="2.5" maxSpeed="40.0"/>\n\n')
        
        # Routes
        f.write('    <route id="route_ns" edges="north_in south_out"/>\n')
        f.write('    <route id="route_ew" edges="east_in west_out"/>\n\n')
        
        # Vehicles
        for v in vehicles:
            route = 'route_ns' if random.random() < 0.5 else 'route_ew'
            f.write(f'    <vehicle id="v_{v["id"]}" type="{v["type"]}" ')
            f.write(f'route="{route}" depart="{v["depart"]:.2f}"/>\n')
        
        f.write('\n</routes>\n')
    
    print(f"✅ Generated {len(vehicles)} vehicles")
    print(f"   Output: {output_file}")
    
    return vehicles


if __name__ == "__main__":
    generate_realistic_traffic(duration=300, flow_rate=0.5)