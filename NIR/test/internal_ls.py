#!/usr/bin/env python3
"""
Simple Lambda Sweep Test Script for Keysight 8164B
No OOP, just direct commands to test sweep functionality
"""

import time
import numpy as np
import struct

# ==============================================================================
# CONFIGURATION PARAMETERS - MODIFY THESE AS NEEDED
# ==============================================================================
START_NM = 1540.0      # Start wavelength in nm
STOP_NM = 1560.0       # Stop wavelength in nm  
STEP_NM = 0.01         # Step size in nm
POWER_DBM = 1        # Laser power in dBm
DWELL_TIME_MS = 20     # Time to stay at each wavelength (ms)
AVG_TIME_MS = 10       # Detector averaging time (ms) - should be < dwell time
SWEEP_MODE = "CONT"    # "CONT" or "STEP"

# Calculate derived parameters
NUM_POINTS = int((STOP_NM - START_NM) / STEP_NM) + 1
SWEEP_SPEED_NMS = (STEP_NM * 1000) / DWELL_TIME_MS  # For CONT mode (nm/s)

print(f"Configuration:")
print(f"  Range: {START_NM}-{STOP_NM} nm")
print(f"  Step: {STEP_NM} nm")
print(f"  Points: {NUM_POINTS}")
print(f"  Dwell: {DWELL_TIME_MS} ms")
print(f"  Mode: {SWEEP_MODE}")
if SWEEP_MODE == "CONT":
    print(f"  Speed: {SWEEP_SPEED_NMS} nm/s")
print("-" * 50)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def write_cmd(inst, cmd):
    """Write command and print it"""
    print(f"WRITE: {cmd}")
    inst.write(cmd)
    time.sleep(0.05)  # Small delay between commands

def query_cmd(inst, cmd):
    """Query command and return response"""
    print(f"QUERY: {cmd}")
    response = inst.query(cmd).strip()
    print(f"  RESP: {response}")
    return response

def check_errors(inst):
    """Check for instrument errors"""
    error = query_cmd(inst, "SYST:ERR?")
    if not error.startswith("0") and not error.startswith("+0"):
        print(f"  ERROR DETECTED: {error}")
    return error

def parse_binary_data(inst, cmd):
    """Parse binary data from instrument"""
    print(f"BINARY QUERY: {cmd}")
    inst.write(cmd)
    
    # Read the header
    header = inst.read_bytes(1)
    if header != b'#':
        print("  ERROR: Invalid binary header")
        return None
    
    # Read size of size
    size_of_size = int(inst.read_bytes(1))
    # Read the actual size
    data_size = int(inst.read_bytes(size_of_size))
    # Read the binary data
    binary_data = inst.read_bytes(data_size)
    
    # Parse as float32 array (assuming IEEE format)
    num_floats = data_size // 4
    data = struct.unpack(f'<{num_floats}f', binary_data)
    
    print(f"  Retrieved {len(data)} points")
    return np.array(data)

# ==============================================================================
# MAIN TEST SEQUENCE
# ==============================================================================

