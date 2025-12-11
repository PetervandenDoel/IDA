from GUI.lib_gui import *
from remi import start, App
import os
import json
import threading

# ---------------------------------------------------------------------------
# Paths for command.json and shared_memory.json
# ---------------------------------------------------------------------------
SHARED_PATH = os.path.join("database", "shared_memory.json")
command_path = os.path.join("database", "command.json")


class area_scan(App):
    """
    GUI panel for configuring Area Scan settings.
    Watches shared_memory.json to populate UI,
    and command.json for remote updates (automation scripts).
    """

    def __init__(self, *args, **kwargs):
        # Track mtime of both JSON files
        self._cmd_mtime = None
        self._shared_mtime = None
        self._first_command_check = True
        self._first_shared_check = True

        # Stores the "AreaS" block from shared memory
        self.area_s = {}

        # Normal REMI init
        if "editing_mode" not in kwargs:
            super(area_scan, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ----------------------------------------------------------------------
    # Utility Helpers
    # ----------------------------------------------------------------------
    def run_in_thread(self, target, *args):
        """Run an action asynchronously."""
        threading.Thread(target=target, args=args, daemon=True).start()

    @staticmethod
    def _set_spin_safely(widget, value):
        """
        Safe wrapper for setting a SpinBox value.
        Attempts float conversion, then raw, and ignores failures.
        """
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
    # REMI Hooks
    # ----------------------------------------------------------------------
    def idle(self):
        """Monitor both JSON files for changes and react accordingly."""

        # ---- Watch command.json ----
        try:
            cmd_mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            cmd_mtime = None

        if self._first_command_check:
            self._cmd_mtime = cmd_mtime
            self._first_command_check = False
        else:
            if cmd_mtime != self._cmd_mtime:
                self._cmd_mtime = cmd_mtime
                self.execute_command()

        # ---- Watch shared_memory.json ----
        try:
            shared_mtime = os.path.getmtime(SHARED_PATH)
        except FileNotFoundError:
            shared_mtime = None

        if self._first_shared_check:
            self._shared_mtime = shared_mtime
            self._first_shared_check = False
        else:
            if shared_mtime != self._shared_mtime:
                self._shared_mtime = shared_mtime
                self._load_from_shared()

    def main(self):
        ui = self.construct_ui()
        # Load existing state on startup
        self._load_from_shared()
        return ui

    # ----------------------------------------------------------------------
    # UI Construction
    # ----------------------------------------------------------------------
    def construct_ui(self):
        BOX_W, BOX_H = 320, 350
        LBL_W, INP_W, UNIT_W = 120, 90, 50
        LBL_X = 10
        INP_X = LBL_X + LBL_W + 8
        UNIT_X = INP_X + INP_W + 6 + 20
        y = 10
        ROW = 30

        container = StyledContainer(
            variable_name="area_scan_setting_container",
            left=0,
            top=0,
            width=BOX_W,
            height=BOX_H
        )

        # Allow scroll when contents overflow
        try:
            container.style["overflow"] = "auto"
        except Exception:
            pass

        # Title
        StyledLabel(
            container=container,
            text="Area Scan Settings",
            variable_name="title_lb",
            left=10,
            top=y,
            width=BOX_W - 20,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111"
        )
        y += ROW

        # Pattern selector (kept for compatibility)
        StyledLabel(
            container=container,
            text="Pattern",
            variable_name="pattern_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222"
        )
        self.pattern_dd = StyledDropDown(
            container=container,
            variable_name="pattern_dd",
            text=["Crosshair", "Spiral"],
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24,
            position="absolute"
        )
        self.pattern_dd.set_value("Spiral")
        y += ROW

        # X Size
        StyledLabel(
            container=container,
            text="X Size",
            variable_name="x_size_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24
        )
        self.x_size = StyledSpinBox(
            container=container,
            variable_name="x_size_in",
            left=INP_X,
            top=y,
            value=50,
            width=INP_W,
            height=24,
            min_value=-1000,
            max_value=1000,
            step=1
        )
        StyledLabel(
            container=container,
            text="µm",
            variable_name="x_size_um",
            left=UNIT_X,
            top=y,
            width=UNIT_W,
            height=24
        )
        y += ROW

        # Y Size
        StyledLabel(
            container=container,
            text="Y Size",
            variable_name="y_size_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24
        )
        self.y_size = StyledSpinBox(
            container=container,
            variable_name="y_size_in",
            left=INP_X,
            top=y,
            value=50,
            width=INP_W,
            height=24,
            min_value=-1000,
            max_value=1000,
            step=1
        )
        StyledLabel(
            container=container,
            text="µm",
            variable_name="y_size_um",
            left=UNIT_X,
            top=y,
            width=UNIT_W,
            height=24
        )
        y += ROW

        # Spiral step size
        StyledLabel(
            container=container,
            text="Step Size",
            variable_name="step_size_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24
        )
        self.step_size = StyledSpinBox(
            container=container,
            variable_name="step_size_in",
            left=INP_X,
            top=y,
            value=5,
            width=INP_W,
            height=24,
            min_value=0.001,
            max_value=1000,
            step=0.1
        )
        StyledLabel(
            container=container,
            text="µm",
            variable_name="step_size_um",
            left=UNIT_X,
            top=y,
            width=UNIT_W,
            height=24
        )
        y += ROW

        # Primary detector selector (auto-generated from SlotInfo)
        StyledLabel(
            container=container,
            text="Primary Detector",
            variable_name="primary_ch_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24
        )
        self.primary_detector_dd = StyledDropDown(
            container=container,
            variable_name="primary_detector_dd",
            text=["MAX"],
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24
        )
        y += ROW

        # Plot selector
        StyledLabel(
            container=container,
            text="Plot",
            variable_name="plot_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24
        )
        self.plot_dd = StyledDropDown(
            container=container,
            variable_name="plot_dd",
            text=["New", "Previous"],
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24
        )
        y += ROW

        # Confirm button
        self.confirm_btn = StyledButton(
            container=container,
            text="Confirm",
            variable_name="confirm_btn",
            left=(BOX_W - 80) // 2,
            top=y + 6,
            height=28,
            width=80
        )
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        return container

    # ----------------------------------------------------------------------
    # Shared Memory Loading
    # ----------------------------------------------------------------------
    def _load_from_shared(self):
        """Load values from shared_memory.json into the GUI."""
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.area_s = data.get("AreaS", {}) or {}

        # ---- Build detector list from SlotInfo ----
        slot_info = data.get("SlotInfo", [])
        channel_labels = []

        for entry in slot_info:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue
            slot, head = entry
            try:
                ch = 2 * (int(slot) - 1) + int(head) + 1
                channel_labels.append(f"CH{ch}")
            except Exception:
                pass

        if channel_labels:
            channel_labels = sorted(set(channel_labels), key=lambda x: int(x[2:]))
        channel_labels.append("MAX")

        # Update dropdown
        try:
            self.primary_detector_dd.set_options(channel_labels)
        except Exception:
            try:
                self.primary_detector_dd.update_options(channel_labels)
            except Exception:
                pass

        # Sizes
        self._set_spin_safely(self.x_size, self.area_s.get("x_size"))
        self._set_spin_safely(self.y_size, self.area_s.get("y_size"))

        # Step size (mirrors x_step/y_step for compatibility)
        step_val = self.area_s.get("x_step", self.area_s.get("step_size"))
        if step_val is not None:
            self._set_spin_safely(self.step_size, step_val)

        # Pattern
        pat = str(self.area_s.get("pattern", "")).lower()
        try:
            self.pattern_dd.set_value("Spiral" if pat == "spiral" else "Crosshair")
        except Exception:
            pass

        # Primary detector
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

        # Plot setting
        plot = self.area_s.get("plot", "New")
        if isinstance(plot, str):
            if plot.lower() == "previous":
                plot = "Previous"
            else:
                plot = "New"
        try:
            self.plot_dd.set_value(plot)
        except Exception:
            pass

    # ----------------------------------------------------------------------
    # Save configuration
    # ----------------------------------------------------------------------
    def onclick_confirm(self):
        """
        Save area scan settings to shared_memory.json.
        Spiral mode mirrors step_size into x_step/y_step for compatibility.
        """
        try:
            pat = self.pattern_dd.get_value()
            spiral = isinstance(pat, str) and pat.lower() == "spiral"
        except Exception:
            spiral = False

        try:
            step_val = float(self.step_size.get_value())
        except Exception:
            step_val = 1.0

        x_step_out = step_val
        y_step_out = step_val

        value = {
            "x_size": float(self.x_size.get_value()),
            "x_step": float(x_step_out),
            "y_size": float(self.y_size.get_value()),
            "y_step": float(y_step_out),
            "pattern": "spiral" if spiral else "crosshair",
            "primary_detector": str(self.primary_detector_dd.get_value().lower()),
            "plot": self.plot_dd.get_value(),
        }

        file = File("shared_memory", "AreaS", value)
        file.save()
        print("Confirm Area Scan Setting:", value)

        # Silent window for PyWebView
        import webview
        local_ip = "127.0.0.1"
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7004",
            width=222,
            height=266,
            resizable=True,
            on_top=True,
            hidden=True
        )

    # ----------------------------------------------------------------------
    # Command handler (backwards compatibility preserved)
    # ----------------------------------------------------------------------
    def execute_command(self, path=command_path):
        """
        Supports remote automation via command.json.
        Handles legacy fields (as_x_step, as_y_step) by mapping them to step_size.
        """
        area = 0
        record = 0
        new_command = {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                command = data.get("command", {})
        except Exception as e:
            print(f"[Error] Failed to load command: {e}")
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
                # Spiral mode: x_step → step_size
                self.step_size.set_value(val)

            elif key == "as_y_step":
                # Same mapping as x_step
                self.step_size.set_value(val)

            elif key == "as_primary_detector":
                if isinstance(val, str):
                    try:
                        self.primary_detector_dd.set_value(val.upper())
                    except Exception:
                        pass

            elif key == "as_plot":
                if isinstance(val, str):
                    v = "Previous" if val.lower() == "previous" else "New"
                    self.plot_dd.set_value(v)

            elif key == "as" and val == "confirm":
                self.onclick_confirm()

        if area == 1:
            print("as record")
            file = File("command", "command", new_command)
            file.save()


# ----------------------------------------------------------------------
# App entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    configuration = {
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
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"]
    )
