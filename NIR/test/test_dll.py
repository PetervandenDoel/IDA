import ctypes
from ctypes import *
import numpy as np

# --------------------------------------------------------------------------------------
# Load hp816x DLL
# --------------------------------------------------------------------------------------
dll = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")  

# Status helper
def err(st, msg=""):
    if st != 0:
        buf = create_string_buffer(256)
        dll.hp816x_error_message(st, buf)
        raise RuntimeError(f"{msg} (status {st}): {buf.value.decode()}")


# --------------------------------------------------------------------------------------
# Set up function prototypes we need
# --------------------------------------------------------------------------------------

dll.hp816x_init.argtypes  = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
dll.hp816x_init.restype   = c_int32

dll.hp816x_close.argtypes = [c_int32]
dll.hp816x_close.restype  = c_int32

dll.hp816x_registerMainframe.argtypes   = [c_int32]
dll.hp816x_unregisterMainframe.argtypes = [c_int32]

dll.hp816x_prepareMfLambdaScan.argtypes = [
    c_int32, c_int32, c_double, c_int32, c_int32,
    c_int32, c_double, c_double, c_double,
    POINTER(c_uint32), POINTER(c_uint32)
]

dll.hp816x_executeMfLambdaScan.argtypes = [
    c_int32,
    POINTER(c_double)
]

dll.hp816x_getLambdaScanResult.argtypes = [
    c_int32, c_int32, c_int32, c_double,
    POINTER(c_double), POINTER(c_double)
]


# --------------------------------------------------------------------------------------
# BEGIN: First-principles MF scan
# --------------------------------------------------------------------------------------

def mf_scan_basic():
    # --------------------------------------------------------
    # Step 1: Initialize mainframe
    # --------------------------------------------------------
    session = c_int32()
    st = dll.hp816x_init(b"GPIB0::20::INSTR", 1, 0, byref(session))
    err(st, "init failed")
    print("Initialized mainframe, session =", session.value)

    # --------------------------------------------------------
    # Step 2: Register mainframe for MF scanning
    # --------------------------------------------------------
    st = dll.hp816x_registerMainframe(session)
    err(st, "register MF failed")
    print("Mainframe registered")

    # --------------------------------------------------------
    # Step 3: Prepare MF scan
    # --------------------------------------------------------
    # Use defaults:
    # powerUnit = DBM = 0
    # power     = 0.0 dBm
    # output    = HIGH POWER = 0
    # num scans = 1 scan = 0
    # PWMChannels = 2 (dual-head PM)
    # start/stop = simple 1550 -> 1551 nm
    # step      = 1 pm

    start = 1550e-9
    stop  = 1551e-9
    step  = 1e-12

    num_points = c_uint32()
    num_arrays = c_uint32()

    st = dll.hp816x_prepareMfLambdaScan(
        session,
        c_int32(0),        # unit DBM
        c_double(0.0),     # power
        c_int32(0),        # HP output
        c_int32(0),        # one scan
        c_int32(2),        # two PWM channels (dual head)
        c_double(start),
        c_double(stop),
        c_double(step),
        byref(num_points),
        byref(num_arrays),
    )
    err(st, "prepare MF failed")

    print("Prepared MF scan:")
    print("  points =", num_points.value)
    print("  arrays =", num_arrays.value)

    # --------------------------------------------------------
    # Step 4: Allocate arrays
    # --------------------------------------------------------
    N = num_points.value
    A = num_arrays.value

    wavelength_array = (c_double * N)()
    power_arrays = [(c_double * N)() for _ in range(A)]

    # --------------------------------------------------------
    # Step 5: Execute MF scan
    # --------------------------------------------------------
    print("Executing MF scan...")
    st = dll.hp816x_executeMfLambdaScan(
        session,
        wavelength_array
    )
    err(st, "execute MF failed")
    print("MF scan executed")

    # --------------------------------------------------------
    # Step 6: Read each power meter channel
    # --------------------------------------------------------
    ALL_LAMBDA = np.zeros(N)
    ALL_POWER  = np.zeros((A, N))

    for ch in range(A):
        print(f"Reading PWM channel {ch}")
        pw_buf = power_arrays[ch]
        wl_buf = (c_double * N)()

        st = dll.hp816x_getLambdaScanResult(
            session,
            c_int32(ch),
            c_int32(0),             # no clipping
            c_double(-80.0),        # ignore
            pw_buf,
            wl_buf,
        )
        err(st, f"getLambdaScanResult channel {ch} failed")

        ALL_LAMBDA[:] = wl_buf[:]            # identical for all arrays
        ALL_POWER[ch, :] = pw_buf[:]

    # --------------------------------------------------------
    # Step 7: Cleanup
    # --------------------------------------------------------
    dll.hp816x_unregisterMainframe(session)
    dll.hp816x_close(session)

    return ALL_LAMBDA, ALL_POWER


# --------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    wl, pw = mf_scan_basic()
    print("Lambda:", wl[:10], "...")
    print("Power (CH0):", pw[0][:10], "...")
    print("Power (CH1):", pw[1][:10], "...")
