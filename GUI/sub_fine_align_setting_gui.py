from GUI.lib_gui import *
from remi import start, App
import os, json, threading 

# --- Paths to JSON files ---
SHARED_PATH = os.path.join("database", "shared_memory.json")
command_path = os.path.join("database", "command.json")


class fine_align(App):
    def __init__(self, *args, **kwargs):
        # Track command.json changes
        self._cmd_mtime = None
        self._first_command_check = True

        # Track shared_memory.json changes (for FineA)
        self._shared_mtime = None
        self._first_shared_check = True

        # Optional cache of FineA block
        self.fine_a = {}

        if "editing_mode" not in kwargs:
            super(fine_align, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    # ---------------- UTILITIES ----------------

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    @staticmethod
    def _set_spin_safely(widget, value):
        """
        Same pattern as AutoSweepConfig / area_scan:
        try float, then raw; ignore on failure.
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

         # --------- SAFE VALUE HELPERS (for Bug #2) ---------

    @staticmethod
    def _safe_float(widget, default):
        try:
            return float(widget.get_value())
        except Exception:
            return default

    @staticmethod
    def _safe_int(widget, default):
        try:
            return int(float(widget.get_value()))
        except Exception:
            return default

    @staticmethod
    def _safe_str(widget, default):
        try:
            val = widget.get_value()
            if val is None:
                return default
            return str(val)
        except Exception:
            return default

    # ---------------- REMI HOOKS ----------------

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

        # --- shared_memory.json watcher for FineA ---
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
        # On first open, load FineA from shared_memory.json
        self._load_from_shared()
        return ui

    # ---------------- UI ----------------

    def construct_ui(self):
        fine_align_setting_container = StyledContainer(
            variable_name="fine_align_setting_container",
            left=0,
            top=0,
            height=330,   # increased to fit new rows
            width=200
        )

        # ----- Window -----
        StyledLabel(
            container=fine_align_setting_container, text="Window",
            variable_name="window_size_lb",
            left=0, top=10,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.window_size = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="window_size_in",
            left=80, top=10,
            value=10,
            width=50, height=24,
            min_value=-1000, max_value=1000,
            step=1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um",
            variable_name="window_size_um",
            left=150, top=10,
            width=20, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Step Size -----
        StyledLabel(
            container=fine_align_setting_container, text="Step Size",
            variable_name="step_size_lb",
            left=0, top=42,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.step_size = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="step_size_in",
            left=80, top=42,
            value=1,
            width=50, height=24,
            min_value=-1000, max_value=1000,
            step=0.1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um",
            variable_name="step_size_um",
            left=150, top=42,
            width=20, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Max Iters -----
        StyledLabel(
            container=fine_align_setting_container, text="Max Iters",
            variable_name="max_iters_lb",
            left=0, top=74,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.max_iters = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="max_iters_in",
            left=80, top=74,
            value=10,
            width=50, height=24,
            min_value=0, max_value=50,
            step=1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="",
            variable_name="max_iters_um",
            left=150, top=74,
            width=20, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Min Grad SS -----
        StyledLabel(
            container=fine_align_setting_container, text="Min Grad SS",
            variable_name="min_grad_ss_lb",
            left=0, top=106,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.min_grad_ss = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="min_grad_ss_in",
            left=80, top=106,
            value=0.1,
            width=50, height=24,
            min_value=0.001, max_value=10,
            step=1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="um",
            variable_name="min_grad_ss_um",
            left=150, top=106,
            width=20, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Detector -----
        StyledLabel(
            container=fine_align_setting_container, text="Detector",
            variable_name="detector_lb",
            left=0, top=138,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        # Initial options; will be overridden from SlotInfo in _load_from_shared
        self.detector = StyledDropDown(
            container=fine_align_setting_container,
            variable_name="detector",
            text=["ch1", "ch2", "Max"],
            left=80, top=138,
            width=60, height=25,
            position="absolute"
        )

        # ----- Ref WL -----
        StyledLabel(
            container=fine_align_setting_container, text="Ref WL",
            variable_name="ref_wl_lb",
            left=0, top=170,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ref_wl = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="ref_wl_in",
            left=80, top=170,
            value=1550.0,
            width=50, height=24,
            min_value=1450.0, max_value=1650.0,
            step=0.01,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="nm",
            variable_name="ref_wl_nm",
            left=150, top=170,
            width=20, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Threshold (dBm) -----
        StyledLabel(
            container=fine_align_setting_container, text="Thresh",
            variable_name="threshold_lb",
            left=0, top=202,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.threshold = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="threshold_in",
            left=80, top=202,
            value=-10.0,
            width=50, height=24,
            min_value=-100.0, max_value=20.0,
            step=0.1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="dBm",
            variable_name="threshold_dbm",
            left=150, top=202,
            width=30, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Secondary WL -----
        StyledLabel(
            container=fine_align_setting_container, text="2nd WL",
            variable_name="secondary_wl_lb",
            left=0, top=234,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.secondary_wl = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="secondary_wl_in",
            left=80, top=234,
            value=1540.0,
            width=50, height=24,
            min_value=1450.0, max_value=1650.0,
            step=0.01,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="nm",
            variable_name="secondary_wl_nm",
            left=150, top=234,
            width=20, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Secondary Loss -----
        StyledLabel(
            container=fine_align_setting_container, text="2nd Loss",
            variable_name="secondary_loss_lb",
            left=0, top=266,
            width=70, height=25,
            font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.secondary_loss = StyledSpinBox(
            container=fine_align_setting_container,
            variable_name="secondary_loss_in",
            left=80, top=266,
            value=50.0,
            width=50, height=24,
            min_value=-100.0, max_value=80.0,
            step=0.1,
            position="absolute"
        )

        StyledLabel(
            container=fine_align_setting_container, text="dBm",
            variable_name="secondary_loss_dbm",
            left=150, top=266,
            width=30, height=25,
            font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # ----- Confirm button -----
        self.confirm_btn = StyledButton(
            container=fine_align_setting_container, text="Confirm",
            variable_name="confirm_btn",
            left=68, top=298,
            height=25, width=70,
            font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.fine_align_setting_container = fine_align_setting_container
        return fine_align_setting_container

    # ---------------- LOAD FROM shared_memory.json (FineA) ----------------

    def _load_from_shared(self):
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        # ----- Build detector list dynamically from SlotInfo -----
        slot_info = data.get("SlotInfo") or []
        channel_labels = []

        # SlotInfo entries are [slot, head], e.g. [1,0], [1,1], [4,0], [4,1]
        # Mapping: ch = 2*(slot-1) + head + 1
        for entry in slot_info:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue
            slot, head = entry
            try:
                slot_i = int(slot)
                head_i = int(head)
            except Exception:
                continue
            ch_num = 2 * (slot_i - 1) + head_i + 1
            channel_labels.append(f"ch{ch_num}")

        if channel_labels:
            # Deduplicate and sort numerically (ch1, ch2, ch7, ch8…)
            try:
                channel_labels = sorted(set(channel_labels), key=lambda x: int(x[2:]))
            except Exception:
                channel_labels = sorted(set(channel_labels))
            channel_labels.append("Max")
        else:
            # Fallback if SlotInfo missing
            channel_labels = ["ch1", "ch2", "Max"]

        # Try to apply options to StyledDropDown, if the helper exists
        try:
            if hasattr(self.detector, "set_options"):
                self.detector.set_options(channel_labels)
            elif hasattr(self.detector, "update_options"):
                self.detector.update_options(channel_labels)
            # else: leave existing options; selection logic below still works
        except Exception:
            pass

        # ----- FineA block -----
        self.fine_a = data.get("FineA", {}) or {}

        # Scalars (window, step, grad, wavelengths)
        self._set_spin_safely(self.window_size, self.fine_a.get("window_size"))
        self._set_spin_safely(self.step_size, self.fine_a.get("step_size"))
        self._set_spin_safely(self.max_iters, self.fine_a.get("max_iters"))
        self._set_spin_safely(self.min_grad_ss, self.fine_a.get("min_gradient_ss"))
        self._set_spin_safely(self.ref_wl, self.fine_a.get("ref_wl"))
        self._set_spin_safely(self.threshold, self.fine_a.get("threshold"))
        self._set_spin_safely(self.secondary_wl, self.fine_a.get("secondary_wl"))
        self._set_spin_safely(self.secondary_loss, self.fine_a.get("secondary_loss"))

        # Detector mapping into dropdown
        det_raw = self.fine_a.get("detector", "")
        det = str(det_raw).lower()

        target = None
        for label in channel_labels:
            if label.lower() == det:
                target = label
                break

        # Special-case "max" so we accept "max", "Max", etc.
        if target is None and det == "max":
            if "Max" in channel_labels:
                target = "Max"
            elif "max" in channel_labels:
                target = "max"

        if target is not None:
            try:
                self.detector.set_value(target)
            except Exception:
                pass


    # ---------------- Save to shared_memory.json (FineA) ----------------
    def onclick_confirm(self):
        value = {
            "window_size":       self._safe_float(self.window_size, 10.0),
            "step_size":         self._safe_float(self.step_size, 1.0),
            "max_iters":         self._safe_int(self.max_iters, 10),
            "min_gradient_ss":   self._safe_float(self.min_grad_ss, 0.1),
            "detector":          self._safe_str(self.detector, "Max"),
            "ref_wl":            self._safe_float(self.ref_wl, 1550.0),
            "threshold":         self._safe_float(self.threshold, -10.0),
            "secondary_wl":      self._safe_float(self.secondary_wl, 1540.0),
            "secondary_loss":    self._safe_float(self.secondary_loss, 50.0),
        }

        file = File("shared_memory", "FineA", value)
        file.save()
        print("Confirm Fine Align Setting")

        import webview
        local_ip = '127.0.0.1'
        webview.create_window(
            "Setting",
            f"http://{local_ip}:7003",
            width=222,
            height=266,
            resizable=True,
            on_top=True,
            hidden=True
        )


    # ---------------- Commands (unchanged) ----------------

    def execute_command(self, path=command_path):
        fa = 0
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
            if key.startswith("fa_set") and record == 0:
                fa = 1
            elif key.startswith("stage_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("tec_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sensor_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("as_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("lim_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("sweep_set") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("devices_control") or record == 1:
                record = 1
                new_command[key] = val
            elif key.startswith("testing_control") or record == 1:
                record = 1
                new_command[key] = val

            elif key == "fa_window_size":
                self.window_size.set_value(val)
            elif key == "fa_step_size":
                self.step_size.set_value(val)
            elif key == "fa_max_iters":
                self.max_iters.set_value(val)
            elif key == "fa_min_gradient_ss":
                self.min_grad_ss.set_value(val)
            elif key == "fa_detector":
                self.detector.set_value(str(val))
            elif key == "fa_ref_wl":
                self.ref_wl.set_value(float(val))
            elif key == "fa_confirm":
                self.onclick_confirm()

        if fa == 1:
            print("fa record")
            file = File("command", "command", new_command)
            file.save()


if __name__ == "__main__":
    configuration = {
        "config_project_name": "fine_align",
        "config_address": "0.0.0.0",
        "config_port": 7003,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(fine_align,
          address=configuration["config_address"],
          port=configuration["config_port"],
          multiple_instance=configuration["config_multiple_instance"],
          enable_file_cache=configuration["config_enable_file_cache"],
          start_browser=configuration["config_start_browser"])
