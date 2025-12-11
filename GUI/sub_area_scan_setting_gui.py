from GUI.lib_gui import *
from remi import start, App
import os
import json
import threading

# ---------------------------------------------------------------------------
# JSON paths
# ---------------------------------------------------------------------------
SHARED_PATH = os.path.join("database", "shared_memory.json")
command_path = os.path.join("database", "command.json")


class area_scan(App):
    """
    Area Scan Settings GUI.

    Restored to original structure:
    - Crosshair + Spiral modes
    - X/Y step size (Crosshair)
    - Step Size (Spiral)
    - Pattern hint
    - Detector dropdown (CH1–CH8 + MAX)
    Now includes:
    - SlotInfo→dynamic channels
    """

    def __init__(self, *args, **kwargs):
        # Track json modification times
        self._cmd_mtime = None
        self._shared_mtime = None
        self._first_command_check = True
        self._first_shared_check = True

        # Local cache
        self.area_s = {}

        # Required dummy attributes (used by commands)
        self.x_step = None
        self.y_step = None

        if "editing_mode" not in kwargs:
            super(area_scan, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ----------------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------------
    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    @staticmethod
    def _set_spin_safely(widget, value):
        """Safely set SpinBox value with float fallback."""
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    # ----------------------------------------------------------------------
    # REMI hooks
    # ----------------------------------------------------------------------
    def idle(self):
        """Monitor json changes and update GUI."""
        # --- command.json ---
        try:
            cmd_mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            cmd_mtime = None

        if self._first_command_check:
            self._cmd_mtime = cmd_mtime
            self._first_command_check = False
        elif cmd_mtime != self._cmd_mtime:
            self._cmd_mtime = cmd_mtime
            self.execute_command()

        # --- shared_memory.json ---
        try:
            shared_mtime = os.path.getmtime(SHARED_PATH)
        except FileNotFoundError:
            shared_mtime = None

        if self._first_shared_check:
            self._shared_mtime = shared_mtime
            self._first_shared_check = False
        elif shared_mtime != self._shared_mtime:
            self._shared_mtime = shared_mtime
            self._load_from_shared()

    def main(self):
        ui = self.construct_ui()
        self._load_from_shared()
        return ui

    # ----------------------------------------------------------------------
    # UI construction
    # ----------------------------------------------------------------------
    def construct_ui(self):
        BOX_W, BOX_H = 330, 410
        LBL_W, INP_W, UNIT_W = 120, 90, 50
        LBL_X = 10
        INP_X = LBL_X + LBL_W + 8
        UNIT_X = INP_X + INP_W + 8
        ROW = 30
        y = 10

        container = StyledContainer(
            variable_name="area_scan_setting_container",
            left=0, top=0,
            width=BOX_W, height=BOX_H
        )

        try:
            container.style["overflow"] = "auto"
        except Exception:
            pass

        # Title
        StyledLabel(
            container=container,
            text="Area Scan Settings",
            variable_name="title_lb",
            left=10, top=y,
            width=BOX_W - 20, height=24,
            font_size=110
        )
        y += ROW

        # Pattern
        StyledLabel(
            container=container,
            text="Pattern",
            variable_name="pattern_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24
        )
        self.pattern_dd = StyledDropDown(
            container=container,
            variable_name="pattern_dd",
            text=["Crosshair", "Spiral"],
            left=INP_X, top=y,
            width=INP_W + UNIT_W, height=24
        )
        self.pattern_dd.set_value("Spiral")
        y += ROW

        # Pattern hint
        self.pattern_hint = StyledLabel(
            container=container,
            text="Spiral: uses Step Size; Crosshair uses X/Y Step.",
            variable_name="pattern_hint",
            left=LBL_X,
            top=y,
            width=BOX_W - 20,
            height=22,
            font_size=90,
            color="#666"
        )
        y += ROW

        # X Size
        StyledLabel(container=container, text="X Size",
                    variable_name="x_size_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)
        self.x_size = StyledSpinBox(
            container=container, variable_name="x_size_in",
            left=INP_X, top=y,
            width=INP_W, height=24,
            value=50, min_value=-1000, max_value=1000
        )
        StyledLabel(container=container, text="µm",
                    variable_name="x_size_unit",
                    left=UNIT_X, top=y,
                    width=UNIT_W, height=24)
        y += ROW

        # Y Size
        StyledLabel(container=container, text="Y Size",
                    variable_name="y_size_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)
        self.y_size = StyledSpinBox(
            container=container, variable_name="y_size_in",
            left=INP_X, top=y,
            width=INP_W, height=24,
            value=50, min_value=-1000, max_value=1000
        )
        StyledLabel(container=container, text="µm",
                    variable_name="y_size_unit",
                    left=UNIT_X, top=y,
                    width=UNIT_W, height=24)
        y += ROW

        # X Step (Crosshair)
        StyledLabel(container=container, text="X Step",
                    variable_name="x_step_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)
        self.x_step = StyledSpinBox(
            container=container, variable_name="x_step_in",
            left=INP_X, top=y,
            width=INP_W, height=24,
            value=5, step=0.1
        )
        StyledLabel(container=container, text="µm",
                    variable_name="x_step_unit",
                    left=UNIT_X, top=y,
                    width=UNIT_W, height=24)
        y += ROW

        # Y Step (Crosshair)
        StyledLabel(container=container, text="Y Step",
                    variable_name="y_step_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)
        self.y_step = StyledSpinBox(
            container=container, variable_name="y_step_in",
            left=INP_X, top=y,
            width=INP_W, height=24,
            value=5, step=0.1
        )
        StyledLabel(container=container, text="µm",
                    variable_name="y_step_unit",
                    left=UNIT_X, top=y,
                    width=UNIT_W, height=24)
        y += ROW

        # Step Size (Spiral)
        StyledLabel(container=container, text="Step Size (Spiral)",
                    variable_name="step_size_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)
        self.step_size = StyledSpinBox(
            container=container, variable_name="step_size_in",
            left=INP_X, top=y,
            width=INP_W, height=24,
            value=5, min_value=0.001, max_value=1000, step=0.1
        )
        StyledLabel(container=container, text="µm",
                    variable_name="step_size_unit",
                    left=UNIT_X, top=y,
                    width=UNIT_W, height=24)
        y += ROW

        # Primary Detector
        StyledLabel(container=container, text="Primary Detector",
                    variable_name="primary_ch_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)

        # Default CH1–CH8 + MAX
        default_chs = [f"CH{i}" for i in range(1, 9)] + ["MAX"]

        self.primary_detector_dd = StyledDropDown(
            container=container,
            variable_name="primary_detector_dd",
            text=default_chs,
            left=INP_X, top=y,
            width=INP_W + UNIT_W, height=24
        )
        y += ROW

        # Plot
        StyledLabel(container=container, text="Plot",
                    variable_name="plot_lb",
                    left=LBL_X, top=y,
                    width=LBL_W, height=24)
        self.plot_dd = StyledDropDown(
            container=container,
            variable_name="plot_dd",
            text=["New", "Previous"],
            left=INP_X, top=y,
            width=INP_W + UNIT_W, height=24
        )
        y += ROW

        # Confirm
        self.confirm_btn = StyledButton(
            container=container,
            text="Confirm",
            variable_name="confirm_btn",
            left=(BOX_W - 90) // 2,
            top=y + 5,
            width=90, height=28
        )
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        return container

    # ----------------------------------------------------------------------
    # Load from shared memory
    # ----------------------------------------------------------------------
    def _load_from_shared(self):
        """Populate UI from shared_memory.json."""
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.area_s = data.get("AreaS", {}) or {}

        # -------- SlotInfo → dynamic channel list --------
        slot_info = data.get("SlotInfo", [])
        channels = []

        for entry in slot_info:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue
            slot, head = entry
            try:
                ch = 2 * (int(slot) - 1) + int(head) + 1
                channels.append(f"CH{ch}")
            except Exception:
                pass

        if channels:
            channels = sorted(set(channels), key=lambda x: int(x[2:]))
        channels.append("MAX")

        try:
            self.primary_detector_dd.set_options(channels)
        except Exception:
            pass

        # -------- Basic fields --------
        self._set_spin_safely(self.x_size, self.area_s.get("x_size"))
        self._set_spin_safely(self.y_size, self.area_s.get("y_size"))
        self._set_spin_safely(self.x_step, self.area_s.get("x_step"))
        self._set_spin_safely(self.y_step, self.area_s.get("y_step"))

        step_val = self.area_s.get("x_step", self.area_s.get("step_size"))
        if step_val is not None:
            self._set_spin_safely(self.step_size, step_val)

        # -------- Pattern --------
        pat = str(self.area_s.get("pattern", "spiral")).lower()
        val = "Spiral" if pat == "spiral" else "Crosshair"
        try:
            self.pattern_dd.set_value(val)
        except Exception:
            pass

        # -------- Primary detector --------
        det = str(self.area_s.get("primary_detector", "")).lower()
        if det.startswith("ch"):
            try:
                num = int(det[2:])
                det_ui = f"CH{num}"
            except Exception:
                det_ui = "MAX"
        else:
            det_ui = "MAX"

        try:
            self.primary_detector_dd.set_value(det_ui)
        except Exception:
            pass

        # -------- Plot --------
        plot = str(self.area_s.get("plot", "New"))
        plot = "Previous" if plot.lower() == "previous" else "New"
        try:
            self.plot_dd.set_value(plot)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    # Save
    # ----------------------------------------------------------------------
    def onclick_confirm(self):
        """Save values to shared_memory.json."""
        try:
            pat = self.pattern_dd.get_value()
            spiral = pat.lower() == "spiral"
        except Exception:
            spiral = True

        if spiral:
            try:
                step_val = float(self.step_size.get_value())
            except Exception:
                step_val = 1.0
            x_step_out = step_val
            y_step_out = step_val
        else:
            x_step_out = float(self.x_step.get_value())
            y_step_out = float(self.y_step.get_value())

        value = {
            "x_size": float(self.x_size.get_value()),
            "x_step": float(x_step_out),
            "y_size": float(self.y_size.get_value()),
            "y_step": float(y_step_out),
            "pattern": "spiral" if spiral else "crosshair",
            "primary_detector": str(self.primary_detector_dd.get_value().lower()),
            "plot": self.plot_dd.get_value()
        }

        file = File("shared_memory", "AreaS", value)
        file.save()
        print("Confirm Area Scan Setting:", value)

    # ----------------------------------------------------------------------
    # Command JSON integration
    # ----------------------------------------------------------------------
    def execute_command(self, path=command_path):
        """Respond to updates in command.json."""
        area = 0
        record = 0
        new_command = {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                command = data.get("command", {})
        except Exception:
            return

        for key, val in command.items():
            if key.startswith("as_set") and record == 0:
                area = 1

            elif key.startswith((
                "stage_control", "tec_control", "sensor_control",
                "fa_set", "lim_set", "sweep_set",
                "devices_control", "testing_control"
            )) or record == 1:
                record = 1
                new_command[key] = val

            elif key == "as_x_size":
                self.x_size.set_value(val)

            elif key == "as_y_size":
                self.y_size.set_value(val)

            elif key == "as_x_step":
                self.step_size.set_value(val)
                self.x_step.set_value(val)

            elif key == "as_y_step":
                self.step_size.set_value(val)
                self.y_step.set_value(val)

            elif key == "as_primary_detector":
                try:
                    self.primary_detector_dd.set_value(val.upper())
                except Exception:
                    pass

            elif key == "as_plot":
                v = "Previous" if str(val).lower() == "previous" else "New"
                self.plot_dd.set_value(v)

            elif key == "as" and val == "confirm":
                self.onclick_confirm()

        if area == 1:
            file = File("command", "command", new_command)
            file.save()


# ----------------------------------------------------------------------
# App entry
# ----------------------------------------------------------------------
if __name__ == "__main__":
    config = {
        "config_project_name": "area_scan",
        "config_address": "0.0.0.0",
        "config_port": 7004,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }

    start(
        area_scan,
        address=config["config_address"],
        port=config["config_port"],
        multiple_instance=config["config_multiple_instance"],
        enable_file_cache=config["config_enable_file_cache"],
        start_browser=config["config_start_browser"]
    )
