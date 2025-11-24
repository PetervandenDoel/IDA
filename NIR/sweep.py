import ctypes
import numpy as np
import pyvisa
import pandas as pd
from ctypes import (c_double,
                    c_int32,
                    c_uint32,
                    c_uint16,
                    c_char,
                    c_char_p,
                    POINTER,
                    byref,
                    create_string_buffer)
from typing import Optional
from tqdm import tqdm
import time

import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)

"""
This class currently has a few working implemenations and variations
Its purpose it to take Multi and Single frame sweeps for a set of channels.
I included some default settings for the 8164B w/ 81635 A PWM and 8160 TLS

For Single Frame:
    - I recommend using lambda_scan2 for now
      it is roughly 10 s faster than the 
      original / seg
    - Bobby has shown that the other one also
      works if you are a traditionalist

For Multiframe:
    - You must pass your sessions that can be
      created from the class XXXXX tbd

There are a few recommendations that I can make 
that I did not have time to try out for efficiency
purposes:

    - The scans revert the settings back and do not 
      persist the settings, so the ref, range must
      be reset at each stitching segment. This is 
      slow. A possible solution could be having 
      default settings in a Watt format, since
      each lambda sweep defaults back to those
      during the sweep.
    - Rewrite this code in C/C++ 
    - I do not recommend using the VISA calls directly
      and implementing your own lambda sweep. Esp if
      you are using internal triggering.

Cameron Basara, 2025
"""

