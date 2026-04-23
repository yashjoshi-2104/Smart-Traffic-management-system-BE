# data_preprocessing/map_to_sumo.py
"""
Convert NGSIM data to SUMO format
Maps real-world coordinates to SUMO network and extracts vehicle journeys
"""

import pandas as pd
import numpy as np
from pathlib import Path


class NGSIMToSUMOConverter:
    """
    Converts NGSIM trajectory data to SUMO route files
    """
    
    def __init__(self, ngsim_csv="../data/processed/ngsim_sample_60s.csv"):
        """
        Initialize converter
        
        Args:
            ngsim_csv: Path to NGSIM data (use sample for faster processing)
        """
        self.ngsim_csv = ngsim_csv
        self.df = None
        self.vehicles = {}
        
    def load_data(self):
        """Load NGSIM sample data"""
        print("📥 Loading NGSIM sample data...")
        self.df = pd.read_csv(self.ngsim_csv)
        print(f"✅ Loaded {len(self.df):,} records")
        print(f"   Vehicles: {self.df['Vehicle_ID'].nunique()}")
        print(f"   Time span: {self.df['Frame_ID'].min()/10:.1f}s - {self.df['Frame_ID'].max()/10:.1f}s")
    
    def convert_units(self):
        """Convert feet to meters"""
        print("\n📏 Converting units (feet → meters)...")
        
        # Position: feet to meters
        self.df['x_m'] = self.df['Local_X'] * 0.3048
        self.df['y_m'] = self.df['Local_Y'] * 0.3048
        
        # Speed: ft/s to m/s
        self.df['speed_ms'] = self.df['v_Vel'] * 0.3048
        
        # Length/Width: feet to meters
        self.df['length_m'] = self.df['v_length'] * 0.3048
        self.df['width_m'] = self.df['v_Width'] * 0.3048
        
        # Time: frame to seconds
        self.df['time_s'] = self.df['Frame_ID'] / 10.0
        
        print("✅ Units converted")
    
    def extract_vehicle_journeys(self):
        """
        Extract individual vehicle journeys
        
        Returns:
            dict: Vehicle journeys {vehicle_id: journey_data}
        """
        print("\n🚗 Extracting vehicle journeys...")
        
        vehicles = {}
        
        for vid in self.df['Vehicle_ID'].unique():
            vehicle_data = self.df[self.df['Vehicle_ID'] == vid].sort_values('Frame_ID')
            
            # Get vehicle characteristics
            vehicle_class = vehicle_data['v_Class'].iloc[0]
            vehicle_type = self._map_vehicle_type(vehicle_class)
            
            # Extract trajectory
            trajectory = vehicle_data[['time_s', 'x_m', 'y_m', 'speed_ms', 'Lane_ID']].values
            
            # Calculate journey stats
            start_time = trajectory[0, 0]
            end_time = trajectory[-1, 0]
            duration = end_time - start_time
            distance = np.sqrt(
                (trajectory[-1, 1] - trajectory[0, 1])**2 +
                (trajectory[-1, 2] - trajectory[0, 2])**2
            )
            
            vehicles[vid] = {
                'id': vid,
                'type': vehicle_type,
                'class': vehicle_class,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'distance': distance,
                'trajectory': trajectory,
                'start_lane': int(trajectory[0, 4]),
                'end_lane': int(trajectory[-1, 4]),
                'avg_speed': vehicle_data['speed_ms'].mean(),
                'max_speed': vehicle_data['speed_ms'].max(),
                'length': vehicle_data['length_m'].mean(),
                'width': vehicle_data['width_m'].mean()
            }
        
        print(f"✅ Extracted {len(vehicles)} vehicle journeys")
        
        self.vehicles = vehicles
        return vehicles
    
    def _map_vehicle_type(self, vehicle_class):
        """Map NGSIM vehicle class to SUMO vehicle type"""
        mapping = {
            1: "motorcycle",
            2: "passenger",
            3: "truck"
        }
        return mapping.get(vehicle_class, "passenger")
    
    def generate_sumo_routes(self, output_file="../data/processed/ngsim_routes.rou.xml"):
        """
        Generate SUMO route file from NGSIM data
        
        Args:
            output_file: Output route file path
        """
        print(f"\n📝 Generating SUMO route file...")
        
        if not self.vehicles:
            self.extract_vehicle_journeys()
        
        # Create route file
        with open(output_file, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
            f.write('xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n\n')
            
            # Define vehicle types
            f.write('    <!-- Vehicle Types -->\n')
            f.write('    <vType id="passenger" accel="2.6" decel="4.5" sigma="0.5" ')
            f.write('length="5.0" minGap="2.5" maxSpeed="33.0" guiShape="passenger"/>\n')
            f.write('    <vType id="truck" accel="1.3" decel="4.0" sigma="0.5" ')
            f.write('length="12.0" minGap="3.0" maxSpeed="25.0" guiShape="truck"/>\n')
            f.write('    <vType id="motorcycle" accel="3.0" decel="5.0" sigma="0.3" ')
            f.write('length="2.5" minGap="1.5" maxSpeed="40.0" guiShape="motorcycle"/>\n\n')
            
            # For simplification, create a simple route
            # (In real implementation, you'd map lanes to actual SUMO network edges)
            f.write('    <!-- Routes -->\n')
            f.write('    <route id="route_0" edges="north_in north_out"/>\n\n')
            
            # Add vehicles
            f.write('    <!-- Vehicles from NGSIM data -->\n')
            
            for vid, vehicle in self.vehicles.items():
                depart = f"{vehicle['start_time']:.2f}"
                vtype = vehicle['type']
                
                # Color based on vehicle class
                colors = {
                    'passenger': '1,0,0',
                    'truck': '0,0,1',
                    'motorcycle': '0,1,0'
                }
                color = colors.get(vtype, '1,1,0')
                
                f.write(f'    <vehicle id="ngsim_{vid}" type="{vtype}" ')
                f.write(f'route="route_0" depart="{depart}" color="{color}"/>\n')
            
            f.write('\n</routes>\n')
        
        print(f"✅ Route file created: {output_file}")
        print(f"   Total vehicles: {len(self.vehicles)}")
        
        return output_file
    
    def generate_statistics_report(self):
        """Generate statistics report"""
        print("\n" + "=" * 70)
        print("📊 CONVERSION STATISTICS")
        print("=" * 70)
        
        if not self.vehicles:
            return
        
        # Vehicle type distribution
        type_counts = {}
        for v in self.vehicles.values():
            vtype = v['type']
            type_counts[vtype] = type_counts.get(vtype, 0) + 1
        
        print("\n🚗 Vehicle Type Distribution:")
        for vtype, count in type_counts.items():
            print(f"   {vtype}: {count} ({count/len(self.vehicles)*100:.1f}%)")
        
        # Journey statistics
        durations = [v['duration'] for v in self.vehicles.values()]
        distances = [v['distance'] for v in self.vehicles.values()]
        speeds = [v['avg_speed'] for v in self.vehicles.values()]
        
        print("\n📏 Journey Statistics:")
        print(f"   Avg Duration: {np.mean(durations):.1f}s")
        print(f"   Avg Distance: {np.mean(distances):.1f}m")
        print(f"   Avg Speed: {np.mean(speeds):.2f} m/s ({np.mean(speeds)*3.6:.1f} km/h)")
        print(f"   Max Speed: {np.max(speeds):.2f} m/s ({np.max(speeds)*3.6:.1f} km/h)")
        
        # Time distribution
        start_times = [v['start_time'] for v in self.vehicles.values()]
        
        print("\n⏰ Temporal Distribution:")
        print(f"   First vehicle: {min(start_times):.1f}s")
        print(f"   Last vehicle: {max(start_times):.1f}s")
        print(f"   Time span: {max(start_times) - min(start_times):.1f}s")


def main():
    """Main conversion pipeline"""
    
    print("🚀 NGSIM to SUMO Conversion Pipeline")
    print("=" * 70)
    
    # Initialize converter
    converter = NGSIMToSUMOConverter()
    
    # Load data
    converter.load_data()
    
    # Convert units
    converter.convert_units()
    
    # Extract journeys
    converter.extract_vehicle_journeys()
    
    # Generate SUMO routes
    converter.generate_sumo_routes()
    
    # Generate report
    converter.generate_statistics_report()
    
    print("\n" + "=" * 70)
    print("✅ CONVERSION COMPLETE!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  📄 ../data/processed/ngsim_routes.rou.xml")
    print("\nNext steps:")
    print("  1. Review the route file")
    print("  2. Create SUMO network that matches the data")
    print("  3. Test simulation with real traffic patterns")


if __name__ == "__main__":
    main()