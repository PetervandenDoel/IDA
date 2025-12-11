from GUI.lib_gui import *
from remi import start, App
import os, json, threading

# --- Paths to JSON files ---
SHARED_PATH = os.path.join("database", "shared_memory.json")
command_path = os.path.join("database", "command.json")


class area_scan(App):
    def __init__(self, *args, **kwargs):
        # Track command.json changes
        self._cmd_mtime = None
        self._first_command_check = True

        # Track shared_memory.json changes
        self._shared_mtime = None
        self._first_shared_check = True

        # Cache of AreaS block (optional, but handy)
        self.area_s = {}

        # REMI init
        if "editing_mode" not in kwargs:
            super(area_scan, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ------------------- UTILITIES -------------------

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    @staticmethod
    def _set_spin_safely(widget, value):
        """
        Same pattern as AutoSweepConfig:
        try to set a SpinBox with float, then raw, ignore if it fails.
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

    # ------------------- REMI HOOKS -------------------

    def idle(self):
        """
        Watch BOTH:
        - command.json -> execute_command()
        - shared_memory.json -> _load_from_shared()
        """

        # --- command.json watcher ---
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

        # --- shared_memory.json watcher (for AreaS) ---
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
        # On first open, pull current AreaS into the UI
        self._load_from_shared()
        return ui

    # ------------------- UI -------------------
    def construct_ui(self):
        # Layout constants for clean alignment
        BOX_W, BOX_H = 320, 350
        LBL_W, INP_W, UNIT_W = 120, 90, 50
        LBL_X, INP_X, UNIT_X = 10, 10 + LBL_W + 8, 10 + LBL_W + 8 + INP_W + 6 + 20

        y = 10
        ROW = 30

        area_scan_setting_container = StyledContainer(
            variable_name="area_scan_setting_container",
            left=0, top=0, width=BOX_W, height=BOX_H
        )
        # Make long content scroll instead of overflow-cut
        try:
            area_scan_setting_container.style['overflow'] = 'auto'
        except Exception:
            pass

        # Helper to attach a tooltip if supported
        def tooltip(widget, text: str):
            try:
                widget.attributes['title'] = text
            except Exception:
                pass

        # Title row
        StyledLabel(
            container=area_scan_setting_container, text="Area Scan Settings",
            variable_name="title_lb", left=10, top=y, width=BOX_W - 20, height=24,
            font_size=110, flex=True, justify_content="left", color="#111"
        )
        y += ROW

        # Pattern
        StyledLabel(container=area_scan_setting_container, text="Pattern",
                    variable_name="pattern_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.pattern_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="pattern_dd",
            text=["Crosshair", "Spiral"], left=INP_X, top=y, width=INP_W + UNIT_W, height=24,
            position="absolute"
        )
        self.pattern_dd.set_value("Spiral")
        y += ROW

        # # Pattern hint line (updates when Pattern changes)
        # self.pattern_hint = StyledLabel(
        #     container=area_scan_setting_container, text="Crosshair: uses X Step and Y Step.",
        #     variable_name="pattern_hint", left=LBL_X, top=y, width=BOX_W - 2 * LBL_X, height=22,
        #     font_size=90, flex=True, justify_content="left", color="#666"
        # )
        # y += ROW

        # X Size
        StyledLabel(container=area_scan_setting_container, text="X Size",
                    variable_name="x_size_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.x_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="x_size_in",
            left=INP_X, top=y, value=50, width=INP_W, height=24,
            min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="x_size_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # Y Size
        StyledLabel(container=area_scan_setting_container, text="Y Size",
                    variable_name="y_size_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.y_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="y_size_in",
            left=INP_X, top=y, value=50, width=INP_W, height=24,
            min_value=-1000, max_value=1000, step=1, position="absolute"
        )
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="y_size_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # --- Crosshair controls ---
        # StyledLabel(container=area_scan_setting_container, text="X Step (Crosshair)",
                    # variable_name="x_step_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    # font_size=100, flex=True, justify_content="right", color="#222")
        # self.x_step = StyledSpinBox(
            # container=area_scan_setting_container, variable_name="x_step_in",
            # left=INP_X, top=y, value=5, width=INP_W, height=24,
            # min_value=-1000, max_value=1000, step=0.1, position="absolute"
        # )
        # tooltip(self.x_step, "Used when Pattern = Crosshair. Saved as x_step.")
        # StyledLabel(container=area_scan_setting_container, text="µm",
                    # variable_name="x_step_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    # font_size=100, flex=True, justify_content="left", color="#222")
        # y += ROW

        # StyledLabel(container=area_scan_setting_container, text="Y Step (Crosshair)",
                    # variable_name="y_step_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    # font_size=100, flex=True, justify_content="right", color="#222")
        # self.y_step = StyledSpinBox(
            # container=area_scan_setting_container, variable_name="y_step_in",
            # left=INP_X, top=y, value=5, width=INP_W, height=24,
            # min_value=-1000, max_value=1000, step=0.1, position="absolute"
        # )
        # tooltip(self.y_step, "Used when Pattern = Crosshair. Saved as y_step.")
        # StyledLabel(container=area_scan_setting_container, text="µm",
                    # variable_name="y_step_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    # font_size=100, flex=True, justify_content="left", color="#222")
        # y += ROW

        # --- Spiral control ---
        StyledLabel(container=area_scan_setting_container, text="Step Size (Spiral)",
                    variable_name="step_size_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.step_size = StyledSpinBox(
            container=area_scan_setting_container, variable_name="step_size_in",
            left=INP_X, top=y, value=5, width=INP_W, height=24,
            min_value=0.001, max_value=1000, step=0.1, position="absolute"
        )
        tooltip(self.step_size, "Used when Pattern = Spiral. Mirrored to both x_step and y_step on save.")
        StyledLabel(container=area_scan_setting_container, text="µm",
                    variable_name="step_size_um", left=UNIT_X, top=y, width=UNIT_W, height=24,
                    font_size=100, flex=True, justify_content="left", color="#222")
        y += ROW

        # Primary channel selector
        StyledLabel(container=area_scan_setting_container, text="Primary Detector",
                    variable_name="primary_ch_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.primary_detector_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="primary_detector_dd",
            text=["CH1", "CH2", "MAX",
                  "CH3", "CH4", "CH5",
                  "CH6", "CH7", "CH8"], left=INP_X, top=y, width=INP_W + UNIT_W, height=24, position="absolute"
        )
        y += ROW

        # Plot selector
        StyledLabel(container=area_scan_setting_container, text="Plot",
                    variable_name="plot_lb", left=LBL_X, top=y, width=LBL_W, height=24,
                    font_size=100, flex=True, justify_content="right", color="#222")
        self.plot_dd = StyledDropDown(
            container=area_scan_setting_container, variable_name="plot_dd",
            text=["New", "Previous"], left=INP_X, top=y, width=INP_W + UNIT_W, height=24, position="absolute"
        )
        y += ROW

        # Confirm button
        self.confirm_btn = StyledButton(
            container=area_scan_setting_container, text="Confirm",
            variable_name="confirm_btn", left=(BOX_W - 80) // 2, top=y + 6, height=28, width=80, font_size=90
        )
        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        # Try to attach onchange for live hint updates (guarded)
        try:
            self.pattern_dd.do_onchange(lambda *_: self._update_pattern_hint())
        except Exception:
            pass

        # Initial hint
        self._update_pattern_hint()
        return area_scan_setting_container

    # Clarifies which fields apply in each mode (no enabling/hiding; pure text)
    def _update_pattern_hint(self):
        try:
            pat = self.pattern_dd.get_value()
            spiral = (isinstance(pat, str) and pat.lower() == "spiral")
        except Exception:
            spiral = False
        if spiral:
            text = "Spiral: uses Step Size (mirrored to X/Y Step on save)."
        else:
            text = "Crosshair: uses X Step and Y Step."
        try:
            self.pattern_hint.set_text(text)
        except Exception:
            # fallback: ignore if StyledLabel doesn't expose set_text
            pass

    # ------------------- LOAD FROM shared_memory.json (AreaS) -------------------

    def _load_from_shared(self):
        """
        Mirror AutoSweepConfig._load_from_shared, but for AreaS.

        shared_memory.json structure (relevant part):

        "AreaS": {
            "x_size": 119.0,
            "x_step": 7.0,
            "y_size": 119.0,
            "y_step": 7.0,
            "pattern": "spiral",
            "primary_detector": "max",
            "plot": "New"
        }
        """
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
                ch = 2*(int(slot)-1) + int(head) + 1
                channel_labels.append(f"CH{ch}")
            except:
                pass

        if channel_labels:
            channel_labels = sorted(set(channel_labels), key=lambda x: int(x[2:]))
        channel_labels.append("MAX")

        try:
            self.primary_detector_dd.set_options(channel_labels)
        except:
            try:
                self.primary_detector_dd.update_options(channel_labels)
            except:
                pass
        # Sizes
        self._set_spin_safely(self.x_size, self.area_s.get("x_size"))
        self._set_spin_safely(self.y_size, self.area_s.get("y_size"))

        # Steps
        x_step = self.area_s.get("x_step")
        y_step = self.area_s.get("y_step")
        self._set_spin_safely(self.x_step, x_step)
        self._set_spin_safely(self.y_step, y_step)

        # Pattern -> dropdown mapping
        pat = str(self.area_s.get("pattern", "")).lower()
        if pat == "spiral":
            try:
                self.pattern_dd.set_value("Spiral")
            except Exception:
                pass
            # For spiral, use x_step as step_size if present
            if x_step is not None:
                self._set_spin_safely(self.step_size, x_step)
        elif pat == "crosshair":
            try:
                self.pattern_dd.set_value("Crosshair")
            except Exception:
                pass
        else:
            # default
            try:
                self.pattern_dd.set_value("Spiral")
            except Exception:
                pass
            
        # Primary detector mapping ("max", "ch1", "ch2" -> "MAX"/"CH1"/"CH2")
        det = str(self.area_s.get("primary_detector", "")).lower()
        if det.startswith("ch"):
            try:
                num = int(det[2:])
                det_ui = f"CH{num}"
            except:
                det_ui = "MAX"
        else:
            det_ui = "MAX"
        try:
            self.primary_detector_dd.set_value(det_ui)
        except Exception:
            pass

        # Plot ("New"/"Previous")
        plot = self.area_s.get("plot", "New")
        if isinstance(plot, str):
            low = plot.lower()
            if low == "new":
                plot = "New"
            elif low == "previous":
                plot = "Previous"
            else:
                plot = "New"
            try:
                self.plot_dd.set_value(plot)
            except Exception:
                pass

        # Refresh hint text based on loaded pattern
        self._update_pattern_hint()

    # ------------------- Save (protocol unchanged) -------------------
    def onclick_confirm(self):
        """
        We still write ONLY: x_size, x_step, y_size, y_step, plot, pattern, primary_detector.
        If Pattern == 'Spiral', mirror step_size into x_step & y_step here.
        """
        try:
            pat = self.pattern_dd.get_value()
            spiral = (isinstance(pat, str) and pat.lower() == "spiral")
        except Exception:
            spiral = False

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
            "plot": self.plot_dd.get_value(),
        }
        file = File("shared_memory", "AreaS", value)
        file.save()
        print("Confirm Area Scan Setting:", value)

        import webview
        # Set to a hidden window
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7004",
            width=222,
            height=266,
            resizable=True,
            on_top=True,
            hidden=True
        )

    # ------------------- Commands (unchanged) -------------------
    def execute_command(self, path=command_path):
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
            elif key.startswith(("stage_control", "tec_control", "sensor_control",
                                 "fa_set", "lim_set", "sweep_set",
                                 "devices_control", "testing_control")) or record == 1:
                record = 1
                new_command[key] = val

            elif key == "as_x_size":
                self.x_size.set_value(val)
            elif key == "as_x_step":
                self.x_step.set_value(val)
            elif key == "as_y_size":
                self.y_size.set_value(val)
            elif key == "as_y_step":
                self.y_step.set_value(val)
            elif key == "as_primary_detector":
                if isinstance(val, str):
                    v = val.upper()
                    if v not in ("CH1", "CH2", "MAX"):
                        v = "MAX"
                    self.primary_detector_dd.set_value(v)
            elif key == "as_plot":
                if isinstance(val, str):
                    low = val.lower()
                    if low == "new":
                        val = "New"
                    elif low == "previous":
                        val = "Previous"
                    else:
                        val = "New"
                self.plot_dd.set_value(val)
            elif key == "as" and val == "confirm":
                self.onclick_confirm()

        if area == 1:
            print("as record")
            file = File("command", "command", new_command)
            file.save()


# ---- App entry ----
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
    start(area_scan,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
