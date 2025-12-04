import datetime
import json
import os
import threading

from remi import App, start
from GUI.lib_gui import *

SHARED_PATH = os.path.join("database", "shared_memory.json")

def update_detector_window_setting(names: list, payloads: list):
    try:
        with open(SHARED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    dws = data.get("DetectorWindowSettings", {})
    if not isinstance(dws, dict):
        dws = {}

    # Overwrite the specific setting
    for n, p  in zip(names, payloads):
        dws[n] = p
    
    data["DetectorWindowSettings"] = dws

    # Keep your change flag behavior
    data["Detector_Change"] = "1"

    with open(SHARED_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

class AutoSweepConfig(App):
    """Auto sweep settings panel."""

    def __init__(self, *args, **kwargs):
        # Track shared_memory.json changes
        self._user_stime = None
        self._first_check = True

        # Cached sweep block
        self.sweep = {}

        # Widgets
        self.power = None
        self.step_size = None
        self.start_wvl = None
        self.stop_wvl = None
        self.range_mode_dd = None
        self.manual_range = None
        self.ref_value = None
        self.detector = None
        self.confirm_btn = None

        # REMI init (support editing_mode)
        editing_mode = kwargs.pop("editing_mode", False)
        super_kwargs = {}
        if not editing_mode:
            super_kwargs["static_file_path"] = {"my_res": "./res/"}
        super(AutoSweepConfig, self).__init__(*args, **super_kwargs)

    # ---------------- REMI HOOKS ----------------

    def main(self):
        ui = self.construct_ui()
        self._load_from_shared()
        return ui

    def idle(self):
        """Reload when shared_memory.json changes on disk."""
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

    @staticmethod
    def _set_spin_safely(widget, value):
        """Set a spinbox if widget/value are valid."""
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    # ---------------- UI ----------------

    def construct_ui(self):
        root = StyledContainer(
            variable_name="auto_sweep_container",
            left=0,
            top=0,
            width=280,
            height=260,
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

        # Range + manual range (Ch1)
        y += row_h
        StyledLabel(
            container=root,
            text="Range (Ch1)",
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

        # Reference (Ch1)
        y += row_h
        StyledLabel(
            container=root,
            text="Ref (Ch1)",
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
            value=-30,
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

        # FA detector selection (FineA.detector)
        y += row_h
        StyledLabel(
            container=root,
            text="FA Detector",
            variable_name="detector_lb",
            left=5,
            top=y,
            width=95,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.detector = StyledDropDown(
            container=root,
            variable_name="detector",
            text=["ch1", "ch2", "Max"],
            left=105,
            top=y,
            width=70,
            height=25,
            position="absolute",
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
            lambda *_: self.run_in_thread(self.onclick_confirm)
        )

        self.auto_sweep_container = root
        return root

    # --- LOAD EXISTING STATE ---

    def _load_from_shared(self):
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        # Sweep
        self.sweep = data.get("Sweep", {}) or {}
        self._set_spin_safely(self.power, self.sweep.get("power"))
        self._set_spin_safely(self.step_size, self.sweep.get("step"))
        self._set_spin_safely(self.start_wvl, self.sweep.get("start"))
        self._set_spin_safely(self.stop_wvl, self.sweep.get("end"))

        # Range / AutoRange for Ch1
        mode = "Auto"
        manual_val = -10.0

        detector_data = data.get("DetectorWindowSettings")
        dr1 = detector_data.get("DetectorRange_Ch1") or {}
        ar1 = detector_data.get("DetectorAutoRange_Ch1") or {}

        if dr1:
            mode = "Manual"
            manual_val = dr1.get("range_dbm", manual_val)
        elif ar1:
            mode = "Auto"

        if self.range_mode_dd is not None:
            try:
                self.range_mode_dd.set_value(mode)
            except Exception:
                pass

        if self.manual_range is not None:
            self._set_spin_safely(self.manual_range, manual_val)

        # Reference for Ch1
        ref_dbm = None
        ref_info = detector_data.get("DetectorReference_Ch1") or {}
        if isinstance(ref_info, dict):
            val = ref_info.get("ref_dbm")
            try:
                ref_dbm = float(val)
            except (TypeError, ValueError):
                ref_dbm = None

        if ref_dbm is None and self.ref_value is not None:
            try:
                ref_dbm = float(self.ref_value.get_value())
            except Exception:
                ref_dbm = -30.0

        if self.ref_value is not None and ref_dbm is not None:
            self._set_spin_safely(self.ref_value, ref_dbm)

        # FineA.detector -> FA Detector dropdown (read-only / non-destructive)
        finea = data.get("FineA")
        if isinstance(finea, dict) and self.detector is not None:
            det = str(finea.get("detector", "")).lower()
            if det == "ch1":
                target = "ch1"
            elif det == "ch2":
                target = "ch2"
            elif det == "max":
                target = "Max"
            else:
                target = None

            if target:
                try:
                    self.detector.set_value(target)
                except Exception:
                    pass

    # ---------------- CONFIRM: WRITE BACK ----------------

    def onclick_confirm(self):
        # Load current shared_memory
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

        if not isinstance(data, dict):
            data = {}

        # ---- Sweep (merge) ----
        existing_sweep = data.get("Sweep", {})
        if not isinstance(existing_sweep, dict):
            existing_sweep = {}

        try:
            existing_sweep.update(
                {
                    "power": float(self.power.get_value()),
                    "step": float(self.step_size.get_value()),
                    "start": float(self.start_wvl.get_value()),
                    "end": float(self.stop_wvl.get_value()),
                }
            )
        except Exception as exc:
            print(f"[AutoSweepConfig] Invalid sweep input: {exc}")
            return

        File("shared_memory", "Sweep", existing_sweep).save()

        ts = datetime.datetime.now().isoformat()
        ch = 1

        # ---- Ch1 Range / AutoRange ----
        mode = (
            self.range_mode_dd.get_value()
            if self.range_mode_dd is not None
            else "Auto"
        )
        try:
            manual_val = float(self.manual_range.get_value())
        except Exception:
            manual_val = -10.0

        # ---- Ch1 Reference ----
        try:
            ref_dbm = float(self.ref_value.get_value())
        except Exception:
            ref_dbm = -30.0

        range_key = "DetectorRange_Ch1"
        auto_key = "DetectorAutoRange_Ch1"
        ref_key = "DetectorReference_Ch1"

        if mode == "Manual":
            # Manual: clear auto, set range_dbm
            update_detector_window_setting(
                [auto_key, range_key, ref_key],
                [{},
                 {"range_dbm": manual_val},
                 {"ref_dbm": ref_dbm}]
            )
        else:
            # Auto: clear manual, set autorange
            update_detector_window_setting(
                [auto_key, range_key, ref_key],
                [{auto_key: {"Auto": 1}},
                 {},
                 {"ref_dbm": ref_dbm}]
            )

        # ---- FineA.detector ----
        finea = data.get("FineA")
        if isinstance(finea, dict) and self.detector is not None:
            try:
                det_ui = str(self.detector.get_value())
            except Exception:
                det_ui = ""

            det_norm = det_ui.lower()
            if det_norm == "max":
                det_norm = "max"
            elif det_norm in ("ch1", "ch2"):
                pass
            else:
                # If invalid choice, keep existing detector
                current = str(finea.get("detector", "")).lower()
                if current in ("ch1", "ch2", "max"):
                    det_norm = current
                else:
                    det_norm = "max"

            finea["detector"] = det_norm
            File("shared_memory", "FineA", finea).save()

        print(
            "[AutoSweepConfig] Updated Sweep , "
            "Ch1 range/auto/ref, and FineA.detector "
        )
        import webview
        # Set to a hidden window
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7109",
            width=222,
            height=266,
            resizable=True,
            on_top=True,
            hidden=True
        )


if __name__ == "__main__":
    configuration = {
        "config_project_name": "auto_sweep_config",
        "config_address": "0.0.0.0",
        "config_port": 7109,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/",
    }

    start(
        AutoSweepConfig,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"],
    )
