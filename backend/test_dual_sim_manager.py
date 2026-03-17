# backend/test_dual_sim_manager.py
"""
Test script for DualSimManager
Verifies parallel simulation orchestration
"""

import time
from services.dual_sim_manager import DualSimManager


def test_basic_dual_simulation():
    """Test basic dual simulation functionality"""
    
    print("🧪 Testing DualSimManager - Basic Functionality")
    print("=" * 70)
    
    # Create manager
    manager = DualSimManager(
        config_file="../sumo/configs/backend_test.sumocfg"
    )
    
    try:
        # Start both simulations
        manager.start()
        
        print("\n📊 Running parallel simulations for 50 steps...")
        print("-" * 70)
        
        for step in range(50):
            # Step both simulations
            baseline_state, rl_state = manager.step()
            
            # Print every 10 steps
            if step % 10 == 0:
                print(f"\nStep {step:3d}:")
                print(f"  Baseline: Time={baseline_state['time']:5.1f}s, "
                      f"Vehicles={baseline_state['vehicle_count']:2d}")
                print(f"  RL:       Time={rl_state['time']:5.1f}s, "
                      f"Vehicles={rl_state['vehicle_count']:2d}")
        
        # Check synchronization
        print("\n" + "-" * 70)
        print("📌 Checking synchronization...")
        sync_status = manager.get_sync_status()
        
        if sync_status['synchronized']:
            print("✅ Simulations are synchronized!")
            print(f"   Time difference: {sync_status['time_difference']:.3f}s")
        else:
            print("⚠️  Simulations are NOT synchronized")
            print(f"   Baseline: {sync_status['baseline_time']:.2f}s")
            print(f"   RL: {sync_status['rl_time']:.2f}s")
        
        # Stop
        manager.stop()
        
        print("\n" + "=" * 70)
        print("🎉 BASIC TEST PASSED!")
        
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


def test_metrics_computation():
    """Test traffic metrics computation"""
    
    print("\n\n🧪 Testing DualSimManager - Metrics Computation")
    print("=" * 70)
    
    manager = DualSimManager(
        config_file="../sumo/configs/backend_test.sumocfg"
    )
    
    try:
        manager.start()
        
        print("\n📊 Running simulation and computing metrics...")
        print("-" * 70)
        
        # Run for 30 steps to get some traffic
        for step in range(30):
            manager.step()
        
        # Get metrics
        metrics = manager.get_traffic_metrics()
        
        print("\n📈 BASELINE METRICS:")
        baseline = metrics['baseline']
        print(f"  Vehicles: {baseline['vehicle_count']}")
        print(f"  Avg Speed: {baseline['avg_speed']:.2f} m/s")
        print(f"  Avg Waiting Time: {baseline['avg_waiting_time']:.2f} s")
        print(f"  Stopped Vehicles: {baseline['stopped_vehicles']} "
              f"({baseline['stopped_percentage']:.1f}%)")
        
        print("\n📈 RL METRICS:")
        rl = metrics['rl']
        print(f"  Vehicles: {rl['vehicle_count']}")
        print(f"  Avg Speed: {rl['avg_speed']:.2f} m/s")
        print(f"  Avg Waiting Time: {rl['avg_waiting_time']:.2f} s")
        print(f"  Stopped Vehicles: {rl['stopped_vehicles']} "
              f"({rl['stopped_percentage']:.1f}%)")
        
        print("\n📊 COMPARISON:")
        comparison = metrics['comparison']
        print(f"  Waiting Time Improvement: {comparison['waiting_time_improvement']:.1f}%")
        print(f"  Speed Improvement: {comparison['speed_improvement']:.1f}%")
        
        manager.stop()
        
        print("\n" + "=" * 70)
        print("🎉 METRICS TEST PASSED!")
        
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


def test_mode_switching():
    """Test switching between control modes"""
    
    print("\n\n🧪 Testing DualSimManager - Mode Switching")
    print("=" * 70)
    
    manager = DualSimManager(
        config_file="../sumo/configs/backend_test.sumocfg"
    )
    
    try:
        manager.start()
        
        # Test mode switching
        print("\n📌 Testing mode switching...")
        
        manager.set_rl_mode('fixed')
        print("  Current mode: fixed")
        
        manager.set_rl_mode('manual')
        print("  Current mode: manual")
        
        manager.set_rl_mode('rl')
        print("  Current mode: rl")
        
        print("✅ Mode switching works!")
        
        manager.stop()
        
        print("\n" + "=" * 70)
        print("🎉 MODE SWITCHING TEST PASSED!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        
        try:
            manager.stop()
        except:
            pass
        
        return False


if __name__ == "__main__":
    # Run all tests
    test1 = test_basic_dual_simulation()
    
    if test1:
        test2 = test_metrics_computation()
        
        if test2:
            test3 = test_mode_switching()
            
            if test3:
                print("\n" + "=" * 70)
                print("🎉🎉🎉 ALL DUALSIMMANAGER TESTS PASSED! 🎉🎉🎉")
                print("=" * 70)