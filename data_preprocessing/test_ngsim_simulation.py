# data_preprocessing/test_ngsim_simulation.py
"""
Test NGSIM routes in SUMO simulation
Compare real vs synthetic traffic patterns
"""

import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.sumo_controller import SumoController


def test_ngsim_traffic():
    """Test simulation with real NGSIM traffic"""
    
    print("🚗 Testing NGSIM Traffic in SUMO")
    print("=" * 70)
    
    # Note: Using simple network since NGSIM routes are simplified
    controller = SumoController(
        config_file="../sumo/configs/tls_test.sumocfg",
        port=8813
    )
    
    # Override with NGSIM routes
    controller.route_file = "../data/processed/ngsim_routes.rou.xml"
    
    print("\n📊 Starting simulation with NGSIM data...")
    print("   786 vehicles from real highway traffic")
    print("   60-second duration")
    
    try:
        controller.start()
        
        # Run simulation
        max_vehicles = 0
        total_speed = 0
        total_measurements = 0
        
        for step in range(600):  # 60 seconds
            controller.step()
            
            state = controller.get_detailed_state()
            vehicle_count = state['vehicle_count']
            
            if vehicle_count > max_vehicles:
                max_vehicles = vehicle_count
            
            # Calculate average speed
            if state['vehicles']:
                for vid, vdata in state['vehicles'].items():
                    total_speed += vdata['speed']
                    total_measurements += 1
            
            # Print every 10 seconds
            if step % 100 == 0:
                avg_speed = total_speed / total_measurements if total_measurements > 0 else 0
                print(f"   Step {step:3d}: Vehicles={vehicle_count:3d}, "
                      f"Avg Speed={avg_speed:.2f} m/s")
        
        avg_speed_overall = total_speed / total_measurements if total_measurements > 0 else 0
        
        print("\n📈 NGSIM Simulation Results:")
        print(f"   Max vehicles: {max_vehicles}")
        print(f"   Avg speed: {avg_speed_overall:.2f} m/s ({avg_speed_overall*3.6:.1f} km/h)")
        
        controller.close()
        
        print("\n✅ NGSIM test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        controller.close()


def test_synthetic_traffic():
    """Test simulation with synthetic traffic"""
    
    print("\n\n🏭 Testing Synthetic Traffic in SUMO")
    print("=" * 70)
    
    controller = SumoController(
        config_file="../sumo/configs/tls_test.sumocfg",
        port=8813
    )
    
    controller.route_file = "../data/processed/synthetic_realistic.rou.xml"
    
    print("\n📊 Starting simulation with synthetic data...")
    print("   170 vehicles generated")
    print("   300-second duration")
    
    try:
        controller.start()
        
        max_vehicles = 0
        total_speed = 0
        total_measurements = 0
        
        for step in range(3000):  # 300 seconds
            controller.step()
            
            state = controller.get_detailed_state()
            vehicle_count = state['vehicle_count']
            
            if vehicle_count > max_vehicles:
                max_vehicles = vehicle_count
            
            if state['vehicles']:
                for vid, vdata in state['vehicles'].items():
                    total_speed += vdata['speed']
                    total_measurements += 1
            
            if step % 500 == 0:
                avg_speed = total_speed / total_measurements if total_measurements > 0 else 0
                print(f"   Step {step:4d}: Vehicles={vehicle_count:3d}, "
                      f"Avg Speed={avg_speed:.2f} m/s")
        
        avg_speed_overall = total_speed / total_measurements if total_measurements > 0 else 0
        
        print("\n📈 Synthetic Simulation Results:")
        print(f"   Max vehicles: {max_vehicles}")
        print(f"   Avg speed: {avg_speed_overall:.2f} m/s ({avg_speed_overall*3.6:.1f} km/h)")
        
        controller.close()
        
        print("\n✅ Synthetic test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        controller.close()


if __name__ == "__main__":
    test_ngsim_traffic()
    test_synthetic_traffic()
    
    print("\n" + "=" * 70)
    print("🎉 ALL DATA PIPELINE TESTS COMPLETE!")
    print("=" * 70)