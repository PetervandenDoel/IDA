from typing import Dict, List, Any, Optional
import pyvisa
import struct
from SMU.hal.smu_hal import SMUHal, SMUEventType  

# --- Helpers ---
_CHMAP = {"A": "smua", "B": "smub"}

def _chname(channel: str) -> str:
    c = channel.upper()
    if c not in _CHMAP: raise ValueError(f"channel must be 'A' or 'B', got {channel}")
    return _CHMAP[c]

class Keithley2600BController(SMUHal):
    def __init__(self, visa_address: str, nplc: float = 0.1, off_mode: str = "NORMAL"):
        super().__init__()
        self.addr = visa_address
        self.nplc = nplc
        self.off_mode = off_mode.upper()  # NORMAL | ZERO | HI-Z
        self.rm = None
        self.inst = None

    # --- lifecycle ---
    def connect(self) -> bool:
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(self.addr)
            self.inst.write_termination = "\n"
            self.inst.read_termination = "\n"
            
            # Do a light reset of per-channel state (no *RST).
            for ch in ("A", "B"):
                c = _chname(ch)
                self.inst.write(f"{c}.reset() {c}.nvbuffer1.clear()")
                # OFF mode configuration (predictable output-off behavior)
                if self.off_mode == "HI-Z":
                    self.inst.write(f"{c}.source.offmode = {c}.OUTPUT_HIGH_Z")
                elif self.off_mode == "ZERO":
                    self.inst.write(f"{c}.source.offmode = {c}.OUTPUT_ZERO")
                else:
                    self.inst.write(f"{c}.source.offmode = {c}.OUTPUT_NORMAL; {c}.source.offfunc = {c}.OUTPUT_DCVOLTS")
            self.connected = True
            self._emit_event(SMUEventType.CONFIG_CHANGED, {"idn": self.idn()})
            return True
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"connect", "error": str(e)})
            return False

    def disconnect(self) -> bool:
        try:
            for ch in ("A", "B"):
                c = _chname(ch)
                self.inst.write(f"{c}.source.output = {c}.OUTPUT_OFF")
            if self.inst: self.inst.close()
            if self.rm: self.rm.close()
            self.connected = False
            self._emit_event(SMUEventType.SMU_OFF, {"all": True})
            return True
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"disconnect", "error": str(e)})
            return False
    
    def idn(self) -> str:
        # keep as-is; useful for logging
        return self.inst.query("*IDN?").strip()

    def get_and_clear_errors(self) -> list[dict]:
        try:
            errs = self.get_errors()
            self.clear_errors()
            return errs
        except Exception as e:
            self._emit_event(
                SMUEventType.ERROR,
                {"where":"get_and_clear_errors", "error": str(e)}
                )
            return []

    def clear_errors(self) -> None:
        try:
            self.inst.write("errorqueue.clear()")
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"clear_errors", "error": str(e)})

    def get_errors(self) -> list[dict]:
        try:
            n = int(float(self.inst.query("print(errorqueue.count)")))
            errs = []
            for _ in range(n):
                code, msg, sev, node = self.inst.query("print(errorqueue.next())").strip().split("\t")
                errs.append({"code": int(code), "message": msg, "severity": int(sev), "node": int(node)})
            return errs
        except Exception as e:
            self._emit_event(SMUEventType.ERROR, {"where":"get_errors", "error": str(e)})
            return []
        
    def get_config(self) -> Dict:
        return {"address": self.addr, "nplc": self.nplc, "off_mode": self.off_mode}

    # --- getters (both channels) ---
    def get_current(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.measure.i())")) for ch in ("A","B")}  # SI A

    def get_current_limits(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.source.limiti)")) for ch in ("A","B")}  # SI A

    def get_voltage(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.measure.v())")) for ch in ("A","B")}  # SI V

    def get_voltage_limits(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.source.limitv)")) for ch in ("A","B")}  # SI V

    def get_resistance(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.measure.r())")) for ch in ("A","B")}  # SI ohms

    def get_power_limits(self) -> Dict[str, float]:
        return {ch: float(self.inst.query(f"print({_chname(ch)}.source.limitp)")) for ch in ("A","B")}  # SI W

    def get_state(self) -> Dict:
        return {
            "connected": self.connected,
            "idn": self.idn(),
            "limits": {
                "V": self.get_voltage_limits(),
                "I": self.get_current_limits(),
                "P": self.get_power_limits(),
            },
            "output": {ch: bool(int(float(self.inst.query(f"print({_chname(ch)}.source.output)") or "0"))) for ch in ("A","B")},
        }

    # --- setters (per-channel) ---
    def set_source_mode(self, mode: str, channel: str) -> bool:
        c = _chname(channel)
        if mode.upper() == "V" or mode.upper().startswith("VOLT"):
            self.inst.write(f"{c}.source.func = {c}.OUTPUT_DCVOLTS")
        else:
            self.inst.write(f"{c}.source.func = {c}.OUTPUT_DCAMPS")
        return True

    def set_current(self, val: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.leveli = {val}")
        return True

    def set_current_limit(self, lim: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.limiti = {lim}")
        return True

    def set_voltage(self, val: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.levelv = {val}")
        return True

    def set_voltage_limit(self, lim: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.limitv = {lim}")
        return True

    def set_power_limit(self, lim: float, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.limitp = {lim}")
        return True  # 2600B supports limitp (true power compliance)

    # --- output & level ) ---
    def output_on(self, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.output = {c}.OUTPUT_ON")
        self._emit_event(SMUEventType.SMU_ON, {"ch": channel})
        return True

    def output_off(self, channel: str) -> bool:
        c = _chname(channel)
        self.inst.write(f"{c}.source.output = {c}.OUTPUT_OFF")
        self._emit_event(SMUEventType.SMU_OFF, {"ch": channel})
        return True

    def output_level(self, output: float, channel: str) -> bool:
        # Set setpoint respecting current source mode
        c = _chname(channel)
        func = self.inst.query(f"print({c}.source.func)").strip()
        if "DCVOLTS" in func:
            self.inst.write(f"{c}.source.levelv = {output}")
        else:
            self.inst.write(f"{c}.source.leveli = {output}")
        return True

    # --- high-throughput IV sweep (single channel; dual via two calls) ---
    def iv_sweep(self,
                 start: float,
                 stop: float,
                 step: float,
                 channel: List[str],
                 type: str  # "voltage" or "current"
                 ) -> Dict[str, Any]:
        assert len(channel) == 1, "Use one channel per call to keep the buffer contract simple."
        ch = channel[0]
        c = _chname(ch)
        kind = type.lower()
        if kind not in ("voltage", "current"):
            raise ValueError("type must be 'voltage' or 'current'")

        # Compute count robustly and clamp the last point to 'stop'
        npts = int(round((stop - start) / step)) + 1
        if npts <= 1: raise ValueError("sweep requires at least 2 points")

        # Configure measure speed and buffers
        self.inst.write(f"""
            {c}.nvbuffer1.clear()
            {c}.nvbuffer1.appendmode = 1
            {c}.nvbuffer1.collectsourcevalues = 0
            {c}.measure.nplc = {self.nplc}
            {c}.measure.count = 1""")

        # Select source mode
        if kind == "voltage":
            self.inst.write(f"{c}.source.func = {c}.OUTPUT_DCVOLTS")
            level_field = "levelv"
        else:
            self.inst.write(f"{c}.source.func = {c}.OUTPUT_DCAMPS")
            level_field = "leveli"

        # Build and run the TSP sweep on instrument
        # We write a compact for-loop to minimize I/O (no host sleeps).
        tsp = [f"for x = {start}, {stop}, {step} do",
               f"  {c}.source.{level_field} = x",
               "  delay(0)",  # use NPLC as integration; set dwell here if needed
               f"  {c}.measure.i({c}.nvbuffer1)" if kind == "voltage" else f"  {c}.measure.v({c}.nvbuffer1)",
               "end"]
        self.inst.write("\n".join(tsp))

        # Prepare binary fetch: REAL64, little-endian (manual format.data/byteorder)
        self.inst.write("format.data = format.REAL64")             # double precision binary :contentReference[oaicite:1]{index=1}
        self.inst.write("format.byteorder = format.LITTLEENDIAN")  # choose host endianness          :contentReference[oaicite:2]{index=2}

        # One response message with all data (printbuffer contract)
        # printbuffer(startIndex, endIndex, buffer.readings)      (manual)   :contentReference[oaicite:3]{index=3}
        resp = self.inst.query_binary_values(f"printbuffer(1, {c}.nvbuffer1.n, {c}.nvbuffer1.readings)",
                                             datatype="d", container=list)  # 'd' -> REAL64

        # Compose outputs
        if kind == "voltage":
            V = [start + i*step for i in range(npts)]
            I = resp[:npts]
        else:
            I = [start + i*step for i in range(npts)]
            V = resp[:npts]
        t = [0.0]*npts  # If you want timestamps, enable collecttimestamps; default stays off (manual) :contentReference[oaicite:4]{index=4}

        out = {"V": V, "I": I, "t": t, "meta": {"npts": npts, "start": start, "stop": stop, "step": step, "nplc": self.nplc, "type": kind, "channel": ch}}
        self._emit_event(SMUEventType.IV_SWEEP, {"channel": ch, "npts": npts})
        return out
