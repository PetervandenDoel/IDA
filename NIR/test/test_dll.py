import ctypes
from ctypes import *
import numpy as np

# --------------------------------------------------------------------------------------
# Load hp816x DLL
# --------------------------------------------------------------------------------------
dll = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")  

def err(st, msg=""):
    if st != 0:
        buf = create_string_buffer(256)
        dll.hp816x_error_message(st, buf)
        raise RuntimeError(f"{msg} (status {st}): {buf.value.decode()}")


# --------------------------------------------------------------------------------------
# Function prototypes
# --------------------------------------------------------------------------------------

dll.hp816x_init.argtypes  = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
dll.hp816x_close.argtypes = [c_int32]

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

dll.hp816x_getNoOfRegPWMChannels_Q.argtypes = [
    c_int32, POINTER(c_uint32)
]


# --------------------------------------------------------------------------------------
# CHANNEL LOCATION HELPER (optional debug)
# --------------------------------------------------------------------------------------
def debug_get_channel_locations(session, max_channels=16):
    print("=== MF CHANNEL MAP ===")
    for pwm in range(max_channels):
        mf = c_int32()
        slot = c_int32()
        head = c_int32()

        st = dll.hp816x_getChannelLocation(
            session,
            c_int32(pwm),
            byref(mf),
            byref(slot),
            byref(head)
        )
        if st != 0:
            break

        print(f"PWM {pwm}: MF={mf.value}, slot={slot.value}, head={head.value}")
    print("=======================")


# --------------------------------------------------------------------------------------
# DYNAMIC MF SCAN
# --------------------------------------------------------------------------------------

def mf_scan_dynamic():
    # --------------------------------------------------------
    # Step 1: Initialize
    # --------------------------------------------------------
    session = c_int32()
    st = dll.hp816x_init(b"GPIB0::20::INSTR", 1, 0, byref(session))
    err(st, "init failed")

    print("Initialized session =", session.value)

    # --------------------------------------------------------
    # Step 2: Register
    # --------------------------------------------------------
    st = dll.hp816x_registerMainframe(session)
    err(st, "register MF failed")

    print("Mainframe registered.")

    # --------------------------------------------------------
    # Step 3: Find number of PWM channels
    # --------------------------------------------------------
    pwm_count = c_uint32()
    st = dll.hp816x_getNoOfRegPWMChannels_Q(session, byref(pwm_count))
    err(st, "getNoOfRegPWMChannels failed")

    N_PWM = pwm_count.value
    print(f"Registered PWM channels = {N_PWM}")

    if N_PWM == 0:
        raise RuntimeError("ERROR: No PWM channels registered — MF scan impossible.")

    # (Optional) Show mapping
    debug_get_channel_locations(session, max_channels=N_PWM)

    # --------------------------------------------------------
    # Step 4: Prepare MF scan dynamically
    # --------------------------------------------------------
    start = 1550e-9
    stop  = 1551e-9
    step  = 1e-12

    num_points = c_uint32()
    num_arrays = c_uint32()

    st = dll.hp816x_prepareMfLambdaScan(
        session,
        c_int32(0),        # dBm
        c_double(0.0),     # TLS power
        c_int32(0),        # optical output = high power
        c_int32(0),        # one scan
        c_int32(N_PWM),    # USE DETECTED NUMBER HERE
        c_double(start),
        c_double(stop),
        c_double(step),
        byref(num_points),
        byref(num_arrays)
    )
    err(st, "prepare MF failed")

    print("Prepare OK:")
    print("  datapoints =", num_points.value)
    print("  arrays     =", num_arrays.value)

    # --------------------------------------------------------
    # Step 5: Allocate arrays
    # --------------------------------------------------------
    N = num_points.value
    A = num_arrays.value

    wavelength = (c_double * N)()
    power_arrays = [(c_double * N)() for _ in range(A)]

    # --------------------------------------------------------
    # Step 6: Execute
    # --------------------------------------------------------
    print("Executing MF scan...")
    st = dll.hp816x_executeMfLambdaScan(session, wavelength)
    err(st, "execute MF failed")

    print("Execution OK.")

    # --------------------------------------------------------
    # Step 7: Read out all N_PWM channels
    # --------------------------------------------------------
    ALL_LAMBDA = np.zeros(N)
    ALL_POWER = np.zeros((A, N))

    for ch in range(A):
        pw_buf = power_arrays[ch]
        wl_buf = (c_double * N)()

        st = dll.hp816x_getLambdaScanResult(
            session,
            c_int32(ch),
            c_int32(0),
            c_double(-80),
            pw_buf,
            wl_buf
        )
        err(st, f"getLambdaScanResult ch {ch} failed")

        ALL_LAMBDA[:] = wl_buf[:]
        ALL_POWER[ch, :] = pw_buf[:]
        print(f"Read channel {ch}")

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------
    dll.hp816x_unregisterMainframe(session)
    dll.hp816x_close(session)

    return ALL_LAMBDA, ALL_POWER


# --------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------
if __name__ == "__main__":
    wl, pw = mf_scan_dynamic()
    print("Wavelength:", wl[:10], "...")
    print("Power[0]:", pw[0][:10], "...")
