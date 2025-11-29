import ctypes
from ctypes import *
import numpy as np
import matplotlib.pyplot as plt
import time

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
dll.hp816x_setInitialRangeParams.argtypes = [
    c_int32, c_int32, c_uint16,
    c_double, c_double
]

dll.hp816x_get_PWM_powerRange_Q.argtypes = [
    c_int32, c_int32, c_int32,
    POINTER(c_uint16), POINTER(c_double)
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
        st = dll.hp816x_setInitialRangeParams (
            session,
            pwm,       # PWMChannel
            0,       # reset to defualt
            c_double(range_dbm),
            c_double(0)  # Decremint
        )
        check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(1)
        st = dll.hp816x_set_PWM_powerRange(
            session,
            slot,       # slot number
            head,       # channelNumber
            0,          # Manual mode
            c_double(range_dbm)  # For auto test
        )
        check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(0.15)

def apply_auto_ranging(session, mapping):
    """Apply Autoranging by querying range value detected by autorange"""
    for pwm, slot, head in mapping:
        time.sleep(1)
        st = dll.hp816x_setInitialRangeParams(
            session,
            pwm,       # PWMChannel
            0,       # reset to defualt
            c_double(-20.0),
            c_double(0)  # Decremint
        )
        check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(1)
        # For each pwm, set to auto ranging, get the range value, then reapply manual ranging
        st = dll.hp816x_set_PWM_powerRange(
            session,
            slot,       # slot number
            head,       # channelNumber
            1,          # Manual mode
            c_double(0.0)  # For auto test
        )
        check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(1)
        rangeMode = c_uint16()
        powerRange = c_double()
        st = dll.hp816x_get_PWM_powerRange_Q(
            session,
            slot,
            head,
            byref(rangeMode),
            byref(powerRange)
        )
        time.sleep(0.15)
        # Retrieve powerRange value
        range_dbm = powerRange.value
        print("Autorange value: ", range_dbm)

        st = dll.hp816x_set_PWM_powerRange(
            session,
            slot,       # slot number
            head,       # channelNumber
            0,          # Manual mode
            c_double(range_dbm)  # For auto test
        )
        check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(0.15)


def run_mf_scan(session, n_pwm, mapping):
    """Prepare + execute + fetch MF scan."""
    start = 1500e-9
    stop = 1580e-9
    step = 1e-11

    num_points = c_uint32()
    num_arrays = c_uint32()
    print('Prepare scan')
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

    print('Apply ranging')
    # apply_manual_ranging(session, mapping, range_dbm=-20.0)
    apply_auto_ranging(session, mapping)

    N = num_points.value
    A = num_arrays.value

    wavelength = (c_double * N)()
    power_arrays = [(c_double * N)() for _ in range(A)]

    print('Execute')
    st = dll.hp816x_executeMfLambdaScan(session, wavelength)
    check(st, "execute failed")

    wl_out = np.array(wavelength[:])
    pow_out = np.zeros((A, N))

    for i in range(A):
        pw = power_arrays[i]
        wl = (c_double * N)()
        print('Retrieve')
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

    # # 1) Baseline scan (auto range)
    # wl_auto, pw_auto = run_mf_scan(session, n_pwm)

    # 2) Manual range
    # apply_manual_ranging(session, mapping, range_dbm=-20.0)

    wl_man, pw_man = run_mf_scan(session, n_pwm, mapping)

    dll.hp816x_unregisterMainframe(session)
    dll.hp816x_close(session)



    plt.plot(wl_man*1e9, pw_man[0])
    if pw_man.shape[0] > 1:
        plt.plot(wl_man*1e9, pw_man[1])
        plt.plot(wl_man*1e9, pw_man[2])
        plt.plot(wl_man*1e9, pw_man[3])
    plt.title("Manual Range (-30 dBm)")
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("dBm")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
