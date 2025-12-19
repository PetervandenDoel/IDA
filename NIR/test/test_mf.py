import ctypes
from ctypes import *
import numpy as np
import matplotlib.pyplot as plt
import time

# --------------------------------------------------------------------------------------
# Load hp816x DLL
# --------------------------------------------------------------------------------------
dll = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")  

def check(session, st, msg=""):
    if st != 0:
        buf = create_string_buffer(256)
        dll.hp816x_error_message(session, st, buf)
        raise RuntimeError(f"{msg}: {buf.value.decode()}")
    else:
        print(f'{msg}: Passed')


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

dll.hp816x_error_message.argtypes = [
    c_int32, c_int32, c_char_p 
]
dll.hp816x_error_message.restype = c_int32


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
        check(session, st, f"getChannelLocation failed for PWM {pwm}")

        mapping.append((pwm, slot.value, head.value))
    return mapping


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
        c_double(0.5),
        c_int32(0),
        c_int32(0),
        c_int32(n_pwm),      # dynamic
        c_double(start),
        c_double(stop),
        c_double(step),
        byref(num_points),
        byref(num_arrays)
    )
    print('Doe we pre check')
    check(session, st, "prepare MF failed")

    N = num_points.value
    A = num_arrays.value

    wavelength = (c_double * N)()
    power_arrays = [(c_double * N)() for _ in range(A)]

    print('Execute')
    st = dll.hp816x_executeMfLambdaScan(session, wavelength)
    check(session, st, "execute failed")

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
        check(session, st, f"getLambdaScanResult ch {i} failed")

        pow_out[i, :] = pw[:]

    return wl_out, pow_out


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    sessions = []
    session_1 = c_int32() 
    session_2 = c_int32()
    st = dll.hp816x_init(b"GPIB0::4::INSTR", 1, 0, byref(session_1))
    check(session_1, st, "init failed")
    sessions.append(session_1)
    dll.hp816x_registerMainframe(session_1)

    st = dll.hp816x_init(b"GPIB0::20::INSTR", 1, 0, byref(session_2))
    check(session_2, st, "init failed")
    sessions.append(session_2)
    dll.hp816x_registerMainframe(session_2)

    time.sleep(10)

    # detect PWM channels
    n_pwms = []
    for sesh in sessions:
        n_pwm = c_uint32()
        dll.hp816x_getNoOfRegPWMChannels_Q(sesh, byref(n_pwm))
        n_pwm = n_pwm.value
        print(n_pwm)
        n_pwms.append(n_pwm)

    for i, sesh in enumerate(sessions):
        mapping = get_pwm_map(sesh, n_pwms[i])
        print(i, sesh, "\n")
        print(mapping)

        # (pwmIndex, slot, head)
    
    # for sesh in sessions:
        
    # wl_man, pw_man = run_mf_scan(session, n_pwm, mapping)
    # print('Does this print')
    for sesh in sessions:
        dll.hp816x_unregisterMainframe(sesh)
        dll.hp816x_close(sesh)



    # plt.plot(wl_man*1e9, pw_man[0])
    # if pw_man.shape[0] > 1:
    #     plt.plot(wl_man*1e9, pw_man[1])
    #     # plt.plot(wl_man*1e9, pw_man[2])
    #     # plt.plot(wl_man*1e9, pw_man[3])
    # plt.title(f"Manual Range ({RANGE} dBm)")
    # plt.xlabel("Wavelength (nm)")
    # plt.ylabel("dBm")

    # plt.tight_layout()
    # plt.show()


if __name__ == "__main__":
    main()
