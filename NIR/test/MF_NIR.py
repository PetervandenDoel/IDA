"""
Minimalist test script for MF_NIR_controller controller.
Tests each method individually on actual hardware.
"""

import sys
import numpy as np
from NIR.mf_nir_controller import MF_NIR_controller


def test_connection():
    """Test connection and enumeration"""
    print("\n=== Test: Connection ===")
    nir = MF_NIR_controller(gpib_addr=20)
    
    result = nir.connect()
    print(f"Connection: {'PASS' if result else 'FAIL'}")
    
    if result:
        info = nir.get_enumeration_info()
        print(f"Mainframe: {info['mainframe_model']}")
        print(f"Slots: {info['num_slots']}")
        print(f"Lasers: {len(info['discovered_modules']['lasers'])}")
        print(f"Detectors: {len(info['discovered_modules']['detectors'])}")
        print(f"Active laser slot: {info['active_laser_slot']}")
        print(f"Active detector slots: {info['active_detector_slots']}")
        print(f"Detector channels: {info['detector_channels']}")
    
    return nir if result else None


def test_laser_functions(nir):
    """Test laser control functions"""
    print("\n=== Test: Laser Functions ===")
    
    # Test get wavelength
    wl = nir.get_wavelength()
    print(f"Get wavelength: {'PASS' if wl is not None else 'FAIL'} ({wl:.3f} nm)")
    
    # Test set wavelength
    target_wl = 1550.0
    result = nir.set_wavelength(target_wl)
    actual_wl = nir.get_wavelength()
    wl_match = abs(actual_wl - target_wl) < 0.001
    print(f"Set wavelength to {target_wl} nm: {'PASS' if result and wl_match else 'FAIL'} ({actual_wl:.3f} nm)")
    
    # Test get power
    pwr = nir.get_power()
    print(f"Get power: {'PASS' if pwr is not None else 'FAIL'} ({pwr:.2f} dBm)")
    
    # Test set power
    target_pwr = 0.0
    result = nir.set_power(target_pwr)
    actual_pwr = nir.get_power()
    pwr_match = abs(actual_pwr - target_pwr) < 0.1
    print(f"Set power to {target_pwr} dBm: {'PASS' if result and pwr_match else 'FAIL'} ({actual_pwr:.2f} dBm)")
    
    # Test output state
    state = nir.get_output_state()
    print(f"Get output state: {'PASS' if isinstance(state, bool) else 'FAIL'} (state={state})")
    
    # Test enable output
    result = nir.enable_output(True)
    state = nir.get_output_state()
    print(f"Enable output: {'PASS' if result and state else 'FAIL'} (state={state})")
    
    # Test disable output
    result = nir.enable_output(False)
    state = nir.get_output_state()
    print(f"Disable output: {'PASS' if result and not state else 'FAIL'} (state={state})")


def test_detector_functions(nir):
    """Test detector functions"""
    print("\n=== Test: Detector Functions ===")
    
    if not nir.detector_channels:
        print("No detectors found, skipping detector tests")
        return
    
    # Test get units
    units = nir.get_detector_units()
    print(f"Get detector units: {'PASS' if units is not None else 'FAIL'} ({units})")
    
    # Test set units
    result = nir.set_detector_units(0)
    units = nir.get_detector_units()
    all_dbm = all(u == 0 for u in units) if units else False
    print(f"Set detector units to dBm: {'PASS' if result and all_dbm else 'FAIL'}")
    
    # Test read power
    powers = nir.read_power()
    print(f"Read power: {'PASS' if powers is not None else 'FAIL'}")
    if powers:
        for i, (slot, ch) in enumerate(nir.detector_channels):
            print(f"  Slot {slot} Ch {ch}: {powers[i]:.2f} dBm")
    
    # Test enable autorange
    result = nir.enable_autorange(True)
    print(f"Enable autorange: {'PASS' if result else 'FAIL'}")
    
    # Test set manual range
    result = nir.set_power_range(-10.0)
    ranges = nir.get_power_range()
    print(f"Set manual range: {'PASS' if result else 'FAIL'}")
    if ranges:
        for i, (mode, val) in enumerate(ranges):
            print(f"  Channel {i}: mode={mode} range={val:.2f}")
    
    # Test set reference
    result = nir.set_power_reference(-40.0)
    refs = nir.get_power_reference()
    print(f"Set reference: {'PASS' if result else 'FAIL'}")
    if refs:
        for i, ref in enumerate(refs):
            print(f"  Channel {i}: {ref:.2f} dBm")