class HP816xLambdaScan:
    def __init__(self):
        # Load the HP 816x library
        self.lib = ctypes.WinDLL("C:\\Program Files\\IVI Foundation\\VISA\\Win64\\Bin\\hp816x_64.dll")  # or .lib path
        self.visa_lib = ctypes.WinDLL("visa32.dll")
        self.session = None
        self.connected = False
        self._setup_function_prototypes()
        self.instrument = None
        self._cancel = False

    def _setup_function_prototypes(self):
        ###################################################
        # # -*- coding: utf-8 -*-
        # import ctypes
        # ViChar = ctypes.c_char
        # ViInt8 = ctypes.c_int8
        # ViInt16 = ctypes.c_int16
        # ViUInt16 = ctypes.c_uint16
        # ViInt32 = ctypes.c_int32
        # ViUInt32 = ctypes.c_uint32
        # ViInt64 = ctypes.c_int64
        # ViString = ctypes.c_char_p
        # ViReal32 = ctypes.c_float
        # ViReal64 = ctypes.c_double
        # # Types that are based on other visatypes
        # ViBoolean = ViUInt16
        # VI_TRUE = ViBoolean(True)
        # VI_FALSE = ViBoolean(False)
        # ViStatus = ViInt32
        # ViSession = ViUInt32
        # ViAttr = ViUInt32
        # ViConstString = ViString
        # ViRsrc = ViString
        ###################################################
        # hp816x_init
        self.lib.hp816x_init.argtypes = [c_char_p, c_int32, c_int32, POINTER(c_int32)]
        self.lib.hp816x_init.restype = c_int32

        # Error/utility functions (so we can actually read human messages)
        ViSession = c_int32
        ViStatus = c_int32
        self.lib.hp816x_error_message.argtypes = [ViSession, ViStatus, POINTER(c_char)]
        self.lib.hp816x_error_message.restype = ViStatus
        self.lib.hp816x_error_query.argtypes = [ViSession, POINTER(c_int32), POINTER(c_char)]
        self.lib.hp816x_error_query.restype = ViStatus
        self.lib.hp816x_errorQueryDetect.argtypes = [ViSession, c_int32]  # VI_TRUE/VI_FALSE
        self.lib.hp816x_errorQueryDetect.restype = ViStatus
        self.lib.hp816x_dcl.argtypes = [ViSession]
        self.lib.hp816x_dcl.restype = ViStatus
        self.lib.hp816x_reset.argtypes = [ViSession]
        self.lib.hp816x_reset.restype = ViStatus
        self.lib.hp816x_registerMainframe.argtypes = [ViSession]
        self.lib.hp816x_registerMainframe.restype = ViStatus

        # --- Single-frame Lambda Scan (TLS + up to 8 power arrays returned in one call) ---
        #    int hp816x_prepareLambdaScan(
        #      ViSession, ViInt32 powerUnit, ViReal64 power, ViInt32 opticalOutput,
        #      ViInt32 numberOfScans, ViInt32 PWMChannels,
        #      ViReal64 startWavelength, ViReal64 stopWavelength, ViReal64 stepSize,
        #      ViUInt32* numberOfDatapoints, ViUInt32* numberOfArrays);
        self.lib.hp816x_prepareLambdaScan.argtypes = [
            c_int32,        # ViSession
            c_int32,        # powerUnit (0=dBm, 1=W)
            c_double,       # power (TLS setpoint)
            c_int32,        # opticalOutput (0=HIGHPOW, others per frame)
            c_int32,        # numberOfScans (0->1 scan, 1->2 scans, ...)
            c_int32,        # PWMChannels (COUNT of enabled arrays)
            c_double,       # startWavelength (m)
            c_double,       # stopWavelength  (m)
            c_double,       # stepSize (m)
            POINTER(c_uint32),  # numberOfDatapoints
            POINTER(c_uint32),  # numberOfArrays
        ]
        self.lib.hp816x_prepareLambdaScan.restype = c_int32

        #    int hp816x_executeLambdaScan(
        #      ViSession, ViReal64* wl,
        #      ViReal64* p1, ViReal64* p2, ViReal64* p3, ViReal64* p4,
        #      ViReal64* p5, ViReal64* p6, ViReal64* p7, ViReal64* p8);
        self.lib.hp816x_executeLambdaScan.argtypes = [
            c_int32,                # ViSession
            POINTER(c_double),      # wl buffer
            POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double),
            POINTER(c_double), POINTER(c_double), POINTER(c_double), POINTER(c_double),
        ]
        self.lib.hp816x_executeLambdaScan.restype = c_int32

        # hp816x_prepareMfLambdaScan
        self.lib.hp816x_prepareMfLambdaScan.argtypes = [
            c_int32,  # session ViSession
            c_int32,  # unit ViInt32
            c_double,  # power ViReal64
            c_int32,  # optical output ViInt32
            c_int32,  # number of scans ViInt32
            c_int32,  # PWM channels ViInt32
            c_double,  # start wavelength ViReal64
            c_double,  # stop wavelength ViReal64
            c_double,  # step size ViReal64
            POINTER(c_uint32),  # number of datapoints ViUInt32
            POINTER(c_uint32)  # number of value arrays ViUInt32
        ]
        self.lib.hp816x_prepareMfLambdaScan.restype = c_int32

        # hp816x_executeMfLambdaScan
        self.lib.hp816x_executeMfLambdaScan.argtypes = [c_int32, POINTER(c_double)]
        self.lib.hp816x_executeMfLambdaScan.restype = c_int32

        # hp816x_getLambdaScanResult
        self.lib.hp816x_getLambdaScanResult.argtypes = [
            c_int32, c_int32, c_int32, c_double, POINTER(c_double), POINTER(c_double)
        ]
        self.lib.hp816x_getLambdaScanResult.restype = c_int32

        # hp816x_get_PWM_referenceValue_Q
        self.lib.hp816x_set_PWM_referenceValue.argtypes = [
            c_int32, c_int32, c_int32, c_double, c_double
        ]
        self.lib.hp816x_set_PWM_referenceValue.restype = c_int32

        self.lib.hp816x_set_PWM_referenceSource.argtypes = [
            c_int32, c_int32, c_int32, c_int32, c_int32, c_int32, c_int32
        ]
        self.lib.hp816x_set_PWM_referenceSource.restype = c_int32

        self.lib.hp816x_get_PWM_referenceValue_Q.argtypes = [
            c_int32, c_int32, c_int32,
            POINTER(c_int32), POINTER(c_double), POINTER(c_double)
        ]
        self.lib.hp816x_get_PWM_referenceValue_Q.restype = c_int32
        
        self.lib.hp816x_get_PWM_referenceSource_Q.argtypes = [
            c_int32, c_int32, c_int32,
            POINTER(c_int32), POINTER(c_int32), POINTER(c_int32),
            POINTER(c_int32)
        ]
        self.lib.hp816x_get_PWM_referenceSource_Q.restype = c_int32

        self.lib.hp816x_setInitialRangeParams.argtypes = [
            c_int32, c_int32, c_uint16, c_double, c_double
        ]
        self.lib.hp816x_setInitialRangeParams.restype = c_int32
        
        # hp816x_get_PWM_powerRange_Q
        self.lib.hp816x_get_PWM_powerRange_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_uint16), POINTER(c_double)
        ]
        self.lib.hp816x_get_PWM_powerRange_Q.restype = c_int32

        self.lib.hp816x_set_PWM_powerRange.argtypes = [
            c_int32, c_int32, c_int32, c_uint16, c_double
        ]
        self.lib.hp816x_set_PWM_powerRange.restype = c_int32

        self.lib.hp816x_set_PWM_powerUnit.argtypes = [
            c_int32, c_int32, c_int32, c_int32
        ]
        self.lib.hp816x_set_PWM_powerUnit.restype = c_int32

    def _err_msg(self, status):
        if not self.session:
            return f"(no session) status={status}"
        buf = create_string_buffer(512)
        # Driver/VISA message
        self.lib.hp816x_error_message(self.session, status, buf)
        msg = buf.value.decode(errors="replace")
        # Try instrument FIFO too (if any)
        inst_code = c_int32(0)
        buf2 = create_string_buffer(512)
        if self.lib.hp816x_error_query(self.session, byref(inst_code), buf2) == 0 and inst_code.value != 0:
            msg += f" | Instrument Error {inst_code.value}: {buf2.value.decode(errors='replace')}"
        return msg

    def clear_fifo(self):
        inst_code = c_int32()
        buf = create_string_buffer(512)
        # Drain errors
        while True:
            self.lib.hp816x_error_query(
                self.session,
                byref(inst_code),
                buf)
            if inst_code.value == 0:
                # Success code
                break

    @staticmethod
    def _round_to_pm_grid(value_nm: float, step_pm: float) -> float:
        pm = step_pm
        return round((value_nm * 1000.0) / pm) * (pm / 1000.0)

    def connect(self):
        try:
            session = c_int32()
            # self.rm = pyvisa.ResourceManager()
            visa_address = "GPIB0::20::INSTR"
            queryID = 1
            result = self.lib.hp816x_init(
                visa_address.encode(), queryID, 0, byref(session)
            )
            error_msg = create_string_buffer(256)  # 256 byte buffer
            self.lib.hp816x_error_message(session.value, result, error_msg)
            logging.debug(f"result: {result}, error: {error_msg.value.decode('utf-8')}")

            if result == 0:
                self.session = session.value
                self.lib.hp816x_errorQueryDetect(self.session, 1)  # VI_TRUE
                self.lib.hp816x_registerMainframe(self.session)
                self.connected = True
                return True
        except Exception as e:
            logging.error(f"[LSC] Connection error: {e}")
            return False

    def lambda_scan_mf(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                       power_dbm: float = 3.0, num_scans: int = 0, channels: list = [0, 1]):
        if not self.session:
            raise RuntimeError("Not connected to instrument")
        ##############################################################
        # Addendum
        # To obtain a higher precision, the Tunable Laser Source
        # is set 1 nm before the Start Wavelength, this means,
        # you have to choose a Start Wavelength 1 nm greater than
        # the minimum possible wavelength. Also, the wavelength
        # sweep is actually started 90 pm befo re the Start Wavelength
        #  and ends 90 pm after the Stop Wavelength, this means, you
        # have to choose a Stop Wavelength 90 pm less than
        # the maximum possible wavelength.
        ###############################################################
        # hp816x_prepareLambdaScan(
        #     ViSession ihandle, ViInt32 powerUnit,
        #     ViReal64 power, ViInt32 opticalOutput,
        #     ViInt32 numberofScans, ViInt32 PWMChannels,
        #     ViReal64 startWavelength, ViReal64 stopWavelength,
        #     ViReal64 stepSize, ViUInt32 numberofDatapoints,
        #     ViUInt32 numberofChannels);
        ###############################################################
        # 81635A:
        #   Power range: +10 to -80dBm
        #   Wavelength range 800 nm – 1650 nm
        ###############################################################
        self._cancel = False  # unflag
        # Constain values to limits if out of range
        start_nm = 1490 if start_nm < 1490 else start_nm
        stop_nm = 1640 if stop_nm > 1640 else stop_nm
        step_pm = 0.1 if step_pm < 0.1 else step_pm

        # Convert to meters
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_size = step_pm * 1e-12

        # Build uniform grid
        step_nm = step_pm / 1000.0
        n_target = int(round((float(stop_nm) - float(start_nm)) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # Stitching params
        max_points_per_scan = 20001
        guard_pre_pm = 90.0
        guard_post_pm = 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too large for guard-banded segmentation (eff_points_budget < 2).")

        pts_est = n_target
        segments = int(np.ceil(pts_est / float(eff_points_budget)))
        if segments < 1:
            segments = 1

        # Preallocate outputs
        out_by_ch = {ch: np.full(n_target, np.nan, dtype=np.float64) for ch in channels}

        # Segment loop
        bottom = float(start_nm)
        for seg in tqdm(range(segments), desc="Lambda Scan Stitching", unit="seg"):
            if self._cancel: break
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))

            bottom_r = bottom
            top_r = top

            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            result = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                0,  # dBm
                power_dbm,
                0,  # High power
                num_scans,
                len(channels),  # expose all requested arrays
                bottom_r * 1e-9,
                top_r * 1e-9,
                step_pm * 1e-12,
                byref(num_points_seg),
                byref(num_arrays_seg)
            )
            if result != 0:
                raise RuntimeError(f"Prepare scan failed: {result} :: {self._err_msg(result)}")

            points_seg = int(num_points_seg.value)
            wavelengths_seg = (c_double * points_seg)()

            result = self.lib.hp816x_executeMfLambdaScan(self.session, wavelengths_seg)
            if result != 0:
                raise RuntimeError(f"Execute scan failed: {result} :: {self._err_msg(result)}")

            # Wavelengths (nm), guard trim, grid index map
            wl_seg_nm_full = np.ctypeslib.as_array(wavelengths_seg, shape=(points_seg,)).astype(np.float64) * 1e9
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue
            wl_seg_nm = wl_seg_nm_full[mask]
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]

            # Per-array fetch into preallocated grid
            for ch in channels:
                buf = (c_double * points_seg)()
                res = self.lib.hp816x_getLambdaScanResult(self.session, int(ch), 1, -90.0, buf, wavelengths_seg)
                if res != 0:
                    continue
                pwr_full = np.ctypeslib.as_array(buf, shape=(points_seg,)).astype(np.float64)
                pwr_seg = pwr_full[mask][valid]
                if pwr_seg.size != idx.size:
                    m = min(pwr_seg.size, idx.size)
                    if m <= 0:
                        continue
                    out_by_ch[ch][idx[:m]] = pwr_seg[:m]
                else:
                    out_by_ch[ch][idx] = pwr_seg

            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm

        # Guarantee last sample is filled
        for ch in channels:
            if n_target >= 2 and np.isnan(out_by_ch[ch][-1]):
                nz = np.where(~np.isnan(out_by_ch[ch]))[0]
                if nz.size:
                    out_by_ch[ch][-1] = out_by_ch[ch][nz[-1]]

        channels_dbm = [out_by_ch[ch] for ch in channels]
        return {
            'wavelengths_nm': wl_target,
            'channels': channels,
            'channels_dbm': channels_dbm,
            'num_points': int(n_target)
        }
    
    def lambda_scan_mf2(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                    power_dbm: float = 3.0, num_scans: int = 0, channels: list = (1, 2),
                    args: list = (1, -30.0, None)):
        """
        Completed multi-frame Lambda scan using prepare/execute + per-channel result fetch.
        Same signature/return shape as your lambda_scan(...).
    
        args packs 3-tuples repeating: [slot, ref_dbm, range_dbm_or_None, ...]
          - ref_dbm is used in RELATIVE mode (internal)
          - range_dbm_or_None -> None means AUTO, otherwise MANUAL full-scale (dBm)
    
        Returns:
            {
              'wavelengths_nm': wl_target (np.ndarray float64),
              'channels': channels (list as passed in),
              'channels_dbm': [np.ndarray for each channel in channels order],
              'num_points': int,
            }
        """
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        self._cancel = False  # unflag

        # 81635A specs
        start_nm = max(1490.0, float(start_nm))
        stop_nm  = min(1640.0, float(stop_nm))
        if stop_nm <= start_nm:
            raise ValueError("stop_nm must be > start_nm")
        step_pm  = max(0.1, float(step_pm))
    
        # ---- TLS power in dBm (powerUnit=0 here) ----
        # Keep it sane for 81608A (example): [-20, +13] dBm
        power_dbm = float(power_dbm)
        if power_dbm < -20.0: power_dbm = -20.0
        if power_dbm >  13.0: power_dbm =  13.0
    
        # ---- Build the uniform target grid we will fill/stitch into ----
        step_nm = step_pm / 1000.0
        n_target = int(round((stop_nm - start_nm) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm
    
        # ---- Segmentation with guard-bands ----
        max_points_per_scan = 20001
        guard_pre_pm  = 90.0
        guard_post_pm = 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points  = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too small for guard-banded segmentation (eff_points_budget < 2)")
    
        segments = int(np.ceil(n_target / float(eff_points_budget)))
        if segments < 1:
            segments = 1
    
        # ---- Preallocate outputs (by channel label) ----
        out_by_ch = {ch: np.full(n_target, np.nan, dtype=np.float64) for ch in channels}
    
        # ---- Helpers for re-applying PM settings AFTER prepare ----
        def _ok(status, ctx):
            if status != 0:
                raise RuntimeError(f"{ctx} failed: {self._err_msg(status)}")
    
        def _pm_set_unit_dbm(slot, ch):
            _ok(self.lib.hp816x_set_PWM_powerUnit(self.session, c_int32(slot), c_int32(ch), c_int32(0)),
                f"set unit dBm s{slot} ch{ch}")
    
        def _pm_set_range(slot, ch, manual_dbm):
            # mode: 0=MANUAL, 1=AUTO
            if manual_dbm is None:
                _ok(self.lib.hp816x_set_PWM_powerRange(self.session, c_int32(slot), c_int32(ch),
                                                       c_uint16(1), c_double(0.0)),
                    f"set AUTO range s{slot} ch{ch}")
            else:
                _ok(self.lib.hp816x_set_PWM_powerRange(self.session, c_int32(slot), c_int32(ch),
                                                       c_uint16(0), c_double(float(manual_dbm))),
                    f"set MAN range s{slot} ch{ch}={manual_dbm} dBm")
    
        def _pm_set_ref_rel_internal(slot, ch, ref_dbm):
            # measureMode=1 RELATIVE, referenceSource=0 INTERNAL
            _ok(self.lib.hp816x_set_PWM_referenceSource(self.session, c_int32(slot), c_int32(ch),
                                                        c_int32(1), c_int32(0), c_int32(0), c_int32(0)),
                f"set REF REL/INT s{slot} ch{ch}")
            if ref_dbm is not None:
                _ok(self.lib.hp816x_set_PWM_referenceValue(self.session, c_int32(slot), c_int32(ch),
                                                           c_double(float(ref_dbm)), c_double(0.0)),
                    f"set REF value s{slot} ch{ch}={ref_dbm} dBm")
    
        # ---- Segment loop ----
        bottom = float(start_nm)
        for _seg in tqdm(range(segments), desc="MF Lambda Scan", unit="seg"):
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))
    
            # Requested sub-span (no guard in the request; mainframe handles edges)
            bottom_r = bottom
            top_r    = top
    
            # ---- PREPARE (MF) ----
            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            st = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                c_int32(0),                 # powerUnit: 0 = dBm for TLS setpoint
                c_double(power_dbm),        # TLS power setpoint (dBm)
                c_int32(0),                 # opticalOutput: 0 = HIGHPOW
                c_int32(int(num_scans)),    # numberOfScans (0->1 scan, as per your code)
                c_int32(len(channels)),     # PWMChannels: count of enabled arrays you want back
                c_double(bottom_r * 1e-9),  # start (m)
                c_double(top_r    * 1e-9),  # stop  (m)
                c_double(step_pm  * 1e-12), # step  (m)
                byref(num_points_seg),      # out: number of datapoints
                byref(num_arrays_seg)       # out: number of arrays returned by MF
            )
            _ok(st, "prepareMfLambdaScan")
    
            points_seg = int(num_points_seg.value)
            C          = int(num_arrays_seg.value)
            if C < 1 or points_seg < 2:
                # nothing to fetch; advance and continue
                bottom = top + step_nm
                continue
    
            # ---- REASSERT PM CONFIG AFTER PREPARE (critical) ----
            if args and len(args) >= 3:
                for i in range(0, len(args), 3):
                    slot = int(args[i])
                    ref_dbm = float(args[i + 1])
                    range_dbm = args[i + 2]  # None => AUTO
                    for chn in (0, 1):  # master/slave on this slot
                        _pm_set_unit_dbm(slot, chn)
                        _pm_set_range(slot, chn, range_dbm)
                        _pm_set_ref_rel_internal(slot, chn, ref_dbm)
                        time.sleep(0.3)
    
            # ---- EXECUTE (MF; wavelengths only) ----
            wl_buf = (c_double * points_seg)()
            st = self.lib.hp816x_executeMfLambdaScan(self.session, wl_buf)
            _ok(st, "executeMfLambdaScan")
    
            # ---- Guard-trim and index mapping into global grid ----
            wl_seg_nm_full = np.ctypeslib.as_array(wl_buf, shape=(points_seg,)).copy() * 1e9
    
            # Keep only [bottom_r, top_r] (drop ~90 pm internal guards)
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue
            wl_seg_nm = wl_seg_nm_full[mask]
    
            # Global target indices for these wavelengths
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]
            if idx.size == 0:
                bottom = top + step_nm
                continue
    
            # ---- Fetch per-channel power arrays and stitch ----
            # NOTE: MF returns arrays in "slot order": powerArray1..C.
            # Your 'channels' list represents labels you expect in output.
            # The driver call needs the powerArray index (1..C). We'll
            # fetch all returned arrays, then map them to your labels 1:1.
            # If your 'channels' aligns with MF array order, this is direct.
            # Otherwise, adjust here if you maintain a different mapping.
            for slot_i in range(1, C + 1):  # 1..C
                buf = (c_double * points_seg)()
                # interpolate flag (int): 1, minPower floor (dBm): -90.0
                st = self.lib.hp816x_getLambdaScanResult(
                    self.session,
                    c_int32(slot_i),    # MF array index (1..C)
                    c_int32(1),         # interpolate=1 (equidistant)
                    c_double(-90.0),    # floor
                    buf,                # out power
                    wl_buf              # wavelengths (pointer)
                )
                _ok(st, f"getLambdaScanResult array{slot_i}")
    
                pwr_full = np.ctypeslib.as_array(buf, shape=(points_seg,)).copy()
                pwr_seg  = pwr_full[mask][valid]
    
                # Map MF array index back to your channels list (1:1 position mapping)
                if slot_i <= len(channels):
                    ch_label = channels[slot_i - 1]
                    if pwr_seg.size != idx.size:
                        m = min(pwr_seg.size, idx.size)
                        if m > 0:
                            out_by_ch[ch_label][idx[:m]] = pwr_seg[:m]
                    else:
                        out_by_ch[ch_label][idx] = pwr_seg
    
            # ---- Next segment ----
            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm
    
        # ---- Guarantee the last sample is filled if the very last point was missed ----
        for ch in channels:
            arr = out_by_ch[ch]
            if np.isnan(arr[-1]) and n_target >= 2:
                arr[-1] = arr[-2]
    
        # ---- Pack outputs in the same shape as your lambda_scan(...) ----
        channels_dbm = [out_by_ch[ch] for ch in channels]
        return {
            "wavelengths_nm": wl_target,
            "channels": list(channels),
            "channels_dbm": channels_dbm,
            "num_points": int(n_target),
        }

    def lambda_scan(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                    power_dbm: float = 3.0, num_scans: int = 0, channels: list = [1],
                    args: list = (1,-30,None)):
        """
        Mainframe lambda scan, only to be taken with internal power detectors and TLS.
        Internal triggering is set as the default. Equally spaced datapoints in enabled
        by default, meaning interpolation is on.

        :param start_nm: Start wavelength in nm
        :param stop_nm: Stop wavelength in nm
        :param step_pm: Step size in pm
        :param power_dbm: Power in dBm
        :param num_scans: Number of scans, zero indexed up to 4 scans
        :param channels: List of channels to use, up to 4 channels, [1,2,3,4]
        :param args: input arguments for changing the reference and ranging before
                      a sweep has been taken. Use these parameter naming convention,
                      should be taken from shared memory config. If more than 1 channel,
                      group *args into 3 pairs, eg. lambda_scan(..., args = [1,-80, -10, 2, -70, -20])
                      :param channel[int]: master/slave channel slot
                      :param ref[float]: reference value in dBm (PWM relative internal)
                      :param rang[float]: range value in dBm, if None => autorange

        return: Dict {
            'wavelengths_nm': wl_target,
            'channels': channels,
            'channels_dbm': channels_dbm, # List of np array measurements per channel
            'num_points': int(n_target)
        }
        """
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        self._cancel = False  # unflag

        # Constrain to instrument limits
        start_nm = 1490 if start_nm < 1490 else start_nm
        stop_nm = 1640 if stop_nm > 1640 else stop_nm
        step_pm = 0.1 if step_pm < 0.1 else step_pm
        # 2.06279e-007 to 13.5241;
        if power_dbm < 3e-7: power_dbm = 3e-7
        elif power_dbm > 13.5: power_dbm = 13.5

        # Convert to meters for DLL
        step_nm = step_pm / 1000.0
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_m = step_pm * 1e-12

        # Uniform output grid
        n_target = int(round((float(stop_nm) - float(start_nm)) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # Segmentation (accounting for 90 pm guard)
        max_points_per_scan = 20001
        guard_pre_pm, guard_post_pm = 90.0, 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too large for guard-banded segmentation (eff_points_budget < 2).")

        pts_est = n_target
        segments = max(1, int(np.ceil(pts_est / float(eff_points_budget))))

        # Preallocate outputs
        out_by_ch = {ch: np.full(n_target, np.nan, dtype=np.float64) for ch in channels}

        bottom = float(start_nm)
        for seg in tqdm(range(segments), desc="Lambda Scan Stitching", unit="seg"):
            if self._cancel:
                raise RuntimeError("Cancelling Lambda Scan Stitching")
            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))

            bottom_r = bottom
            top_r = top

            # -------- SINGLE-FRAME PREP --------
            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            print('Preparing scan')
            result = self.lib.hp816x_prepareLambdaScan(
                self.session,
                0,  # powerUnit: 0=dBm
                c_double(power_dbm),  # TLS setpoint
                0,  # opticalOutput: 0=HIGHPOW (change if LOWSSE/BHR/BLR)
                c_int32(num_scans),  # 0->1 scan, 1->2 scans, etc.
                c_int32(len(channels)),  # PWMChannels = COUNT (NOT a mask)
                c_double(bottom_r * 1e-9),
                c_double(top_r * 1e-9),
                c_double(step_pm * 1e-12),
                byref(num_points_seg),
                byref(num_arrays_seg)
            )
            if result != 0:
                raise RuntimeError(f"Prepare scan failed: {result} :: {self._err_msg(result)}")
            
            
            # Prepare power ranging
            if len(args) > 0:
                print('Applying config')
                for i in range(0,len(args),3):
                    # For each 3-pair, configure ranging and ref for sweep
                    # Pull 3-pair out
                    chan = args[i] # Slot
                    ref_val = args[i+1]
                    range_val = args[i+2]
                    # Configure both channels (Master = CH1, Slave = CH2)
                    for ch_num in [0, 1]:  # hp816x_CHAN_1=0, hp816x_CHAN_2=1
                        try:
                            # Try
                            if ch_num == 0:
                                result = self.lib.hp816x_setInitialRangeParams(
                                    self.session,
                                    chan,
                                    c_uint16(0),  # No reset to default
                                    c_double(range_val if range_val is not None else -10.0),
                                    c_double(0.0)
                                )
                                if result != 0:
                                    raise RuntimeError(f"hp816x_setInitialRangeParams failed: {result} :: {self._err_msg(result)}")

                            time.sleep(3)
                            # # # --- Power Unit ---
                            # result = self.lib.hp816x_set_PWM_powerUnit(
                            #     self.session,
                            #     c_int32(chan),
                            #     c_int32(ch_num),
                            #     c_int32(0)  # 0: dBm, 1: Watt
                            # )
                            # if result != 0:
                            #     raise RuntimeError(f"hp816x_set_PWM_powerUnit: {result} :: {self._err_msg(result)}")
                            time.sleep(3)
                            # --- Power Range (Auto/Manual) ---
                            #
                            #  If you set the power Range to n dBm
                            #  You can measure (3+n, n-40) 
                            #  So if you set PowerRange to -30 dBm
                            #  you have a (-27, -70) dBm window w
                            #  a resolution of -70 dBm (0.1nW)
                            result = self.lib.hp816x_set_PWM_powerRange(
                                c_int32(self.session),
                                c_int32(chan),
                                c_int32(ch_num),
                                c_uint16(0 if range_val is not None else 1),
                                c_double(range_val if range_val is not None else 0.0),
                            )
                            time.sleep(1)
                            if result != 0:
                                raise RuntimeError(f"hp816x_set_PWM_powerRange: {result} :: {self._err_msg(result)}")
                            time.sleep(2)
                            # # --- Reference Source ---
                            # # Internal, Absolute (for mainframe lambda scan)
                            # result = self.lib.hp816x_set_PWM_referenceSource(
                            #     self.session,
                            #     chan,
                            #     ch_num,
                            #     0,  # hp816x_PWM_REF_ABSOLUTE (dBm)
                            #     0,  # hp816x_PWM_TO_REF (Internal)
                            #     0,  # Unused (slot)
                            #     0  # Unused (channel)
                            # )
                            # if result != 0:
                            #     raise RuntimeError(f"hp816x_set_PWM_referenceSource: {result} :: {self._err_msg(result)}")
                            # time.sleep(1)
                            # # --- Reference Value ---
                            # self.lib.hp816x_set_PWM_referenceValue(
                            #     self.session,
                            #     chan,
                            #     ch_num,
                            #     ref_val,  # internal reference value in dBm
                            #     0.0  # reference channel value (unused)
                            # )
                            # if result != 0:
                            #     raise RuntimeError(f"hp816x_set_PWM_referenceValue: {result} :: {self._err_msg(result)}")
                            # time.sleep(1)
                            # # DUT
                            
                        except:
                            print("Exception when setting detector windows in lambda sweep")
                            pass
            time.sleep(0.5)
            # self.check_both(1, 0)
            self.check_range(1,0)
            time.sleep(0.5)
            self.check_range(1,1)
            
            # Create segments
            points_seg = int(num_points_seg.value)
            C = int(num_arrays_seg.value)
            if C < 1:
                # Nothing enabled; skip this segment
                bottom = top + step_nm
                continue
            if C != len(channels):
                pass

            # -------- ALLOCATE BUFFERS FOR EXECUTE --------
            wl_buf = (c_double * points_seg)()

            # Prepare up to 8 power array pointers; fill first C, NULL the rest
            power_slots = [None] * 8
            power_arrays = {}
            for i in range(C):  # i: 0..C-1 maps to powerArray1..C
                arr = (c_double * points_seg)()
                power_slots[i] = arr
                power_arrays[i + 1] = arr  # keep by slot index (1-based)

            # Helper: NULL pointer for unused arrays
            from ctypes import POINTER
            def ptr_or_null(arr):
                return arr if arr is not None else POINTER(c_double)()

            # -------- SINGLE-FRAME EXECUTE (returns wl + all channels at once) --------
            print('Executing labmda scan')
            result = self.lib.hp816x_executeLambdaScan(
                self.session,
                wl_buf,
                ptr_or_null(power_slots[0]),
                ptr_or_null(power_slots[1]),
                ptr_or_null(power_slots[2]),
                ptr_or_null(power_slots[3]),
                ptr_or_null(power_slots[4]),
                ptr_or_null(power_slots[5]),
                ptr_or_null(power_slots[6]),
                ptr_or_null(power_slots[7]),
            )
            if result != 0:
                raise RuntimeError(f"Execute scan failed: {result} :: {self._err_msg(result)}")
            
            # time.sleep(0.5)
            # self.check_both(1, 0)
            # time.sleep(0.5)
            # self.check_both(1, 1)

            # -------- Convert wl + guard-trim + index into global grid --------
            wl_seg_nm_full = np.ctypeslib.as_array(wl_buf, shape=(points_seg,)).copy() * 1e9
            # Keep only [bottom_r, top_r] (drop 90 pm guards)
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue

            wl_seg_nm = wl_seg_nm_full[mask]
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]

            # -------- Map slot order (1..C) to 'channels' labels --------
            # Example: if channels=[2,4], powerArray1->ch=2, powerArray2->ch=4
            for slot_i, ch_label in enumerate(channels, start=1):
                if slot_i > C:
                    break
                arr = power_arrays[slot_i]
                pwr_full = np.ctypeslib.as_array(arr, shape=(points_seg,)).copy()  # copy: decouple
                pwr_seg = pwr_full[mask][valid]

                if pwr_seg.size != idx.size:
                    m = min(pwr_seg.size, idx.size)
                    if m > 0:
                        out_by_ch[ch_label][idx[:m]] = pwr_seg[:m]
                else:
                    out_by_ch[ch_label][idx] = pwr_seg

            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm

        # Fill last sample if instrument left it NaN after stitching
        DBM_FLOOR = -80 # dBm
        for ch in channels:
            np.clip(out_by_ch[ch], a_min=DBM_FLOOR, a_max=None, out=out_by_ch[ch])
            if n_target >= 2 and np.isnan(out_by_ch[ch][-1]):
                nz = np.where(~np.isnan(out_by_ch[ch]))[0]
                if nz.size:
                    out_by_ch[ch][-1] = out_by_ch[ch][nz[-1]]

        channels_dbm = [out_by_ch[ch] for ch in channels]
        return {
            'wavelengths_nm': wl_target,
            'channels': channels,
            'channels_dbm': channels_dbm,
            'num_points': int(n_target)
        }

    def lambda_scan2(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                    power_dbm: float = 3.0, num_scans: int = 0, channels: list = [1],
                    args: list = [1, -30, None], auto_range: Optional[float] = None):
        """
        MF-based mainframe lambda scan: same interface and stitching as lambda_scan,
        but uses hp816x_prepareMfLambdaScan + hp816x_executeMfLambdaScan + hp816x_getLambdaScanResult.
        """
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        self._cancel = False  # unflag

        # ---- SAME LIMITS / NORMALIZATION AS lambda_scan ----
        start_nm = 1490 if start_nm < 1490 else start_nm
        stop_nm = 1640 if stop_nm > 1640 else stop_nm
        step_pm = 0.1 if step_pm < 0.1 else step_pm
        # 2.06279e-007 to 13.5241;
        if power_dbm < 3e-7:
            power_dbm = 3e-7
        elif power_dbm > 13.5:
            power_dbm = 13.5

        step_nm = step_pm / 1000.0
        start_wl = start_nm * 1e-9
        stop_wl = stop_nm * 1e-9
        step_m = step_pm * 1e-12

        # Uniform output grid
        n_target = int(round((float(stop_nm) - float(start_nm)) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # Segmentation (accounting for 90 pm guard)
        max_points_per_scan = 20001
        guard_pre_pm, guard_post_pm = 90.0, 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too large for guard-banded segmentation (eff_points_budget < 2).")

        pts_est = n_target
        segments = max(1, int(np.ceil(pts_est / float(eff_points_budget))))

        # Preallocate outputs
        out_by_ch = {ch: np.full(n_target, np.nan, dtype=np.float64) for ch in channels}

        bottom = float(start_nm)
        for seg in tqdm(range(segments), desc="Lambda Scan Stitching", unit="seg"):
            if self._cancel:
                raise RuntimeError("Cancelling Lambda Scan Stitching")

            planned_top = bottom + (eff_points_budget - 1) * step_nm
            top = min(planned_top, float(stop_nm))

            bottom_r = bottom
            top_r = top

            # -------- MF PREP (pattern from lambda_scan_mf2) --------
            num_points_seg = c_uint32()
            num_arrays_seg = c_uint32()
            result = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                c_int32(0),              # powerUnit: 0 = dBm
                c_double(power_dbm),     # TLS setpoint
                c_int32(0),              # opticalOutput: 0 = HIGHPOW
                c_int32(num_scans),      # 0->1 scan, 1->2 scans, etc.
                c_int32(len(channels)),  # PWMChannels = COUNT, not mask
                c_double(bottom_r * 1e-9),
                c_double(top_r * 1e-9),
                c_double(step_pm * 1e-12),
                byref(num_points_seg),
                byref(num_arrays_seg)
            )
            if result != 0:
                raise RuntimeError(f"Prepare scan failed: {result} :: {self._err_msg(result)}")

            if len(args) > 0:
                for i in range(0, len(args), 3):
                    slot = args[i]      
                    ref_val = args[i+1]
                    range_val = args[i+2]
                    for ch_num in [0, 1]:  # hp816x_CHAN_1=0, hp816x_CHAN_2=1
                        try:
                            # Range (auto/manual)
                            result = self.lib.hp816x_set_PWM_powerRange(
                                c_int32(self.session),
                                c_int32(slot),
                                c_int32(ch_num),
                                c_uint16(0),
                                c_double(auto_range or 0.0), 
                            )
                            if result != 0:
                                raise RuntimeError(f"hp816x_set_PWM_powerRange failed: {result} :: {self._err_msg(result)}")
                            time.sleep(1)

                            # Try
                            print(
                                f's{slot}|cn{ch_num}\n',
                                f'RV: {range_val if range_val is not None else auto_range}'
                            )
                            result = self.lib.hp816x_setInitialRangeParams(
                                self.session,
                                slot,
                                c_uint16(0),  # No reset to default
                                c_double(range_val if range_val is not None else auto_range),
                                c_double(0.0)
                            )
                            if result != 0:
                                raise RuntimeError(f"hp816x_setInitialRangeParams failed: {result} :: {self._err_msg(result)}")

                            time.sleep(3)
                            # Power unit
                            result = self.lib.hp816x_set_PWM_powerUnit(
                                self.session,
                                c_int32(slot),
                                c_int32(ch_num),
                                c_int32(0)  # dBm
                            )
                            if result != 0:
                                raise RuntimeError(f"hp816x_set_PWM_powerUnit failed: {result} :: {self._err_msg(result)}")

                            time.sleep(0.15)
                            # Reference source (ABS + internal, same as original lambda_scan)
                            result = self.lib.hp816x_set_PWM_referenceSource(
                                self.session,
                                slot,
                                ch_num,
                                0,  # ABSOLUTE (dBm)
                                0,  # TO_REF internal
                                0,
                                0
                            )
                            if result != 0:
                                raise RuntimeError(f"hp816x_set_PWM_referenceSource failed: {result} :: {self._err_msg(result)}")
                            
                            time.sleep(0.15)
                            # Reference value
                            result = self.lib.hp816x_set_PWM_referenceValue(
                                self.session,
                                slot,
                                ch_num,
                                ref_val,
                                0.0
                            )
                            if result != 0:
                                raise RuntimeError(f"hp816x_set_PWM_referenceValue failed: {result} :: {self._err_msg(result)}")
                            time.sleep(0.15)

                        except Exception:
                            print("Exception when setting detector windows in lambda sweep")
                            pass

            # print('#############################')
            # print('PRE')
            # print('#############################')
            time.sleep(0.5)
            self.check_both(1, 0)
            time.sleep(0.5)
            self.check_both(1, 1)

            points_seg = int(num_points_seg.value)
            C = int(num_arrays_seg.value)
            if C < 1:
                bottom = top + step_nm
                continue
            if C != len(channels):
                # Optional: warn about mismatch
                pass

            # -------- MF EXECUTE (wavelengths only) --------
            wl_buf = (c_double * points_seg)()
            result = self.lib.hp816x_executeMfLambdaScan(
                self.session,
                wl_buf
            )
            if result != 0:
                raise RuntimeError(f"Execute scan failed: {result} :: {self._err_msg(result)}")

            # print('#############################')
            # print('POST')
            # print('#############################')
            # time.sleep(0.5)
            # self.check_both(1, 0)
            # time.sleep(0.5)
            # self.check_both(1, 1)

            # -------- GUARD TRIM + INDEXING (same as lambda_scan) --------
            wl_seg_nm_full = np.ctypeslib.as_array(wl_buf, shape=(points_seg,)).copy() * 1e9
            mask = (wl_seg_nm_full >= bottom_r - 1e-6) & (wl_seg_nm_full <= top_r + 1e-6)
            if not np.any(mask):
                bottom = top + step_nm
                continue

            wl_seg_nm = wl_seg_nm_full[mask]
            idx = np.rint((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]

            # -------- MF RESULT RETRIEVAL (0-based array index) --------
            # MF returns C arrays; valid indices = 0..C-1.
            for array_idx in range(C):  # 0..C-1
                buf = (c_double * points_seg)()
                result = self.lib.hp816x_getLambdaScanResult(
                    self.session,
                    c_int32(array_idx),   # <-- 0-based MF array index
                    c_int32(1),           # interpolate = 1
                    c_double(-80.0),      # minPower floor (dBm)
                    buf,
                    wl_buf
                )
                if result != 0:
                    raise RuntimeError(
                        f"getLambdaScanResult array{array_idx} failed: {result} :: {self._err_msg(result)}"
                    )

                pwr_full = np.ctypeslib.as_array(buf, shape=(points_seg,)).copy()
                pwr_seg = pwr_full[mask][valid]

                # Map MF array index 0..C-1 -> channels list 0..len-1
                if array_idx < len(channels):
                    ch_label = channels[array_idx]
                    if pwr_seg.size != idx.size:
                        m = min(pwr_seg.size, idx.size)
                        if m > 0:
                            out_by_ch[ch_label][idx[:m]] = pwr_seg[:m]
                    else:
                        out_by_ch[ch_label][idx] = pwr_seg

            if top >= float(stop_nm) - 1e-12:
                break
            bottom = top + step_nm

        # ---- SAME FINAL FILL / CLIP AS lambda_scan ----
        DBM_FLOOR = -80  # dBm
        for ch in channels:
            np.clip(out_by_ch[ch], a_min=DBM_FLOOR, a_max=0, out=out_by_ch[ch])
            if n_target >= 2 and np.isnan(out_by_ch[ch][-1]):
                nz = np.where(~np.isnan(out_by_ch[ch]))[0]
                if nz.size:
                    out_by_ch[ch][-1] = out_by_ch[ch][nz[-1]]

        channels_dbm = [out_by_ch[ch] for ch in channels]
        return {
            'wavelengths_nm': wl_target,
            'channels': channels,
            'channels_dbm': channels_dbm,
            'num_points': int(n_target)
        }

    def check_both(self, slot, chan):
        self.check_ref(slot, chan)
        self.check_range(slot, chan)
    
    def check_ref(self, slot, chan):
        # Referemce Source
        measureMode = c_int32()
        referenceSource = c_int32()
        SLOT = c_int32()
        CHANNEL = c_int32() 
        # Reference Value
        mode = c_int32()
        internal = c_double()
        refchan = c_double()
        source = self.lib.hp816x_get_PWM_referenceSource_Q(
            self.session, slot, chan, byref(measureMode), byref(referenceSource), 
            byref(SLOT), byref(CHANNEL)
        )
        if source!=0:
            raise RuntimeError(f"Get PWM reference source failed: {self._err_msg(source)}")
        time.sleep(0.15)
        v = self.lib.hp816x_get_PWM_referenceValue_Q(
            self.session, slot, chan, byref(mode), byref(internal), byref(refchan)
        )
        if v!=0:
            raise RuntimeError(f"Get PWM reference value failed: {self._err_msg(v)}")
        print(
            f"Check Ref on [{slot}|{chan}]\n",
            f"mode: {'abs' if measureMode.value == 0 else 'rel'}\n",
            f"source {'internal' if referenceSource.value == 0 else 'Channel'}\n",
            f"relative to: {SLOT.value}|{CHANNEL.value} and the internal ref val: {internal.value}\n"
        )

    def check_range(self, slot, chan):
        auto = c_uint16()
        rval = c_double()
        s = self.lib.hp816x_get_PWM_powerRange_Q(
            self.session, slot, chan, byref(auto), byref(rval)
        )
        if s!=0:
            raise RuntimeError(f"Get power range failed: {self._err_msg(s)}")
        print(
            f'Check Range on[{slot}|{chan}]\n',
            f'value: {rval.value} auto: {auto.value}\n',
            f'This implies a window from {rval.value + 3}-{rval.value - 40} dBm\n'
            # f'Autoranging ensures result has a displayed val between\n',
            # f'9%-100% of full scale --> ignore the value above as a res\n'
        )

    def cancel(self):
        self._cancel = True
        self.disconnect()
    def disconnect(self):
        if self.session:
            self.lib.hp816x_close(self.session)
            self.connected = None
