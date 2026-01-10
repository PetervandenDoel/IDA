#!/usr/bin/env python3

import time
import struct
import numpy as np


# =====================================================================
# CONFIGURATION (edit these)
# =====================================================================

# Sweep configuration
START_NM          = 1549.0
STOP_NM           = 1551.0
STEP_NM           = 0.01
SWEEP_SPEED_NM_S  = 10.0
POWER_DBM         = -10.0

# Detector averaging
AVG_TIME_S        = 0.001     # 1 ms averaging

# Module locations
TLS_SLOT          = 0         # SOUR0
PM_SLOT           = 1         # SENS1 (dual head)
PM_CHANNELS       = [1, 2]    # CHAN1, CHAN2

LASER_SETTLE_S    = 0.5
POST_SWEEP_WAIT_S = 0.4


# =====================================================================
# HELPERS
# =====================================================================

def write(inst, cmd):
    inst.write(cmd)

def query(inst, cmd):
    return inst.query(cmd).strip()

def read_binary_block(inst, word_format, size):
    """Reads definite-length SCPI binary block."""
    header = inst.read_bytes(1)
    if header != b'#':
        raise RuntimeError("Invalid SCPI binary header")

    digits = int(inst.read_bytes(1))
    length = int(inst.read_bytes(digits).decode())

    data = inst.read_bytes(length)

    # Try to read/flush the terminator (often '\n')
    try:
        inst.read_bytes(1)
    except:
        pass

    if length % size != 0:
        raise RuntimeError(
            f"Data length {length} not divisible by element size {size}"
        )

    n = length // size
    fmt = f"<{n}{word_format}"
    return np.array(struct.unpack(fmt, data))


def check_error(inst, ctx=""):
    err = query(inst, "SYST:ERR?")
    if not err.startswith("+0"):
        raise RuntimeError(f"Error after {ctx}: {err}")
    return err


# =====================================================================
# MAIN LAMBDA SCAN (TLS slot 0, dual head slot 1)
# =====================================================================

def lambda_scan(inst):
    """
    Performs a continuous lambda scan with lambda logging and returns:

    wavelengths_nm, ch1_dbm, ch2_dbm
    """

    # ---------------------------------------------------------------
    # CLEAR & BASE SETUP
    # ---------------------------------------------------------------
    write(inst, "*CLS")
    check_error(inst)

    # Turn off modulation (required for LLOG)
    write(inst, f"SOUR{TLS_SLOT}:AM:STAT OFF")

    # Configure power
    write(inst, f"SOUR{TLS_SLOT}:POW {POWER_DBM}DBM")
    write(inst, f"SOUR{TLS_SLOT}:POW:STAT ON")

    # Move TLS to start wavelength
    write(inst, f"SOUR{TLS_SLOT}:WAV {START_NM}NM")
    time.sleep(LASER_SETTLE_S)

    # ---------------------------------------------------------------
    # TLS SWEEP CONFIGURATION
    # ---------------------------------------------------------------
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:MODE CONT")
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:STAR {START_NM}NM")
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:STOP {STOP_NM}NM")
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:STEP {STEP_NM}NM")
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:SPE  {SWEEP_SPEED_NM_S}NM/S")

    # Enable lambda logging
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:LLOG 1")

    # Configure trigger output (required for LLOG)
    write(inst, "TRIG:CONF DEF")
    write(inst, f"TRIG{TLS_SLOT}:OUTP STFinished")

    check_error(inst, "TLS sweep setup")

    # ---------------------------------------------------------------
    # DETERMINE EXPECTED NUMBER OF TRIGGERS
    # ---------------------------------------------------------------
    expected = int(query(inst, f"SOUR{TLS_SLOT}:WAV:SWE:EXP?"))

    # ---------------------------------------------------------------
    # CONFIGURE POWER METERS (both channels)
    # ---------------------------------------------------------------
    center_nm = 0.5 * (START_NM + STOP_NM)

    for ch in PM_CHANNELS:
        write(inst, f"SENS{PM_SLOT}:CHAN{ch}:POW:WAV {center_nm}NM")
        write(inst, f"SENS{PM_SLOT}:CHAN{ch}:POW:UNIT DBM")
        write(inst, f"SENS{PM_SLOT}:CHAN{ch}:POW:RANG:AUTO 1")
        write(inst, f"SENS{PM_SLOT}:CHAN{ch}:POW:ATIM {AVG_TIME_S}S")

        write(inst, f"TRIG{PM_SLOT}:INP SME")
        write(inst, f"TRIG{PM_SLOT}:INP:REARM ON")

        write(inst,
              f"SENS{PM_SLOT}:CHAN{ch}:FUNC:PAR:LOGG {expected},{AVG_TIME_S}S")
        check_error(inst, f"PM CH {ch} setup")

    # ---------------------------------------------------------------
    # START LOGGING + SWEEP
    # ---------------------------------------------------------------
    for ch in PM_CHANNELS:
        write(inst, f"SENS{PM_SLOT}:CHAN{ch}:FUNC:STAT LOGG,START")

    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:STAT START")

    # ---------------------------------------------------------------
    # WAIT UNTIL LOGGING COMPLETE PER CHANNEL
    # ---------------------------------------------------------------
    complete = {ch: False for ch in PM_CHANNELS}

    while not all(complete.values()):
        for ch in PM_CHANNELS:
            if not complete[ch]:
                state = query(inst, f"SENS{PM_SLOT}:CHAN{ch}:FUNC:STATE?").upper()
                if "COMPLETE" in state:
                    complete[ch] = True
        time.sleep(0.05)

    # Let TLS finish up internal LLOG sequence
    time.sleep(POST_SWEEP_WAIT_S)

    # STOP sweep explicitly
    write(inst, f"SOUR{TLS_SLOT}:WAV:SWE:STAT STOP")

    # ---------------------------------------------------------------
    # RETRIEVE POWER LOG DATA (for CH1, CH2)
    # ---------------------------------------------------------------
    ch_power = {}
    for ch in PM_CHANNELS:
        write(inst, f"SENS{PM_SLOT}:CHAN{ch}:FUNC:RES?")
        ch_power[ch] = read_binary_block(inst, 'f', 4)

    # ---------------------------------------------------------------
    # RETRIEVE WAVELENGTHS (LLOG)
    # ---------------------------------------------------------------
    npts = int(query(inst, f"SOUR{TLS_SLOT}:READ:POIN? LLOG"))
    write(inst, f"SOUR{TLS_SLOT}:READ:DATA? LLOG")
    wl_m = read_binary_block(inst, 'd', 8)
    wl_nm = wl_m * 1e9  # Convert m → nm

    # ---------------------------------------------------------------
    # TRIM LENGTHS
    # ---------------------------------------------------------------
    N = min(len(wl_nm), *(len(ch_power[ch]) for ch in PM_CHANNELS))
    wl_nm = wl_nm[:N]
    ch1 = ch_power[1][:N]
    ch2 = ch_power[2][:N]

    check_error(inst, "final")

    return wl_nm, ch1, ch2
