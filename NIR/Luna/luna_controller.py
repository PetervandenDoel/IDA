import subprocess
import time
import os
from typing import Tuple

import numpy as np

from NIR.hal.nir_hal import LaserHAL, PowerUnit, PowerReading


class LunaController(LaserHAL):
    """
    Luna Optical Vector Analyzer controller

    Communication:
        Luna OVA 5000 Software
        SendCmd.exe (TCP/IP or GPIB)
    """

    def __init__(
        self,
        ip: str = '10.2.137.4',
        port: str = '1',
        sendcmd_path: str = "SendCmd.exe"
    ):
        super().__init__()

        # Connection
        self.ip = ip
        self.port = port
        self.sendcmd = sendcmd_path

        # Internal state (nir-compatible)
        self.center_wavelength_nm = None
        self.scan_start_nm = None
        self.scan_stop_nm = None
        self.scan_step_nm = None

        self.output_enabled = False
        self.sweep_state = "IDLE"

    # ==================================================================
    # Internal SendCmd helpers
    # ==================================================================

    def _write(self, command: str) -> None:
        subprocess.call([self.sendcmd, command, self.ip, self.port])

    def _query(self, command: str) -> str:
        return subprocess.check_output(
            [self.sendcmd, command, self.ip, self.port]
        ).decode().strip()

    # ==================================================================
    # Connection management
    # ==================================================================

    def connect(self) -> bool:
        """
        *IDN?
        Chapter 8.3.1 - Standard Commands
        """
        try:
            _ = self._query("*IDN?")
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[LUNA] connect failed: {e}")
            self._is_connected = False
            return False

    def disconnect(self) -> bool:
        """
        Luna remote interface is stateless.
        """
        self._is_connected = False
        return True

    # ==================================================================
    # Laser output
    # ==================================================================

    def enable_output(self, enable: bool = True) -> bool:
        """
        SYST:LASE <0|1>
        Chapter 8.4.1 - OVA-only System Commands
        """
        self._write(f"SYST:LASE {1 if enable else 0}")
        self.output_enabled = enable
        return True

    def get_output_state(self) -> bool:
        return self.output_enabled

    # ==================================================================
    # Wavelength control
    # ==================================================================

    def set_wavelength(self, wavelength: float) -> bool:
        """
        CONF:CWL <nm>
        Chapter 8.4.2 - OVA-only Configuration Commands
        """
        self._write(f"CONF:CWL {wavelength}")
        self.center_wavelength_nm = wavelength
        return True

    def get_wavelength(self) -> float:
        """
        CONF:CWL?
        Chapter 8.4.2
        """
        val = float(self._query("CONF:CWL?"))
        self.center_wavelength_nm = val
        return val

    # ==================================================================
    # Power control (not supported)
    # ==================================================================

    def set_power(self, power: float, unit: PowerUnit = PowerUnit.DBM) -> bool:
        print("[LUNA] set_power not supported - ignoring")
        return True

    def get_power(self) -> Tuple[float, PowerUnit]:
        print("[LUNA] get_power not supported - returning dummy")
        return 0.0, PowerUnit.DBM

    # ==================================================================
    # Detector semantics (mapped to insertion loss)
    # ==================================================================

    def read_power(self, channel: int = 1) -> PowerReading:
        """
        Implemented as mean insertion loss over a short scan.

        SCAN
        FETC:MEAS? 0
        Chapter 8.4.3 - OVA-only Data Capture and Retrieval Commands
        """
        self._write("SCAN")

        for _ in range(100):
            if "1" in self._query("*OPC?"):
                break
            time.sleep(0.05)

        raw = self._query("FETC:MEAS? 0").splitlines()
        values = [float(v) for v in raw if v.strip()]
        mean_il = float(np.mean(values)) if values else 0.0

        return PowerReading(
            value=mean_il,
            unit=PowerUnit.DBM,  # documented as insertion loss
            wavelength=self.center_wavelength_nm,
        )

    def set_power_unit(self, unit: PowerUnit, channel: int = 1) -> bool:
        print("[LUNA] set_power_unit not supported - ignoring")
        return True

    def get_power_unit(self, channel: int = 1) -> PowerUnit:
        print("[LUNA] get_power_unit not supported - returning DBM")
        return PowerUnit.DBM

    def set_power_range(self, range_dbm: float, channel: int = 1) -> bool:
        print("[LUNA] set_power_range not supported - ignoring")
        return True

    def get_power_range(self, channel: int = 1) -> float:
        print("[LUNA] get_power_range not supported - returning 0")
        return 0.0

    def enable_autorange(self, enable: bool = True, channel: int = 1) -> bool:
        print("[LUNA] autorange not supported - ignoring")
        return True

    # ==================================================================
    # Sweep configuration
    # ==================================================================

    def set_sweep_range_nm(self, start_nm: float, stop_nm: float) -> None:
        """
        CONF:CWL, CONF:RANG
        Chapter 8.4.2
        """
        self.scan_start_nm = start_nm
        self.scan_stop_nm = stop_nm

        scan_range = stop_nm - start_nm
        center = start_nm + scan_range / 2.0

        self._write(f"CONF:CWL {center}")
        self._write(f"CONF:RANG {scan_range}")

        self.center_wavelength_nm = center

    def set_sweep_step_nm(self, step_nm: float) -> None:
        """
        Luna step size is implicit.
        Stored for interface compatibility only.
        """
        self.scan_step_nm = step_nm

    # ==================================================================
    # Sweep execution
    # ==================================================================

    def start_sweep(self) -> None:
        """
        SCAN
        Chapter 8.4.3
        """
        self.sweep_state = "SCANNING"
        self._write("SCAN")

    def stop_sweep(self) -> None:
        print("[LUNA] stop_sweep not supported - ignoring")
        self.sweep_state = "IDLE"

    def get_sweep_state(self) -> str:
        return self.sweep_state

    # ==================================================================
    # Lambda scan lifecycle
    # ==================================================================

    def configure_and_start_lambda_sweep(
        self,
        start_nm: float,
        stop_nm: float,
        step_nm: float,
        laser_power_dbm: float = -10,
        avg_time_s: float = 0.01,
    ) -> bool:
        self.set_sweep_range_nm(start_nm, stop_nm)
        self.set_sweep_step_nm(step_nm)
        self.enable_output(True)
        self.start_sweep()
        return True

    def execute_lambda_scan(self, timeout_s: float = 300) -> bool:
        """
        Poll *OPC?
        Chapter 8.3.1
        """
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if "1" in self._query("*OPC?"):
                self.sweep_state = "COMPLETE"
                return True
            time.sleep(0.2)

        print("[LUNA] execute_lambda_scan timeout")
        self.sweep_state = "ERROR"
        return True  # do not break upstream logic

    # ==================================================================
    # Data retrieval
    # ==================================================================

    def retrieve_scan_data(self):
        """
        SYST:SAVS + file reload
        Chapter 8.4.3
        """
        fname = os.path.join(self.data_dir, "luna_scan.txt")
        self._write(f"SYST:SAVS {fname}")

        data = np.loadtxt(fname, skiprows=9)

        wavelength = data[:, 0]
        insertion_loss = data[:, 2]
        phase = data[:, 7]

        return wavelength, insertion_loss, phase

    # ==================================================================
    # Optical sweep (primary public API)
    # ==================================================================

    def optical_sweep(
        self,
        start_nm: float,
        stop_nm: float,
        step_nm: float,
        laser_power_dbm: float,
        averaging_time_s: float = 0.02,
    ):
        """
        Luna-native optical sweep.
        :params 
        """
        self.configure_and_start_lambda_sweep(
            start_nm=start_nm,
            stop_nm=stop_nm,
            step_nm=step_nm,
            laser_power_dbm=laser_power_dbm,
            avg_time_s=averaging_time_s,
        )

        self.execute_lambda_scan()
        return self.retrieve_scan_data()

