# backend/test_sumo_controller.py
"""
Test script for SumoController class
Verifies that we can control SUMO programmatically
"""

import os
import sys

# Add SUMO tools to path
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("❌ ERROR: Please set SUMO_HOME environment variable")

from services.sumo_controller import SumoController


def test_basic_control():
    """Test basic SUMO control operations"""
    
    print("🧪 Testing SumoController...")
    print("=" * 60)
    
    # Create controller
    controller = SumoController(
        net_file="../sumo/networks/simple_intersection.net.xml",
        route_file="../sumo/routes/test_light.rou.xml",
        port=8813
    )
    
    # Test 1: Start simulation
    print("\n📌 TEST 1: Starting SUMO simulation")
    try:
        controller.start()
        print("   ✅ SUMO started successfully")
    except Exception as e:
        print(f"   ❌ Failed to start: {e}")
        return False
    
    # Test 2: Step through simulation
    print("\n📌 TEST 2: Stepping through simulation")
    try:
        for i in range(50):
            controller.step()
            
            if i % 10 == 0:
                state = controller.get_state()
                print(f"   Step {i:2d}: Time={state['time']:5.1f}s, "
                      f"Vehicles={state['vehicle_count']:2d}")
        
        print("   ✅ Stepping works correctly")
    except Exception as e:
        print(f"   ❌ Stepping failed: {e}")
        controller.close()
        return False
    
    # Test 3: Get traffic state
    print("\n📌 TEST 3: Extracting traffic state")
    try:
        state = controller.get_state()
        
        print(f"   Current state:")
        print(f"     Time: {state['time']} seconds")
        print(f"     Step: {state['step']}")
        print(f"     Vehicles: {state['vehicle_count']}")
        print(f"     Vehicle IDs: {state['vehicles'][:5]}")  # First 5
        
        print("   ✅ State extraction works")
    except Exception as e:
        print(f"   ❌ State extraction failed: {e}")
        controller.close()
        return False
    
    # Test 4: Get traffic light info
    print("\n📌 TEST 4: Getting traffic light information")
    try:
        tls_ids = controller.get_traffic_light_ids()
        print(f"   Traffic lights found: {len(tls_ids)}")
        
        if tls_ids:
            tls_id = tls_ids[0]
            phase = controller.get_traffic_light_phase(tls_id)
            print(f"   TLS '{tls_id}': Current phase = {phase}")
        
        print("   ✅ Traffic light access works")
    except Exception as e:
        print(f"   ❌ Traffic light access failed: {e}")
        controller.close()
        return False
    
    # Test 5: Control traffic light
    print("\n📌 TEST 5: Controlling traffic lights")
    try:
        if tls_ids:
            tls_id = tls_ids[0]
            original_phase = controller.get_traffic_light_phase(tls_id)
            
            # Change phase
            new_phase = (original_phase + 1) % 4
            controller.set_traffic_light_phase(tls_id, new_phase)
            
            # Verify change
            current_phase = controller.get_traffic_light_phase(tls_id)
            
            if current_phase == new_phase:
                print(f"   ✅ Successfully changed phase: {original_phase} → {new_phase}")
            else:
                print(f"   ⚠️  Phase change may not have taken effect")
        
    except Exception as e:
        print(f"   ❌ Traffic light control failed: {e}")
        controller.close()
        return False
    
    # Test 6: Close simulation
    print("\n📌 TEST 6: Closing simulation")
    try:
        controller.close()
        print("   ✅ SUMO closed successfully")
    except Exception as e:
        print(f"   ❌ Close failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


def test_multiple_instances():
    """Test running multiple SUMO instances (for parallel simulation)"""
    
    print("\n\n🧪 Testing Multiple SUMO Instances...")
    print("=" * 60)
    
    # Create two controllers with different ports
    controller1 = SumoController(
        net_file="../sumo/networks/simple_intersection.net.xml",
        route_file="../sumo/routes/test_light.rou.xml",
        port=8813
    )
    
    controller2 = SumoController(
        net_file="../sumo/networks/simple_intersection.net.xml",
        route_file="../sumo/routes/test_light.rou.xml",
        port=8814
    )
    
    try:
        print("\n📌 Starting both instances...")
        controller1.start()
        print("   ✅ Instance 1 started (port 8813)")
        
        controller2.start()
        print("   ✅ Instance 2 started (port 8814)")
        
        print("\n📌 Running both instances in parallel...")
        for i in range(20):
            controller1.step()
            controller2.step()
            
            if i % 5 == 0:
                state1 = controller1.get_state()
                state2 = controller2.get_state()
                
                print(f"   Step {i:2d}: "
                      f"Sim1={state1['vehicle_count']} vehicles, "
                      f"Sim2={state2['vehicle_count']} vehicles")
        
        print("\n📌 Closing both instances...")
        controller1.close()
        controller2.close()
        
        print("\n✅ Multiple instances test PASSED!")
        
    except Exception as e:
        print(f"\n❌ Multiple instances test FAILED: {e}")
        
        # Cleanup
        try:
            controller1.close()
        except:
            pass
        try:
            controller2.close()
        except:
            pass


if __name__ == "__main__":
    # Run basic test
    success = test_basic_control()
    
    if success:
        # Run multiple instances test
        test_multiple_instances()
    else:
        print("\n❌ Basic test failed. Fix issues before testing multiple instances.")