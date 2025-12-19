import ctypes
from ctypes import *
import numpy as np
import time

# --------------------------------------------------------------------------------------
# Load hp816x DLL
# --------------------------------------------------------------------------------------
dll = ctypes.WinDLL(
    r"C:\Program Files\IVI Foundation\VISA\Win64\Bin\hp816x_64.dll"
)

# ==============================================================================
# Prototypes (UNCHANGED)
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

dll.hp816x_error_message.argtypes = [c_int32, c_int32, c_char_p]

# ==============================================================================
# Helpers
# ==============================================================================

def check(session, st, msg=""):
    if st != 0:
        buf = create_string_buffer(256)
        dll.hp816x_error_message(session, st, buf)
        raise RuntimeError(f"{msg}: {buf.value.decode()}")
    print(f"[OK] {msg}")


def get_pwm_map(session, n_pwm):
    """Global MF PWM enumeration"""
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
        check(session, st, f"getChannelLocation pwm={pwm}")

        mapping.append((pwm, mf.value, slot.value, head.value))
    return mapping


def run_mf_scan(session, n_pwm):
    """Prepare + execute + fetch MF scan (single session only)"""

    start = 1500e-9
    stop  = 1520e-9
    step  = 2e-11

    num_points = c_uint32()
    num_arrays = c_uint32()

    st = dll.hp816x_prepareMfLambdaScan(
        session,
        c_int32(0),        # dBm
        c_double(0.0),     # TLS power
        c_int32(0),        # HIGHPOW
        c_int32(0),        # 1 scan
        c_int32(n_pwm),    # ALL PWMs
        c_double(start),
        c_double(stop),
        c_double(step),
        byref(num_points),
        byref(num_arrays)
    )
    check(session, st, "prepare MF lambda scan")

    N = num_points.value
    A = num_arrays.value

    print(f"MF scan reports {A} arrays, {N} points")

    wl_buf = (c_double * N)()
    st = dll.hp816x_executeMfLambdaScan(session, wl_buf)
    check(session, st, "execute MF lambda scan")

    wl_nm = np.array(wl_buf[:]) * 1e9
    powers = []

    for i in range(A):
        pw = (c_double * N)()
        wl_dummy = (c_double * N)()

        st = dll.hp816x_getLambdaScanResult(
            session,
            c_int32(i),
            c_int32(1),
            c_double(-80.0),
            pw,
            wl_dummy
        )
        check(session, st, f"getLambdaScanResult array={i}")

        powers.append(np.array(pw[:]))

    return wl_nm, powers


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    # ---- open two sessions ----
    ses_laser = c_int32()
    ses_det   = c_int32()

    check(
        ses_laser,
        dll.hp816x_init(b"GPIB0::4::INSTR", 1, 0, byref(ses_laser)),
        "init laser frame"
    )

    check(
        ses_det,
        dll.hp816x_init(b"GPIB0::20::INSTR", 1, 0, byref(ses_det)),
        "init detector frame"
    )

    # ---- register BOTH ----
    dll.hp816x_registerMainframe(ses_laser)
    dll.hp816x_registerMainframe(ses_det)

    print("Registered both mainframes")
    time.sleep(2)

    # ---- GLOBAL PWM ENUMERATION (ONCE) ----
    n_pwm = c_uint32()
    dll.hp816x_getNoOfRegPWMChannels_Q(ses_laser, byref(n_pwm))
    n_pwm = n_pwm.value

    print(f"Total registered PWM channels: {n_pwm}")
    assert n_pwm == 4, f"Expected 4 PWMs, got {n_pwm}"

    mapping = get_pwm_map(ses_laser, n_pwm)

    print("\nGLOBAL PWM MAP")
    for pwm, mf, slot, head in mapping:
        print(f"PWM {pwm}: MF={mf}, SLOT={slot}, HEAD={head}")

    # ---- RUN MF SCAN (LASER SESSION ONLY) ----
    wl, powers = run_mf_scan(ses_laser, n_pwm)

    print("\nMF scan completed")
    for i, p in enumerate(powers):
        print(f"Array {i}: min={p.min():.2f} dBm, max={p.max():.2f} dBm")

    # ---- cleanup ----
    dll.hp816x_unregisterMainframe(ses_laser)
    dll.hp816x_unregisterMainframe(ses_det)

    dll.hp816x_close(ses_laser)
    dll.hp816x_close(ses_det)

    print("Done.")


if __name__ == "__main__":
    main()
