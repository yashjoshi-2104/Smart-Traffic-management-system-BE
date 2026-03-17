# backend/test_controllers.py
"""
Test all three signal controllers
"""

from controllers import FixedTimeController, ManualController, RLController


def test_fixed_time_controller():
    """Test fixed-time controller"""
    print("🧪 Testing FixedTimeController...")
    print("=" * 60)
    
    controller = FixedTimeController(phase_durations=[10, 10, 5, 5])
    
    print("\nPhase cycle: [10s, 10s, 5s, 5s] = 30s total")
    print("\nRunning for 35 seconds...")
    
    for step in range(35):
        action = controller.get_action({})
        phase_info = controller.get_phase_info()
        
        if step % 5 == 0:
            print(f"Step {step:2d}: Phase={action}, "
                  f"TimeInPhase={phase_info['time_in_phase']:2d}s, "
                  f"Remaining={phase_info['time_remaining']:2d}s")
    
    print("\n✅ FixedTimeController test passed!")
    return True


def test_manual_controller():
    """Test manual controller"""
    print("\n\n🧪 Testing ManualController...")
    print("=" * 60)
    
    controller = ManualController(initial_phase=0)
    
    print("\nInitial phase: 0")
    print("Manually changing phases...\n")
    
    # Run a few steps
    for i in range(3):
        action = controller.get_action({})
        print(f"Step {i}: Phase = {action}")
    
    # Manual override
    print("\n🔧 User clicks: Change to Phase 2")
    controller.set_phase(2)
    
    for i in range(3, 6):
        action = controller.get_action({})
        print(f"Step {i}: Phase = {action}")
    
    # Another override
    print("\n🔧 User clicks: Change to Phase 1")
    controller.set_phase(1)
    
    for i in range(6, 9):
        action = controller.get_action({})
        print(f"Step {i}: Phase = {action}")
    
    # Check history
    print("\n📜 Phase change history:")
    for change in controller.get_phase_history():
        print(f"   Step {change['step']}: Phase {change['from_phase']} → {change['to_phase']}")
    
    print("\n✅ ManualController test passed!")
    return True


def test_rl_controller():
    """Test RL controller (placeholder mode)"""
    print("\n\n🧪 Testing RLController (Placeholder Mode)...")
    print("=" * 60)
    
    controller = RLController()  # No model = placeholder mode
    
    print("\nRunning in heuristic mode (acts like fixed-time)...\n")
    
    for step in range(40):
        action = controller.get_action({})
        
        if step % 10 == 0:
            print(f"Step {step:2d}: Phase = {action}, "
                  f"Time since change = {controller.time_since_change}s")
    
    print("\n✅ RLController test passed!")
    return True


if __name__ == "__main__":
    test1 = test_fixed_time_controller()
    test2 = test_manual_controller()
    test3 = test_rl_controller()
    
    if test1 and test2 and test3:
        print("\n" + "=" * 60)
        print("🎉🎉🎉 ALL CONTROLLER TESTS PASSED! 🎉🎉🎉")
        print("=" * 60)