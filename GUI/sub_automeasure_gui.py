import datetime
import json
import os
import threading

from remi import App, start

from GUI.lib_gui import *

SHARED_PATH = os.path.join("database", "shared_memory.json")


class AutoSweepConfig(App):
    def __init__(self, *args, **kwargs):
        # File modification tracking
        self._user_stime = None
        self._first_check = True

        # Cached configuration
        self.sweep = {}
        self.finea = {}

        # Widgets
        self.power = None
        self.step_size = None
        self.start_wvl = None
        self.stop_wvl = None
        self.range_mode_dd = None
        self.manual_range = None
        self.ref_value = None
        self.primary_dd = None
        self.confirm_btn = None

        if "editing_mode" not in kwargs:
            super(AutoSweepConfig, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ---------------- REMI HOOKS ----------------

    def main(self):
        ui = self.construct_ui()
        self._load_from_shared()
        return ui

    def idle(self):
        """Reload settings if shared_memory.json changes."""
        try:
            stime = os.path.getmtime(SHARED_PATH)
        except FileNotFoundError:
            stime = None

        if self._first_check:
            self._user_stime = stime
            self._first_check = False
            return

        if stime != self._user_stime:
            self._user_stime = stime
            self._load_from_shared()

    # ---------------- UTIL ----------------

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    # ---------------- UI ----------------

    def construct_ui(self):
        root = StyledContainer(
            variable_name="auto_sweep_container",
            left=0,
            top=0,
            width=280,
            height=230,
        )

        y = 10
        row_h = 28

        # Power
        StyledLabel(
            container=root,
            text="Power",
            variable_name="power_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.power = StyledSpinBox(
            container=root,
            variable_name="power_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=0.0,
            min_value=-110,
            max_value=30,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="power_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Step size
        y += row_h
        StyledLabel(
            container=root,
            text="Step",
            variable_name="step_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.step_size = StyledSpinBox(
            container=root,
            variable_name="step_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=0.001,
            min_value=0,
            max_value=1000,
            step=0.001,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="step_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Start wavelength
        y += row_h
        StyledLabel(
            container=root,
            text="Start Wvl",
            variable_name="start_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.start_wvl = StyledSpinBox(
            container=root,
            variable_name="start_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=1540.0,
            min_value=0,
            max_value=2000,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="start_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Stop wavelength
        y += row_h
        StyledLabel(
            container=root,
            text="Stop Wvl",
            variable_name="stop_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.stop_wvl = StyledSpinBox(
            container=root,
            variable_name="stop_in",
            left=105,
            top=y,
            width=70,
            height=24,
            value=1580.0,
            min_value=0,
            max_value=2000,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="stop_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Range mode + manual range (for primary detector)
        y += row_h
        StyledLabel(
            container=root,
            text="Range",
            variable_name="range_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )

        self.range_mode_dd = StyledDropDown(
            container=root,
            text=["Auto", "Manual"],
            variable_name="range_mode_dd",
            left=105,
            top=y,
            width=70,
            height=24,
        )

        self.manual_range = StyledSpinBox(
            container=root,
            variable_name="manual_range",
            left=195,
            top=y,
            width=60,
            height=24,
            value=-10,
            min_value=-120,
            max_value=20,
            step=1,
        )

        # Reference (numeric, dBm) for primary detector
        y += row_h
        StyledLabel(
            container=root,
            text="Reference",
            variable_name="ref_lb",
            left=5,
            top=y,
            width=95,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )

        self.ref_value = StyledSpinBox(
            container=root,
            variable_name="ref_value",
            left=105,
            top=y,
            width=70,
            height=24,
            value=-80,
            min_value=-120,
            max_value=20,
            step=1,
        )

        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ref_unit",
            left=195,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Primary detector selection (for FineA and mapping)
        y += row_h
        StyledLabel(
            container=root,
            text="(FA) Primary Det",
            variable_name="primary_lb",
            left=5,
            top=y,
            width=170,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )

        self.primary_dd = StyledDropDown(
            container=root,
            text=["CH1", "CH2", "MAX"],
            variable_name="primary_dd",
            left=195,
            top=y,
            width=70,
            height=24,
        )

        # Confirm button
        y += row_h
        self.confirm_btn = StyledButton(
            container=root,
            text="Confirm",
            variable_name="confirm_btn",
            left=105,
            top=y,
            width=80,
            height=24,
            font_size=90,
        )

        self.confirm_btn.do_onclick(
            lambda *args, **kwargs: self.run_in_thread(self.onclick_confirm)
        )

        self.auto_sweep_container = root
        return root

    # ---------------- LOAD EXISTING STATE ----------------

    def _load_from_shared(self):
        """Sync UI from shared_memory.json without altering unrelated keys."""
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        # Sweep
        self.sweep = data.get("Sweep", {}) or {}

        if self.power is not None:
            self.power.set_value(
                self.sweep.get("power", self.power.get_value())
            )
        if self.step_size is not None:
            self.step_size.set_value(
                self.sweep.get("step", self.step_size.get_value())
            )
        if self.start_wvl is not None:
            self.start_wvl.set_value(
                self.sweep.get("start", self.start_wvl.get_value())
            )
        if self.stop_wvl is not None:
            self.stop_wvl.set_value(
                self.sweep.get("end", self.stop_wvl.get_value())
            )

        # Primary detector from FineA.detector
        self.finea = data.get("FineA", {}) or {}
        fa_det = (self.finea.get("detector") or "").lower()

        if fa_det == "ch1":
            primary = "CH1"
        elif fa_det == "ch2":
            primary = "CH2"
        elif fa_det == "max":
            primary = "MAX"
        else:
            primary = "CH1"

        if self.primary_dd is not None:
            self.primary_dd.set_value(primary)

        # Range for primary
        mode = "Auto"
        manual_val = (
            self.manual_range.get_value()
            if self.manual_range is not None
            else -10
        )

        if primary == "CH1":
            dr1 = data.get("DetectorRange_Ch1") or {}
            ar1 = data.get("DetectorAutoRange_Ch1") or {}
            if dr1:
                mode = "Manual"
                manual_val = dr1.get("range_dbm", manual_val)
            elif ar1:
                mode = "Auto"
        elif primary == "CH2":
            dr2 = data.get("DetectorRange_Ch2") or {}
            ar2 = data.get("DetectorAutoRange_Ch2") or {}
            if dr2:
                mode = "Manual"
                manual_val = dr2.get("range_dbm", manual_val)
            elif ar2:
                mode = "Auto"
        else:
            # MAX: do not override mode/value; rely on current UI
            if self.range_mode_dd is not None:
                mode = self.range_mode_dd.get_value()
            if self.manual_range is not None:
                manual_val = self.manual_range.get_value()

        if self.range_mode_dd is not None:
            self.range_mode_dd.set_value(mode)
        if self.manual_range is not None:
            self.manual_range.set_value(float(manual_val))

        # Reference value for primary
        ref_dbm = None
        if primary in ("CH1", "CH2"):
            ch = 1 if primary == "CH1" else 2
            ref_key = f"DetectorReference_Ch{ch}"
            ref_info = data.get(ref_key) or {}
            if isinstance(ref_info, dict):
                ref_dbm = ref_info.get("ref_dbm")

        if ref_dbm is None:
            if self.ref_value is not None:
                try:
                    ref_dbm = float(self.ref_value.get_value())
                except Exception:
                    ref_dbm = -80.0
            else:
                ref_dbm = -80.0

        if self.ref_value is not None:
            self.ref_value.set_value(float(ref_dbm))

    # ---------------- CONFIRM: WRITE BACK ----------------

    def onclick_confirm(self):
        """Write current settings to shared_memory.json."""
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        # Sweep
        sweep = data.get("Sweep", {}) or {}
        sweep.update(
            {
                "power": float(self.power.get_value()),
                "step": float(self.step_size.get_value()),
                "start": float(self.start_wvl.get_value()),
                "end": float(self.stop_wvl.get_value()),
            }
        )
        data["Sweep"] = sweep

        # Primary detector selection
        primary_label = (
            self.primary_dd.get_value()
            if self.primary_dd is not None
            else "CH1"
        )

        if primary_label == "CH1":
            primary_ch = 1
            fa_det = "ch1"
        elif primary_label == "CH2":
            primary_ch = 2
            fa_det = "ch2"
        else:
            primary_ch = None
            fa_det = "max"

        mode = (
            self.range_mode_dd.get_value()
            if self.range_mode_dd is not None
            else "Auto"
        )

        manual_val = (
            float(self.manual_range.get_value())
            if self.manual_range is not None
            else -10.0
        )

        ts = datetime.datetime.now().isoformat()

        # Range mapping for primary channel
        if primary_ch is not None:
            range_key = f"DetectorRange_Ch{primary_ch}"
            auto_key = f"DetectorAutoRange_Ch{primary_ch}"

            if mode == "Auto":
                data[range_key] = {}
                data[auto_key] = {
                    "channel": primary_ch,
                    "timestamp": ts,
                }
            else:
                data[auto_key] = {}
                data[range_key] = {
                    "channel": primary_ch,
                    "range_dbm": manual_val,
                    "timestamp": ts,
                }

        # Reference value for primary channel
        if primary_ch is not None and self.ref_value is not None:
            try:
                ref_dbm = float(self.ref_value.get_value())
            except Exception:
                ref_dbm = -80.0

            ref_key = f"DetectorReference_Ch{primary_ch}"
            data[ref_key] = {
                "channel": primary_ch,
                "ref_dbm": ref_dbm,
                "timestamp": ts,
            }

        # FineA.detector
        finea = data.get("FineA", {}) or {}
        finea["detector"] = fa_det
        data["FineA"] = finea

        # Atomic save via File helper
        tmp = File("shared_memory", "_", {})
        tmp._safe_write(data, SHARED_PATH)

        print(
            "[AutoSweepConfig] Updated Sweep, FineA.detector, range, and "
            "reference for primary detector"
        )


if __name__ == "__main__":
    configuration = {
        "config_project_name": "auto_sweep_config",
        "config_address": "0.0.0.0",
        "config_port": 7109,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(AutoSweepConfig,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
