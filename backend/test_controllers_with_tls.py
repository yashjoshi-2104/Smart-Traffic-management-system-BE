# backend/test_controllers_with_tls.py
"""
Test controllers with actual traffic light network
This demonstrates real signal control with visible effects
"""

from services.dual_sim_manager import DualSimManager
from controllers import FixedTimeController, ManualController, RLController


def test_controllers_on_tls_network():
    """
    Test all three controllers on a network with traffic lights
    Shows how different control strategies affect traffic
    """
    
    print("🚦 Testing Controllers on Traffic Light Network")
    print("=" * 70)
    
    # Create manager with TLS network
    manager = DualSimManager(
        config_file="../sumo/configs/tls_test.sumocfg"
    )
    
    # Create controllers
    fixed_controller = FixedTimeController(
        phase_durations=[30, 30, 10, 10]  # 80s cycle
    )
    
    manual_controller = ManualController(initial_phase=0)
    rl_controller = RLController()
    
    try:
        # Start simulations
        manager.start()
        
        # Get traffic light IDs
        tls_ids = manager.baseline_controller.get_traffic_light_ids()
        
        if not tls_ids:
            print("\n❌ No traffic lights found!")
            manager.stop()
            return False
        
        print(f"\n✅ Found {len(tls_ids)} traffic light(s): {tls_ids}")
        tls_id = tls_ids[0]
        
        print(f"\n🎮 Testing Fixed-Time vs Manual Control")
        print("-" * 70)
        print("  Baseline: Fixed-time (30s, 30s, 10s, 10s)")
        print("  RL:       Manual (we'll change it)")
        
        print("\n📊 Running simulation...")
        print("-" * 70)
        
        for step in range(100):
            # Baseline: Use fixed-time controller
            baseline_state = manager.baseline_controller.get_detailed_state()
            baseline_action = fixed_controller.get_action(baseline_state)
            manager.baseline_controller.set_traffic_light_phase(tls_id, baseline_action)
            
            # RL: Use manual controller (we'll change it at specific steps)
            if step == 25:
                print(f"\n  🔧 Step {step}: Manually switching RL to Phase 2")
                manual_controller.set_phase(2)
            elif step == 50:
                print(f"\n  🔧 Step {step}: Manually switching RL to Phase 0")
                manual_controller.set_phase(0)
            elif step == 75:
                print(f"\n  🔧 Step {step}: Manually switching RL to Phase 1")
                manual_controller.set_phase(1)
            
            rl_state = manager.rl_controller.get_detailed_state()
            rl_action = manual_controller.get_action(rl_state)
            manager.rl_controller.set_traffic_light_phase(tls_id, rl_action)
            
            # Step both simulations
            manager.step()
            
            # Print status every 10 steps
            if step % 10 == 0:
                baseline_metrics = manager._compute_metrics(baseline_state)
                rl_metrics = manager._compute_metrics(rl_state)
                
                print(f"\n  Step {step:3d}:")
                print(f"    Baseline: Phase={baseline_action}, "
                      f"Vehicles={baseline_metrics['vehicle_count']}, "
                      f"Stopped={baseline_metrics['stopped_vehicles']}")
                print(f"    RL:       Phase={rl_action}, "
                      f"Vehicles={rl_metrics['vehicle_count']}, "
                      f"Stopped={rl_metrics['stopped_vehicles']}")
        
        # Final metrics
        print("\n" + "-" * 70)
        print("📊 FINAL METRICS:")
        
        metrics = manager.get_traffic_metrics()
        
        print("\n  BASELINE (Fixed-Time):")
        baseline = metrics['baseline']
        print(f"    Vehicles: {baseline['vehicle_count']}")
        print(f"    Avg Speed: {baseline['avg_speed']:.2f} m/s")
        print(f"    Avg Waiting: {baseline['avg_waiting_time']:.2f} s")
        print(f"    Stopped: {baseline['stopped_vehicles']} ({baseline['stopped_percentage']:.1f}%)")
        
        print("\n  RL (Manual Control):")
        rl = metrics['rl']
        print(f"    Vehicles: {rl['vehicle_count']}")
        print(f"    Avg Speed: {rl['avg_speed']:.2f} m/s")
        print(f"    Avg Waiting: {rl['avg_waiting_time']:.2f} s")
        print(f"    Stopped: {rl['stopped_vehicles']} ({rl['stopped_percentage']:.1f}%)")
        
        manager.stop()
        
        print("\n" + "=" * 70)
        print("🎉 TRAFFIC LIGHT CONTROLLER TEST PASSED!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            manager.stop()
        except:
            pass
        
        return False


def test_compare_all_three_controllers():
    """
    Run three separate simulations to compare all controllers
    """
    
    print("\n\n🏁 Comparing All Three Controllers")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Fixed-Time
    print("\n1️⃣  Running with Fixed-Time Controller...")
    results['fixed'] = run_single_controller_test(FixedTimeController())
    
    # Test 2: Manual (constant phase 0)
    print("\n2️⃣  Running with Manual Controller (Phase 0)...")
    manual = ManualController(initial_phase=0)
    results['manual'] = run_single_controller_test(manual)
    
    # Test 3: RL (placeholder mode)
    print("\n3️⃣  Running with RL Controller (Placeholder)...")
    results['rl'] = run_single_controller_test(RLController())
    
    # Compare results
    print("\n" + "=" * 70)
    print("📊 COMPARISON RESULTS:")
    print("-" * 70)
    
    for name, metrics in results.items():
        print(f"\n{name.upper()}:")
        print(f"  Avg Speed: {metrics['avg_speed']:.2f} m/s")
        print(f"  Avg Waiting: {metrics['avg_waiting_time']:.2f} s")
        print(f"  Stopped %: {metrics['stopped_percentage']:.1f}%")
    
    print("\n" + "=" * 70)


def run_single_controller_test(controller):
    """Helper: Run simulation with one controller"""
    
    from services.sumo_controller import SumoController
    
    sim = SumoController(
        config_file="../sumo/configs/tls_test.sumocfg",
        port=8813
    )
    
    sim.start()
    
    tls_ids = sim.get_traffic_light_ids()
    if tls_ids:
        tls_id = tls_ids[0]
    
    # Run for 100 steps
    for step in range(100):
        state = sim.get_detailed_state()
        
        if tls_ids:
            action = controller.get_action(state)
            sim.set_traffic_light_phase(tls_id, action)
        
        sim.step()
    
    # Get final metrics
    final_state = sim.get_detailed_state()
    
    vehicles = final_state['vehicles']
    if not vehicles:
        metrics = {'avg_speed': 0, 'avg_waiting_time': 0, 'stopped_percentage': 0}
    else:
        total_speed = sum(v['speed'] for v in vehicles.values())
        total_waiting = sum(v['waiting_time'] for v in vehicles.values())
        stopped = sum(1 for v in vehicles.values() if v['speed'] < 0.1)
        
        metrics = {
            'avg_speed': total_speed / len(vehicles),
            'avg_waiting_time': total_waiting / len(vehicles),
            'stopped_percentage': (stopped / len(vehicles) * 100)
        }
    
    sim.close()
    
    return metrics


if __name__ == "__main__":
    success = test_controllers_on_tls_network()
    
    if success:
        test_compare_all_three_controllers()