def test_lambda_sweep(inst):
    """Test lambda sweep configuration and execution"""
    
    print("\n" + "="*50)
    print("LAMBDA SWEEP TEST SEQUENCE")
    print("="*50)
    
    # --------------------------------------------------------------------------
    # PHASE 1: INITIAL SETUP AND CLEANUP
    # --------------------------------------------------------------------------
    print("\n--- PHASE 1: Initial Setup ---")
    
    write_cmd(inst, "*CLS")  # Clear status
    write_cmd(inst, "SOUR0:WAV:SWE:STAT STOP")  # Stop any ongoing sweep
    time.sleep(0.5)
    
    # Check initial state
    query_cmd(inst, "*IDN?")  # Identify instrument
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # PHASE 2: LASER CONFIGURATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 2: Laser Configuration ---")
    
    # Set power and turn on
    write_cmd(inst, f"SOUR0:POW {POWER_DBM}DBM")
    write_cmd(inst, "SOUR0:POW:STAT ON")
    time.sleep(0.5)  # Let laser stabilize
    
    # Verify power
    actual_power = query_cmd(inst, "SOUR0:POW?")
    
    # Set initial wavelength
    write_cmd(inst, f"SOUR0:WAV {START_NM}NM")
    time.sleep(1.0)  # Important: Let laser reach start wavelength
    
    # Verify wavelength
    actual_wavl = query_cmd(inst, "SOUR0:WAV?")
    
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # PHASE 3: SWEEP CONFIGURATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 3: Sweep Configuration ---")
    
    # Set sweep mode
    write_cmd(inst, f"SOUR0:WAV:SWE:MODE {SWEEP_MODE}")
    
    # Set sweep parameters
    write_cmd(inst, f"SOUR0:WAV:SWE:STAR {START_NM}NM")
    write_cmd(inst, f"SOUR0:WAV:SWE:STOP {STOP_NM}NM")
    write_cmd(inst, f"SOUR0:WAV:SWE:STEP {STEP_NM}NM")
    
    # Set dwell time or speed depending on mode
    if SWEEP_MODE == "STEP":
        # Try to set dwell time (may not be available on all models)
        write_cmd(inst, f"SOUR0:WAV:SWE:DWEL {DWELL_TIME_MS}MS")
    else:  # CONT mode
        write_cmd(inst, f"SOUR0:WAV:SWE:SPE {SWEEP_SPEED_NMS}NM/S")
    
    # Set repeat mode and cycles
    write_cmd(inst, "SOUR0:WAV:SWE:REP ONEW")  # One-way
    write_cmd(inst, "SOUR0:WAV:SWE:CYCL 1")    # One cycle
    
    # Verify sweep configuration
    query_cmd(inst, "SOUR0:WAV:SWE:MODE?")
    query_cmd(inst, "SOUR0:WAV:SWE:STAR?")
    query_cmd(inst, "SOUR0:WAV:SWE:STOP?")
    query_cmd(inst, "SOUR0:WAV:SWE:STEP?")
    if SWEEP_MODE == "CONT":
        query_cmd(inst, "SOUR0:WAV:SWE:SPE?")
    
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # PHASE 4: TRIGGER CONFIGURATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 4: Trigger Configuration ---")
    
    # Enable trigger system
    write_cmd(inst, "TRIG:CONF DEF")  # Default trigger configuration
    
    # Configure laser output trigger
    write_cmd(inst, "TRIG0:OUTP STF")  # Trigger on Step Finished
    
    # Verify trigger configuration
    query_cmd(inst, "TRIG:CONF?")
    query_cmd(inst, "TRIG0:OUTP?")
    
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # PHASE 5: DETECTOR CONFIGURATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 5: Detector Configuration ---")
    
    # Set detector wavelength to center of range
    center_wavl = (START_NM + STOP_NM) / 2
    write_cmd(inst, f"SENS1:CHAN1:POW:WAV {center_wavl}NM")
    
    # Configure power units
    write_cmd(inst, "SENS1:CHAN1:POW:UNIT DBM")
    
    # Enable auto-ranging
    write_cmd(inst, "SENS1:CHAN1:POW:RANG:AUTO ON")
    
    # Set power meter averaging time (must be less than dwell time)
    avg_time_s = AVG_TIME_MS / 1000.0
    write_cmd(inst, f"SENS1:CHAN1:POW:ATIM {avg_time_s}S")
    
    # Configure detector triggering
    write_cmd(inst, "TRIG1:INP SME")      # Single measurement per trigger
    write_cmd(inst, "TRIG1:INP:REARM ON")  # Auto-rearm
    
    # Verify detector configuration
    query_cmd(inst, "SENS1:CHAN1:POW:WAV?")
    query_cmd(inst, "SENS1:CHAN1:POW:RANG:AUTO?")
    query_cmd(inst, "TRIG1:INP?")
    
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # PHASE 6: LOGGING CONFIGURATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 6: Logging Configuration ---")
    
    # Stop any ongoing logging
    write_cmd(inst, "SENS1:FUNC:STOP")
    time.sleep(0.2)
    
    # Configure logging parameters
    write_cmd(inst, f"SENS1:FUNC:PAR:LOGG {NUM_POINTS},{avg_time_s}S")
    
    # Verify logging configuration
    query_cmd(inst, "SENS1:FUNC:PAR:LOGG?")
    
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # PHASE 7: START MEASUREMENT
    # --------------------------------------------------------------------------
    print("\n--- PHASE 7: Starting Measurement ---")
    
    # CRITICAL: Start logging BEFORE sweep
    write_cmd(inst, "SENS1:FUNC:STAT LOGG,START")
    time.sleep(0.5)  # Let logging initialize
    
    # Verify logging started
    logging_status = query_cmd(inst, "SENS1:FUNC:STAT?")
    
    # Start the sweep
    write_cmd(inst, "SOUR0:WAV:SWE:STAT START")
    print("\n*** SWEEP STARTED ***")
    
    # Calculate expected duration
    if SWEEP_MODE == "STEP":
        expected_time = NUM_POINTS * (DWELL_TIME_MS / 1000.0)
    else:
        expected_time = (STOP_NM - START_NM) / SWEEP_SPEED_NMS
    
    print(f"Expected duration: {expected_time:.1f} seconds")
    print("Monitoring progress...")
    
    # --------------------------------------------------------------------------
    # PHASE 8: MONITOR PROGRESS
    # --------------------------------------------------------------------------
    start_time = time.time()
    last_report = 0
    
    while True:
        elapsed = time.time() - start_time
        
        # Report status every 2 seconds
        if elapsed - last_report > 2.0:
            sweep_stat = query_cmd(inst, "SOUR0:WAV:SWE:STAT?")
            func_stat = query_cmd(inst, "SENS1:FUNC:STAT?")
            current_wavl = query_cmd(inst, "SOUR0:WAV?")
            print(f"  Elapsed: {elapsed:.1f}s, Wavelength: {float(current_wavl)*1e9:.2f}nm")
            last_report = elapsed
        
        # Check for completion
        if elapsed > 0.5:  # Don't check immediately
            sweep_stat = inst.query("SOUR0:WAV:SWE:STAT?").strip()
            func_stat = inst.query("SENS1:FUNC:STAT?").strip()
            
            if ("0" in sweep_stat or "STOP" in sweep_stat.upper()) and \
               ("COMPLETE" in func_stat.upper() or "1" in func_stat):
                print(f"\n*** SWEEP COMPLETED in {elapsed:.1f} seconds ***")
                break
        
        # Timeout protection
        if elapsed > expected_time * 2:
            print(f"\n*** TIMEOUT after {elapsed:.1f} seconds ***")
            break
        
        time.sleep(0.1)
    
    # --------------------------------------------------------------------------
    # PHASE 9: RETRIEVE DATA
    # --------------------------------------------------------------------------
    print("\n--- PHASE 9: Retrieving Data ---")
    
    # CRITICAL: Stop logging before retrieval
    write_cmd(inst, "SENS1:FUNC:STOP")
    time.sleep(0.5)
    
    # Check how many points were logged
    logged_points = query_cmd(inst, "SENS1:FUNC:PAR:LOGG?")
    
    # Retrieve the data
    print("\nRetrieving Channel 1 data...")
    ch1_data = parse_binary_data(inst, "SENS1:CHAN1:FUNC:RES?")
    
    # Try to get channel 2 if it exists
    print("\nTrying Channel 2...")
    try:
        ch2_data = parse_binary_data(inst, "SENS1:CHAN2:FUNC:RES?")
    except:
        print("  No Channel 2 data available")
        ch2_data = None
    
    # --------------------------------------------------------------------------
    # PHASE 10: DATA VALIDATION
    # --------------------------------------------------------------------------
    print("\n--- PHASE 10: Data Validation ---")
    
    if ch1_data is not None:
        print(f"Channel 1: {len(ch1_data)} points")
        print(f"  Min: {np.min(ch1_data):.2f} dBm")
        print(f"  Max: {np.max(ch1_data):.2f} dBm")
        print(f"  Mean: {np.mean(ch1_data):.2f} dBm")
        
        # Generate wavelength array
        wavelengths = np.linspace(START_NM, STOP_NM, len(ch1_data))
        
        # Show first and last few points
        print("\nFirst 5 points:")
        for i in range(min(5, len(ch1_data))):
            print(f"  {wavelengths[i]:.3f} nm: {ch1_data[i]:.3f} dBm")
        
        print("\nLast 5 points:")
        for i in range(max(0, len(ch1_data)-5), len(ch1_data)):
            print(f"  {wavelengths[i]:.3f} nm: {ch1_data[i]:.3f} dBm")
    else:
        print("ERROR: No data retrieved!")
    
    # Final error check
    print("\n--- Final Error Check ---")
    check_errors(inst)
    
    # --------------------------------------------------------------------------
    # CLEANUP
    # --------------------------------------------------------------------------
    print("\n--- Cleanup ---")
    write_cmd(inst, "SOUR0:WAV:SWE:STAT STOP")
    write_cmd(inst, "SENS1:FUNC:STOP")
    
    print("\n" + "="*50)
    print("TEST COMPLETE")
    print("="*50)
    
    return wavelengths, ch1_data, ch2_data if ch2_data is not None else None


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    print("Lambda Sweep Test Script")
    print("========================")
    print("\nThis script expects you to provide an instrument instance.")
    print("Example usage:")
    print("  import pyvisa")
    print("  rm = pyvisa.ResourceManager()")
    print("  inst = rm.open_resource('GPIB0::20::INSTR')")
    print("  wavelengths, ch1_data, ch2_data = test_lambda_sweep(inst)")
    print("\nOr modify this script to include your VISA setup.")
    
    import pyvisa
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource('GPIB0::20::INSTR')  
    inst.timeout = 30000  # 30 second timeout
    wavelengths, ch1_data, ch2_data = test_lambda_sweep(inst)

    import matplotlib.pyplot as plt
    plt.plot(wavelengths, ch1_data, label='Channel 1')
    plt.plot(wavelengths, ch2_data, label='Channel 2')
    plt.xlabel('Wavelength (nm)')
    plt.ylabel('Power (dBm)')
    plt.title('Lambda Sweep Results')
    plt.legend()
    plt.show()