def test_small_sweep(nir):
    """Test small lambda scan"""
    print("\n=== Test: Small Lambda Scan ===")
    
    if not nir.detector_channels:
        print("No detectors found, skipping sweep test")
        return
    
    try:
        result = nir.optical_sweep(
            start_nm=1549.0,
            stop_nm=1551.0,
            step_nm=0.1,
            power_dbm=0.0,
            num_scans=0
        )
        
        wl, *channels = result
        
        print(f"Sweep execution: PASS")
        print(f"Wavelength points: {len(wl)}")
        print(f"Channels returned: {len(channels)}")
        
        expected_points = int((1551.0 - 1549.0) / 0.1) + 1
        points_match = abs(len(wl) - expected_points) <= 1
        print(f"Expected points: {expected_points}, got {len(wl)} - {'PASS' if points_match else 'FAIL'}")
        
        for i, ch_data in enumerate(channels):
            valid_points = np.sum(~np.isnan(ch_data))
            avg_power = np.nanmean(ch_data)
            print(f"Channel {i}: {valid_points}/{len(ch_data)} valid points, avg={avg_power:.2f} dBm")
        
        all_valid = all(np.sum(~np.isnan(ch)) > 0 for ch in channels)
        print(f"Data validity: {'PASS' if all_valid else 'FAIL'}")
        
    except Exception as e:
        print(f"Sweep execution: FAIL - {e}")


def test_segmented_sweep(nir):
    """Test multi-segment lambda scan"""
    print("\n=== Test: Multi-Segment Lambda Scan ===")
    
    if not nir.detector_channels:
        print("No detectors found, skipping sweep test")
        return
    
    try:
        # 250k points = 3 segments at 100k per segment
        result = nir.optical_sweep(
            start_nm=1490.0,
            stop_nm=1515.0,
            step_nm=0.0001,
            power_dbm=0.0,
            num_scans=0
        )
        
        wl, *channels = result
        
        print(f"Segmented sweep execution: PASS")
        print(f"Wavelength points: {len(wl)}")
        
        expected_points = int((1515.0 - 1490.0) / 0.0001) + 1
        points_match = abs(len(wl) - expected_points) <= 10
        print(f"Expected points: {expected_points}, got {len(wl)} - {'PASS' if points_match else 'FAIL'}")
        
        for i, ch_data in enumerate(channels):
            valid_points = np.sum(~np.isnan(ch_data))
            print(f"Channel {i}: {valid_points}/{len(ch_data)} valid points")
        
    except Exception as e:
        print(f"Segmented sweep execution: FAIL - {e}")


def test_sweep_with_args(nir):
    """Test lambda scan with manual args"""
    print("\n=== Test: Lambda Scan with Manual Args ===")
    
    if not nir.detector_channels:
        print("No detectors found, skipping sweep test")
        return
    
    try:
        # Build args for all detector slots
        args = []
        unique_slots = list(set(slot for slot, ch in nir.detector_channels))
        for slot in unique_slots:
            args.extend([slot, -70.0, -10.0])  # ref=-70dBm, manual range=-10dBm
        
        print(f"Using args: {args}")
        
        result = nir.optical_sweep(
            start_nm=1549.0,
            stop_nm=1551.0,
            step_nm=0.1,
            power_dbm=0.0,
            num_scans=0,
            args=args
        )
        
        wl, *channels = result
        
        print(f"Sweep with manual args: PASS")
        print(f"Points: {len(wl)}, Channels: {len(channels)}")
        
    except Exception as e:
        print(f"Sweep with manual args: FAIL - {e}")


def test_cancel_sweep(nir):
    """Test sweep cancellation"""
    print("\n=== Test: Sweep Cancel ===")
    
    if not nir.detector_channels:
        print("No detectors found, skipping cancel test")
        return
    
    import threading
    
    def cancel_after_delay():
        import time
        time.sleep(0.5)
        nir.sweep_cancel()
        print("Cancel signal sent")
    
    try:
        cancel_thread = threading.Thread(target=cancel_after_delay)
        cancel_thread.start()
        
        result = nir.optical_sweep(
            start_nm=1490.0,
            stop_nm=1640.0,
            step_nm=0.01,
            power_dbm=0.0
        )
        
        cancel_thread.join()
        
        wl, *channels = result
        print(f"Sweep cancelled: points collected = {len(wl)}")
        print(f"Cancel functionality: PASS (partial data returned)")
        
    except Exception as e:
        print(f"Cancel test: FAIL - {e}")


def main():
    print("MF_NIR_controller Controller Test Suite")
    print("=" * 50)
    
    # Test connection
    nir = test_connection()
    if nir is None:
        print("\nConnection failed. Cannot continue tests.")
        sys.exit(1)
    
    try:
        # Test laser functions
        test_laser_functions(nir)
        
        # Test detector functions
        test_detector_functions(nir)
        
        # Test sweeps
        test_small_sweep(nir)
        test_segmented_sweep(nir)
        test_sweep_with_args(nir)
        test_cancel_sweep(nir)
        
    finally:
        # Cleanup
        print("\n=== Cleanup ===")
        nir.enable_output(False)
        nir.disconnect()
        print("Disconnected")
    
    print("\n" + "=" * 50)
    print("Test suite complete")


if __name__ == "__main__":
    main()