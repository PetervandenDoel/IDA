import ctypes
from ctypes import *
import numpy as np

# --------------------------------------------------------------------------------------
# Load hp816x DLL
# --------------------------------------------------------------------------------------
dll = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")  

def check(st, msg=""):
    if st != 0:
        buf = create_string_buffer(256)
        dll.hp816x_error_message(st, buf)
        raise RuntimeError(f"{msg}: {buf.value.decode()}")


# ==============================================================================
# Prototypes
# ==============================================================================

dll.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
dll.hp816x_close.argtypes = [c_int32]

dll.hp816x_registerMainframe.argtypes = [c_int32]
dll.hp816x_unregisterMainframe.argtypes = [c_int32]

dll.hp816x_getNoOfRegPWMChannels_Q.argtypes = [c_int32, POINTER(c_uint32)]

dll.hp816x_getChannelLocation.argtypes = [
    c_int32,
    c_int32,
    POINTER(c_int32),
    POINTER(c_int32),
    POINTER(c_int32)
]

dll.hp816x_set_PWM_powerRange.argtypes = [
    c_int32, c_int32, c_int32,
    c_int16, c_double
]

dll.hp816x_prepareMfLambdaScan.argtypes = [
    c_int32, c_int32, c_double, c_int32, c_int32,
    c_int32, c_double, c_double, c_double,
    POINTER(c_uint32), POINTER(c_uint32)
]

dll.hp816x_executeMfLambdaScan.argtypes = [c_int32, POINTER(c_double)]

dll.hp816x_getLambdaScanResult.argtypes = [
    c_int32, c_int32, c_int32, c_double,
    POINTER(c_double), POINTER(c_double)
]


# ==============================================================================
# Helpers
# ==============================================================================
def get_pwm_map(session, n_pwm):
    """Return list of tuples (pwmIndex, slot, head)."""
    mapping = []
    for pwm in range(n_pwm):
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
        check(st, f"getChannelLocation failed for PWM {pwm}")

        mapping.append((pwm, slot.value, head.value))
    return mapping


def apply_manual_ranging(session, mapping, range_dbm):
    """Apply manual power ranging to all PWM channels."""
    for pwm, slot, head in mapping:
        st = dll.hp816x_set_PWM_powerRange(
            session,
            slot,       # slot number
            head,       # channelNumber
            0,          # Manual mode
            c_double(range_dbm)
        )
        check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")


def run_mf_scan(session, n_pwm):
    """Prepare + execute + fetch MF scan."""
    start = 1550e-9
    stop = 1551e-9
    step = 1e-12

    num_points = c_uint32()
    num_arrays = c_uint32()

    st = dll.hp816x_prepareMfLambdaScan(
        session,
        c_int32(0),
        c_double(0.0),
        c_int32(0),
        c_int32(0),
        c_int32(n_pwm),      # dynamic
        c_double(start),
        c_double(stop),
        c_double(step),
        byref(num_points),
        byref(num_arrays)
    )
    check(st, "prepare MF failed")

    N = num_points.value
    A = num_arrays.value

    wavelength = (c_double * N)()
    power_arrays = [(c_double * N)() for _ in range(A)]

    st = dll.hp816x_executeMfLambdaScan(session, wavelength)
    check(st, "execute failed")

    wl_out = np.array(wavelength[:])
    pow_out = np.zeros((A, N))

    for i in range(A):
        pw = power_arrays[i]
        wl = (c_double * N)()

        st = dll.hp816x_getLambdaScanResult(
            session,
            c_int32(i),
            c_int32(0),
            c_double(-80),
            pw,
            wl
        )
        check(st, f"getLambdaScanResult ch {i} failed")

        pow_out[i, :] = pw[:]

    return wl_out, pow_out


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    session = c_int32()
    st = dll.hp816x_init(b"GPIB0::20::INSTR", 1, 0, byref(session))
    check(st, "init failed")

    dll.hp816x_registerMainframe(session)

    # detect PWM channels
    n_pwm = c_uint32()
    dll.hp816x_getNoOfRegPWMChannels_Q(session, byref(n_pwm))
    n_pwm = n_pwm.value

    mapping = get_pwm_map(session, n_pwm)

    # 1) Baseline scan (auto range)
    wl_auto, pw_auto = run_mf_scan(session, n_pwm)

    # 2) Manual range
    apply_manual_ranging(session, mapping, range_dbm=-30.0)

    wl_man, pw_man = run_mf_scan(session, n_pwm)

    dll.hp816x_unregisterMainframe(session)
    dll.hp816x_close(session)

    # plot comparison
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.title("Auto Range")
    plt.plot(wl_auto*1e9, pw_auto[0], label="Ch0")
    if pw_auto.shape[0] > 1:
        plt.plot(wl_auto*1e9, pw_auto[1], label="Ch1")
    plt.ylabel("dBm")
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.title("Manual Range (-30 dBm)")
    plt.plot(wl_man*1e9, pw_man[0])
    if pw_man.shape[0] > 1:
        plt.plot(wl_man*1e9, pw_man[1])
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("dBm")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
