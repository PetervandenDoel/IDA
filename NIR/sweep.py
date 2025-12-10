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
from math import ceil, floor, log10
from typing import Optional
from tqdm import tqdm
import time

import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)

from utils.progress_write_helpers import FileProgressTqdm, write_progress_file

"""
This class currently has a few working implemenations and variations
Its purpose it to take Multi and Single frame sweeps for a set of channels.
I included some default settings for the 8164B w/ 81635 A PWM and 8160 TLS
as well as some guards and such for the Iris (AMPEL 347) Stage.

For Single Frame:
    - I recommend using lambda_scan for now
      it is roughly 10 s faster than the 
      original / seg 
    - Bobby has shown that the other one also
      works 

For Multiframe:
    - tbd

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
    - I do not recommend using the VISA calls directly
      and implementing your own lambda sweep. Esp if
      you are using internal triggering. If you do,
      Rewrite this code in C/C++

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

        # Debug
        self.lib.hp816x_PWM_slaveChannelCheck.argtypes = [
            c_int32,  # ViSession
            c_int32,  # PWMSlot
            c_uint16,  # Check on/off
        ]
        self.lib.hp816x_PWM_slaveChannelCheck.restype = c_int32

        self.lib.hp816x_getChannelLocation.argtypes = [
            c_int32, c_int32, POINTER(c_int32), POINTER(c_int32), POINTER(c_int32)
        ]
        self.lib.hp816x_getChannelLocation.restype = c_int32

        self.lib.hp816x_getNoOfRegPWMChannels_Q.argtypes = [
            c_int32, POINTER(c_int32)
        ]

        # --- For Autoranging implementation ---
        self.lib.hp816x_PWM_fetchValue.argtypes = [
            c_int32, c_uint32, c_uint32, POINTER(c_double)
        ]
        self.lib.hp816x_PWM_fetchValue.restype = c_int32
        
        self.lib.hp816x_set_TLS_wavelength.argtypes = [
            c_int32, c_int32, c_int32, c_double
        ]
        self.lib.hp816x_get_PWM_powerUnit_Q.argtypes = [
            c_int32, c_int32, c_int32, POINTER(c_int32)
        ]
        self.lib.hp816x_get_PWM_powerUnit_Q.restype = c_int32

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
                # self.lib.hp816x_PWM_slaveChannelCheck(
                #     self.session, c_int32(1), c_uint16(1)
                # )
                self.connected = True
                return True
        except Exception as e:
            logging.error(f"[LSC] Connection error: {e}")
            return False
    
    def enumarate_slots(self):
        """ 
        For External nir controller usage
        Returns slot mapping
        """
        # --- Detect PWM channels, and enumerate ---
        # --- This will dynamically allocate PWM chns, heads, slots ---
        n_pwm = c_int32()
        self.lib.hp816x_getNoOfRegPWMChannels_Q(self.session, byref(n_pwm))
        n_pwm = n_pwm.value

        # list of 3 tuples -> PWMIndex, Slot, Head
        mapping = self.get_pwm_map(n_pwm)
        return mapping

    def lambda_scan_singleframe(self, start_nm: float = 1490, stop_nm: float = 1600, step_pm: float = 0.5,
                    power_dbm: float = 3.0, num_scans: int = 0, channels: list = [1],
                    args: list = (1, -30, None)):
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
    
    def lambda_scan(
        self,
        start_nm: float = 1490.0,
        stop_nm: float = 1600.0,
        step_pm: float = 0.5,
        power_dbm: float = 3.0,
        num_scans: int = 0,
        args: list | None = None
    ):
        # --- Safety Checks ---
        if not self.session:
            raise RuntimeError("Not connected to instrument")

        # --- Detect PWM channels, and enumerate ---
        # --- This will dynamically allocate PWM chns, heads, slots ---
        n_pwm = c_int32()
        self.lib.hp816x_getNoOfRegPWMChannels_Q(self.session, byref(n_pwm))
        n_pwm = n_pwm.value

        # --- Determine Detector settings using map ---
        # list of 3 tuples -> PWMIndex, Slot, Head
        # This will be passed with args into 
        # Apply ranging for each slot, head
        mapping = self.get_pwm_map(n_pwm)
        
        # --- Normalize sweep parameters ---
        start_nm = max(1490.0, float(start_nm))
        stop_nm = min(1640.0, float(stop_nm))
        if stop_nm <= start_nm:
            raise ValueError("stop_nm must be greater than start_nm")

        step_pm = max(0.1, float(step_pm))
        step_nm = step_pm / 1000.0
        step_m = step_pm * 1e-12

        power_dbm = float(power_dbm)
        if power_dbm < 3e-7:
            power_dbm = 3e-7
        if power_dbm > 13.5:
            power_dbm = 13.5

        # target wavelength grid (what we return)
        n_target = int(round((stop_nm - start_nm) / step_nm)) + 1
        wl_target = start_nm + np.arange(n_target, dtype=np.float64) * step_nm

        # segmentation + guard (TLS keeps some margin; we keep extra guard)
        max_points_per_scan = 20001
        guard_pre_pm, guard_post_pm = 90.0, 90.0
        guard_total_pm = guard_pre_pm + guard_post_pm
        guard_points = int(np.ceil(guard_total_pm / step_pm)) + 2
        eff_points_budget = max_points_per_scan - guard_points
        if eff_points_budget < 2:
            raise RuntimeError("Step too small for guard-banded segmentation")

        segments = max(1, int(np.ceil(n_target / float(eff_points_budget))))

        # --- allocate stitched output arrays ---
        # keyed by physical detector identity (slot, head)
        out_by_ch = {
            (slot, head): np.full(n_target, np.nan, dtype=np.float64)
            for (pwm, slot, head) in mapping
        }

        # --- Write tqdm progress to file for pb ---
        def progress_cb(percent, n, total, eta_seconds):
            write_progress_file(
                activity="Lambda Scan Stitching",
                percent=percent,
                eta_seconds=eta_seconds,
                n=n,
                total=total,
            )

        bottom_nm = float(start_nm)

        for _ in FileProgressTqdm(
            range(segments),
            desc="Lambda Scan Stitching",
            unit="seg",
            progress_cb=progress_cb,
        ):
            if self._cancel:
                raise RuntimeError("Cancelling Lambda Scan Stitching")

            planned_top = bottom_nm + (eff_points_budget - 1) * step_nm
            top_nm = min(planned_top, float(stop_nm))

            bottom_wl_m = bottom_nm * 1e-9
            top_wl_m = top_nm * 1e-9

            num_pts_seg = c_uint32()
            num_arrays_seg = c_uint32()

            # --- prepare MF scan (DLL) ---
            st = self.lib.hp816x_prepareMfLambdaScan(
                self.session,
                c_int32(0),                     # powerUnit: 0 = dBm
                c_double(power_dbm),            # TLS setpoint
                c_int32(0),                     # opticalOutput: 0 = HIGHPOW
                c_int32(int(num_scans)),        # numberOfScans (0 -> 1 scan)
                c_int32(n_pwm),                 # Dynamic num of PWM arrays
                c_double(bottom_wl_m),          # Start wl
                c_double(top_wl_m),             # Stop wl
                c_double(step_m),               # Step size
                byref(num_pts_seg),             # Ptr for Num of pts per seg
                byref(num_arrays_seg),          # Ptr for Num of array
            )
            self.check(st, "hp816x_prepareMfLambdaScan")

            points_seg = int(num_pts_seg.value)
            num_arrays = int(num_arrays_seg.value)
            if num_arrays < 1 or points_seg < 2:
                bottom_nm = top_nm + step_nm
                if bottom_nm >= stop_nm:
                    break
                continue

            # --- Apply settings based on mapping ---
            self.apply_ranging(mapping, args, bottom_wl_m, top_wl_m)

            # --- execute MF scan, get wavelengths ---
            wl_buf = (c_double * points_seg)()
            power_arrays = [(c_double * points_seg)()
                             for _ in range(num_arrays)]

            st = self.lib.hp816x_executeMfLambdaScan(self.session, wl_buf)
            self.check(st, "hp816x_executeMfLambdaScan")

            wl_seg_full_nm = (
                np.ctypeslib.as_array(wl_buf, shape=(points_seg,)).copy() * 1e9
            )

            # guard-trim to actual segment window
            mask = (
                (wl_seg_full_nm >= bottom_nm - 1e-6)
                & (wl_seg_full_nm <= top_nm + 1e-6)
            )
            if not mask.any():
                bottom_nm = top_nm + step_nm
                if bottom_nm >= stop_nm:
                    break
                continue

            wl_seg_nm = wl_seg_full_nm[mask]
            idx = np.round((wl_seg_nm - float(start_nm)) / step_nm).astype(np.int64)
            valid = (idx >= 0) & (idx < n_target)
            idx = idx[valid]
            if idx.size == 0:
                bottom_nm = top_nm + step_nm
                if bottom_nm >= stop_nm:
                    break
                continue

            # --- fetch power arrays for each MF array index 0..num_arrays ---
            for array_idx in range(0, num_arrays):
                buf = (c_double * points_seg)()
                st = self.lib.hp816x_getLambdaScanResult(
                    self.session,
                    c_int32(array_idx),   # MF array index 
                    c_int32(1),           # Apply clipping
                    c_double(-80.0),      # min floor dBm
                    buf,
                    wl_buf,
                )
                self.check(st, f"hp816x_getLambdaScanResult array{array_idx}")

                pwr_full = np.ctypeslib.as_array(buf, shape=(points_seg,)).copy()
                pwr_seg = pwr_full[mask][valid]

                # map MF array index -> mapping index
                map_idx = array_idx 

                # retrieve physical detector identity
                pwm, slot, head = mapping[map_idx]
                key = (slot, head)

                # stitch partial segment into global storage
                if pwr_seg.size != idx.size:
                    m = min(pwr_seg.size, idx.size)
                    if m > 0:
                        out_by_ch[key][idx[:m]] = pwr_seg[:m]
                else:
                    out_by_ch[key][idx] = pwr_seg

            if top_nm >= stop_nm - 1e-12:
                break

            bottom_nm = top_nm + step_nm

        # --- post-processing / clipping ---
        dbm_floor = -80.0
        for key in out_by_ch:
            np.clip(out_by_ch[key], a_min=dbm_floor, a_max=0.0, out=out_by_ch[key])
            if n_target > 1 and np.isnan(out_by_ch[key][-1]):
                nz = np.where(~np.isnan(out_by_ch[key]))[0]
                if nz.size:
                    out_by_ch[key][-1] = out_by_ch[key][nz[-1]]

        return {
            "wavelengths_nm": wl_target,
            "power_dbm_by_detector": out_by_ch,
            "num_points": int(n_target),
        }

    def apply_ranging(self, mapping, args_list, btm_wl, top_wl):
        """
        Wrapper: decides whether each slot uses manual or auto ranging.
        For full_mapping pattern found in lambda_scan
        - If range_dbm is None -> autorange
        - Otherwise -> manual
        """
        args_dict = {}
        for slot, ref, range in args_list:
            args_dict[slot] = range

        for pwm, slot, head in mapping:
            range_dbm = args_dict.get(slot, 0.0)  # Default to 0 dBm
            if range_dbm is None:
                print(f'Applying Autoranging for slot: {slot}, {pwm},{head}')
                self.apply_auto_ranging(pwm, slot, head, (btm_wl, top_wl))
            else:
                print(f'Applying Manual Ranging for slot: {slot}, {pwm},{head}')
                self.apply_manual_ranging(pwm, slot, head, range_dbm)

    def apply_manual_ranging(self, pwm, slot, head, range_dbm):
        """Apply manual power ranging to all PWM channels."""
        st = self.lib.hp816x_setInitialRangeParams(
            self.session,
            pwm,       # PWMChannel
            0,       # reset to default 1 true, 0 false
            c_double(range_dbm),
            c_double(0)  # Decrement
        )
        self.check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(0.15)
        st = self.lib.hp816x_set_PWM_powerRange(
            self.session,
            slot,       # slot number
            head,       # channelNumber
            0,          # Manual mode
            c_double(range_dbm)  # For auto test
        )
        self.check(st, f"set_PWM_powerRange failed (slot {slot}, head {head})")
        time.sleep(0.15)

    def apply_auto_ranging(self, pwm, slot, head, wl_len):
        """
        Apply Autoranging by querying range value detected by autorange
        For values throughout the wavelength sweep
        """
        # --- Get wl span ---
        wl_span = float(wl_len[1]) - float(wl_len[0])
        steps = int(max(2, floor(wl_span / 5e-9)))
        wl_samples = np.linspace(wl_len[0], wl_len[1], steps)
        if wl_samples.size <= 1:
            # If no values are found, small reading
            # Take the bottom and top of wavelength
            wl_samples = [wl_len[0], wl_len[1]]

        # -- Step the span, fetch PWM readings ---
        pwm_list = []
        for wl in wl_samples:
            self.lib.hp816x_set_TLS_wavelength(
                self.session,
                c_int32(0),
                c_int32(3),  # Manual
                c_double(wl)  # in m
            )
            time.sleep(0.05)
            sample = c_double()
            self.lib.hp816x_PWM_fetchValue(
                self.session,
                slot,
                head,
                byref(sample)
            )
            # Get the power unit
            ptype = c_int32()
            self.lib.hp816x_get_PWM_powerUnit_Q(
                self.session,
                slot,
                head,
                byref(ptype)
            )
            if ptype.value == 1:
                sample = watts_to_dbm(sample.value)
                pwm_list.append(sample)
                continue
            pwm_list.append(sample.value)
        
        # Filter nan readings
        pwm_arr = np.array(pwm_list, dtype=float)
        pwm_arr = np.nan_to_num(pwm_arr, nan=-np.inf)

        # Filter -> sane readings
        get_sane = pwm_arr[pwm_arr > -70.0]
        final_arr = get_sane[get_sane <= 0.0]
        
        if len(final_arr) == 0:
            # We are in noise
            self.apply_manual_ranging(pwm, slot, head, -20.0)
            return
        
        # --- Determine range ---
        # Some cases the reading may span a larger range than 43 dBm
        # But those values will at LEAST be = 40 dBm if we have incredible 
        # Coupling; this is not a valid reading for autoranging. If a
        # but more realistically will be around 50 dBm or 60 dBm 
        # Which ends up being noise in most cases. 
        p_max = max(final_arr)
        range_val = ceil(p_max / 10) * 10
        self.apply_manual_ranging(pwm, slot, head, range_val)

    def get_pwm_map(self, n_pwm):
        """Return list of tuples (pwmIndex, slot, head)."""
        mapping = []
        for pwm in range(n_pwm):
            mf = c_int32()
            slot = c_int32()
            head = c_int32()

            st = self.lib.hp816x_getChannelLocation(
                self.session,
                c_int32(pwm),
                byref(mf),
                byref(slot),
                byref(head)
            )
            self.check(st, f"getChannelLocation failed for PWM {pwm}")

            mapping.append((pwm, slot.value, head.value))
        return mapping
    
    def check_both(self, slot, chan):
        """ Call check ref and check range """
        self.check_ref(slot, chan)
        self.check_range(slot, chan)
    
    def check_ref(self, slot, chan):
        """ Check reference values, source for slot, chan """
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
        """ Check Ranging for a slot, chan """
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
    
    def check(self, st, msg=""):
        if st != 0:
            buf = create_string_buffer(256)
            self.lib.hp816x_error_message(self.session, st, buf)
            raise RuntimeError(f"{msg}: {buf.value.decode()}")
    
    def find_pwm_channel(self, slot: int, channel: int) -> int:
        """
        Return the MF PWM channel index (0..999) for a given (slot, channel).
        Internally queries hp816x_getChannelLocation for each MF PWM index.
        """
        mf_number = c_int32()
        slot_number = c_int32()
        channel_number = c_int32()

        for pwm in range(5):
            result = self.lib.hp816x_getChannelLocation(
                self.session,
                c_int32(pwm),
                byref(mf_number),
                byref(slot_number),
                byref(channel_number)
            )
            if result != 0:
                continue  # invalid index → skip
            print(f"{pwm} mfn: {mf_number.value} | sn: {slot_number.value} | chn: {channel_number.value}")

            if slot_number.value == slot and channel_number.value == channel:
                return pwm

    def cancel(self):
        self._cancel = True
        self.disconnect()

    def disconnect(self):
        if self.session:
            self.lib.hp816x_unregisterMainframe(self.session)
            self.lib.hp816x_close(self.session)
            self.connected = None

# --- Helpers ---
def watts_to_dbm(power_watts):
  """
  Converts power in Watts to dBm.

  Args:
    power_watts: The power in Watts (float).

  Returns:
    The power in dBm (float).
  """
  if power_watts <= 0:
    return np.nan
  
  power_mw = power_watts * 1000  # Convert Watts to milliwatts
  dbm = 10 * log10(power_mw)
  return dbm