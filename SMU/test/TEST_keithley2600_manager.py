from SMU.keithley2600_manager import Keithley2600Manager
import time
from time import sleep

print("=== Keithley 2600 Manager Test Suite ===")

# Test initialization
print("\n1. Testing Manager Initialization")
manager = Keithley2600Manager(
    visa_address='GPIB0::26::INSTR',
    nplc=0.1,
    off_mode="NORMAL",
    polling_interval=0.5,
    debug=True
)
print(f"Manager created: {manager is not None}")

# Test device lifecycle
print("\n2. Testing Device Lifecycle")
init_ok = manager.initialize()
print(f"Initialize: {init_ok}")

connect_ok = manager.connect()
print(f"Connect: {connect_ok}")

is_connected = manager.is_connected()
print(f"Is Connected: {is_connected}")

if connect_ok:
    print(f"Device IDN: {manager.smu.idn()}")

# Test configuration methods
print("\n3. Testing Configuration Methods")
channels = ["A", "B"]

for ch in channels:
    print(f"\n--- Testing Channel {ch} ---")
    
    # Test setters
    mode_ok = manager.set_source_mode("V", ch)
    print(f"Set source mode (V): {mode_ok}")
    
    volt_ok = manager.set_voltage(1.0, ch)
    print(f"Set voltage (1.0V): {volt_ok}")
    
    curr_lim_ok = manager.set_current_limit(0.01, ch)
    print(f"Set current limit (10mA): {curr_lim_ok}")
    
    volt_lim_ok = manager.set_voltage_limit(5.0, ch)
    print(f"Set voltage limit (5V): {volt_lim_ok}")
    
    pow_lim_ok = manager.set_power_limit(0.5, ch)
    print(f"Set power limit (0.5W): {pow_lim_ok}")

# Test measurements
print("\n4. Testing Measurement Methods")
if connect_ok:
    voltage = manager.get_voltage()
    print(f"Voltage: {voltage}")
    
    current = manager.get_current()
    print(f"Current: {current}")
    
    resistance = manager.get_resistance()
    print(f"Resistance: {resistance}")
    
    state = manager.get_state()
    print(f"State: {state}")

# Test output control
print("\n5. Testing Output Control")
for ch in channels:
    on_ok = manager.output_on(ch)
    print(f"Output ON Channel {ch}: {on_ok}")
    sleep(0.5)
    
    off_ok = manager.output_off(ch)
    print(f"Output OFF Channel {ch}: {off_ok}")

# Test ranging
print("\n6. Testing Ranging")
if connect_ok:
    range_ok = manager.source_range(1.0, ["A"], "voltage")
    print(f"Set source range: {range_ok}")
    
    autorange_ok = manager.source_autorange(0.1, ["A"], "voltage")
    print(f"Set autorange: {autorange_ok}")

# Test error handling
print("\n7. Testing Error Handling")
if connect_ok:
    errors = manager.get_errors()
    print(f"Errors: {errors}")
    
    clear_ok = manager.clear_errors()
    print(f"Clear errors: {clear_ok}")

# Test configuration retrieval
print("\n8. Testing Configuration Retrieval")
config = manager.get_config()
print(f"Config: {config}")

device_info = manager.get_device_info()
print(f"Device Info Keys: {list(device_info.keys())}")

# Test polling functionality
print("\n9. Testing Polling Functionality")
if connect_ok:
    polling_start = manager.start_polling()
    print(f"Start polling: {polling_start}")
    
    is_polling = manager.is_polling()
    print(f"Is polling: {is_polling}")
    
    # Wait for some polling cycles
    print("Waiting 3 seconds for polling...")
    sleep(3)
    
    last_measurements = manager.get_last_measurements()
    print(f"Last measurements keys: {list(last_measurements.keys())}")
    
    # Test polling interval change
    interval_ok = manager.set_polling_interval(1.0)
    print(f"Set polling interval: {interval_ok}")
    
    polling_stop = manager.stop_polling()
    print(f"Stop polling: {polling_stop}")

# Test callback system
print("\n10. Testing Callback System")
callback_called = {"count": 0}

def test_event_callback(event):
    callback_called["count"] += 1
    print(f"Event callback called: {event.event_type.value}")

def test_measurement_callback(measurements):
    print(f"Measurement callback called with {len(measurements)} measurements")

manager.add_event_callback(test_event_callback)
manager.add_measurement_callback(test_measurement_callback)

# Test a quick operation to trigger callbacks
if connect_ok:
    manager.output_on("A")
    sleep(0.1)
    manager.output_off("A")

manager.remove_event_callback(test_event_callback)
manager.remove_measurement_callback(test_measurement_callback)

print(f"Event callbacks triggered: {callback_called['count']}")

# Test IV sweep
print("\n11. Testing IV Sweep")
if connect_ok:
    # Set up safe sweep parameters
    manager.set_source_mode("V", "A")
    manager.set_current_limit(0.001, "A")  # 1mA limit for safety
    
    sweep_result = manager.iv_sweep(
        start=0.0,
        stop=0.1, 
        step=0.05,
        channels=["A"],
        sweep_type="voltage"
    )
    
    if sweep_result:
        print(f"IV Sweep successful: {len(sweep_result)} channels")
        for ch, data in sweep_result.items():
            if data:
                print(f"Channel {ch}: {len(data.get('V', []))} points")
    else:
        print("IV Sweep failed")

# Test IV sweep list
print("\n12. Testing IV Sweep List")
if connect_ok:
    sweep_list_result = manager.iv_sweep_list(
        sweep_list=[0.0, 0.05, 0.1],
        channels=["A"],
        sweep_type="voltage"
    )
    
    if sweep_list_result:
        print(f"IV Sweep List successful: {len(sweep_list_result)} channels")
        for ch, data in sweep_list_result.items():
            if data:
                print(f"Channel {ch}: {len(data.get('V', []))} points")
    else:
        print("IV Sweep List failed")

# Test context manager
print("\n13. Testing Context Manager")
try:
    with Keithley2600Manager('GPIB0::26::INSTR') as ctx_manager:
        print(f"Context manager created: {ctx_manager is not None}")
    print("Context manager exited successfully")
except Exception as e:
    print(f"Context manager error: {e}")

# Cleanup
print("\n14. Cleanup")
if connect_ok:
    # Ensure all outputs are off
    for ch in channels:
        manager.output_off(ch)
    print("All outputs turned off")

disconnect_ok = manager.disconnect()
print(f"Disconnect: {disconnect_ok}")

manager.shutdown()
print("Manager shutdown complete")

print("\n=== Test Suite Complete ===")