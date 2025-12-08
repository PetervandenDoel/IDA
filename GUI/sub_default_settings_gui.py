import datetime
import json
import os
import threading

from remi import App, start
from GUI.lib_gui import *

SHARED_PATH = os.path.join("database", "shared_memory.json")


class DefaultSettingsConfig(App):
    """User and project default settings configuration panel."""

    def __init__(self, *args, **kwargs):
        # Track shared_memory.json changes
        self._user_stime = None
        self._first_check = True

        # Current user and project
        self.current_user = "Guest"
        self.current_project = "MyProject"

        # Configuration manager
        self.config_manager = None

        # Current config data
        self.user_defaults = {}
        self.project_config = {}

        # Widgets - Sweep Settings
        self.sweep_power = None
        self.sweep_start = None
        self.sweep_end = None
        self.sweep_step = None
        
        # Widgets - Area Scan Settings
        self.area_x_size = None
        self.area_x_step = None
        self.area_y_size = None
        self.area_y_step = None
        self.area_pattern_dd = None
        
        # Widgets - Fine Align Settings
        self.fa_window_size = None
        self.fa_step_size = None
        self.fa_max_iters = None
        self.fa_min_grad_ss = None
        self.fa_primary_detector = None
        self.fa_ref_wl = None
        
        # Widgets - Initial Positions
        self.init_fa = None
        
        # Widgets - VISA/Port Settings
        self.stage_port = None
        self.sensor_port = None
        
        # Widgets - Configuration Labels
        self.stage_config_dd = None
        self.sensor_config_dd = None
        
        # Buttons
        self.save_user_btn = None
        self.save_project_btn = None

        # REMI init (support editing_mode)
        editing_mode = kwargs.pop("editing_mode", False)
        super_kwargs = {}
        if not editing_mode:
            super_kwargs["static_file_path"] = {"my_res": "./res/"}
        super(DefaultSettingsConfig, self).__init__(*args, **super_kwargs)

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

    @staticmethod
    def _set_dropdown_safely(widget, value):
        """Set a dropdown if widget/value are valid."""
        if widget is None or value is None:
            return
        try:
            widget.set_value(str(value))
        except Exception:
            pass

    # ---------------- DATA LOADING ----------------

    def _load_from_shared(self):
        """Load current user/project and refresh config."""
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.current_user = data.get("User", "Guest")
            self.current_project = data.get("Project", "MyProject")
            
            # Initialize config manager
            from GUI.lib_gui import UserConfigManager
            self.config_manager = UserConfigManager(self.current_user, self.current_project)
            
            # Load user defaults and project config separately
            self.user_defaults = self.config_manager.get_user_defaults()
            self.project_config = self.config_manager.get_project_overrides()
            
            # Update UI with current project settings (merged view)
            merged_config = self.config_manager.load_config()
            self._update_ui_from_config(merged_config)
            
        except Exception as e:
            print(f"[Default_Settings] Error loading config: {e}")

    def _update_ui_from_config(self, config):
        """Update UI widgets from configuration."""
        # Sweep settings
        sweep = config.get("Sweep", {})
        self._set_spin_safely(self.sweep_power, sweep.get("power", 0.0))
        self._set_spin_safely(self.sweep_start, sweep.get("start", 1540.0))
        self._set_spin_safely(self.sweep_end, sweep.get("end", 1580.0))
        self._set_spin_safely(self.sweep_step, sweep.get("step", 0.001))
        
        # Area scan settings
        area = config.get("AreaS", {})
        self._set_spin_safely(self.area_x_size, area.get("x_size", 20.0))
        self._set_spin_safely(self.area_x_step, area.get("x_step", 1.0))
        self._set_spin_safely(self.area_y_size, area.get("y_size", 20.0))
        self._set_spin_safely(self.area_y_step, area.get("y_step", 1.0))
        self._set_dropdown_safely(self.area_pattern_dd, area.get("pattern", "spiral"))
        
        # Fine align settings
        fine_a = config.get("FineA", {})
        self._set_spin_safely(self.fa_window_size, fine_a.get("window_size", 10.0))
        self._set_spin_safely(self.fa_step_size, fine_a.get("step_size", 1.0))
        self._set_spin_safely(self.fa_max_iters, fine_a.get("max_iters", 10))
        self._set_spin_safely(self.fa_timeout, fine_a.get("timeout_s", 30))
        
        # Initial positions
        initial_pos = config.get("InitialPositions", {})
        self._set_spin_safely(self.init_fa, initial_pos.get("fa", 0.0))
        
        # Port settings
        port = config.get("Port", {})
        self._set_spin_safely(self.stage_port, port.get("stage", 4))
        self._set_spin_safely(self.sensor_port, port.get("sensor", 20))
        
        # Configuration settings
        configuration = config.get("Configuration", {})
        self._set_dropdown_safely(self.stage_config_dd, configuration.get("stage", ""))
        self._set_dropdown_safely(self.sensor_config_dd, configuration.get("sensor", ""))

    # ---------------- UI CONSTRUCTION ----------------

    def construct_ui(self):
        root = StyledContainer(
            variable_name="default_settings_container",
            left=0,
            top=0,
            width=680,
            height=500,
        )

        y = 10
        row_h = 28
        
        # Title
        StyledLabel(
            container=root,
            text=f"Default Settings",
            variable_name="title",
            left=10,
            top=y,
            width=660,
            height=25,
            font_size=120,
            flex=True,
            justify_content="center",
            color="#222",
            bold=True,
        )
        
        y += 35
        
        # User/Project info
        StyledLabel(
            container=root,
            text=f"User: {self.current_user} | Project: {self.current_project}",
            variable_name="user_info",
            left=10,
            top=y,
            width=660,
            height=20,
            font_size=90,
            flex=True,
            justify_content="center",
            color="#666",
        )
        
        y += 35
        
        # Set up 2-column layout
        left_x = 10
        right_x = 350
        y_left = y
        y_right = y
        
        # Create the entire UI with 2-column layout
        self._create_left_column(root, left_x, y_left, row_h)
        self._create_right_column(root, right_x, y_right, row_h)
        
        # Save buttons at bottom
        self._create_save_buttons(root)

        return root

    def _create_left_column(self, root, left_x, y_left, row_h):
        """Create left column with Sweep and Area Scan settings."""
        # Sweep Settings Section
        StyledLabel(
            container=root,
            text="Sweep Settings",
            variable_name="sweep_title",
            left=left_x,
            top=y_left,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y_left += 30

        # Sweep fields
        self._create_field(root, left_x, y_left, row_h, "Power", "power", "dBm", 0.0, -50, 20, 0.1)
        self.sweep_power = root.children["power_in"]
        
        y_left += row_h
        self._create_field(root, left_x, y_left, row_h, "Start Wvl", "start", "nm", 1540.0, 1000, 2000, 0.1)
        self.sweep_start = root.children["start_in"]
        
        y_left += row_h  
        self._create_field(root, left_x, y_left, row_h, "End Wvl", "end", "nm", 1580.0, 1000, 2000, 0.1)
        self.sweep_end = root.children["end_in"]
        
        y_left += row_h
        self._create_field(root, left_x, y_left, row_h, "Step Size", "step", "nm", 0.001, 0.0001, 1.0, 0.0001)
        self.sweep_step = root.children["step_in"]
        
        y_left += 40
        
        # Area Scan Settings
        StyledLabel(
            container=root,
            text="Area Scan Settings",
            variable_name="area_title",
            left=left_x,
            top=y_left,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y_left += 30
        
        # Area Scan fields
        self._create_field(root, left_x, y_left, row_h, "X Size", "x_size", "um", 20.0, 1, 1000, 1)
        self.area_x_size = root.children["x_size_in"]
        
        y_left += row_h
        self._create_field(root, left_x, y_left, row_h, "X Step", "x_step", "um", 1.0, 0.1, 100, 0.1)
        self.area_x_step = root.children["x_step_in"]
        
        y_left += row_h
        self._create_field(root, left_x, y_left, row_h, "Y Size", "y_size", "um", 20.0, 1, 1000, 1)
        self.area_y_size = root.children["y_size_in"]
        
        y_left += row_h
        self._create_field(root, left_x, y_left, row_h, "Y Step", "y_step", "um", 1.0, 0.1, 100, 0.1)
        self.area_y_step = root.children["y_step_in"]
        
        # Pattern dropdown
        y_left += row_h
        StyledLabel(
            container=root,
            text="Pattern",
            variable_name="pattern_lb",
            left=left_x+10,
            top=y_left,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_pattern_dd = StyledDropDown(
            container=root,
            text=["spiral", "crosshair"],
            variable_name="pattern_dd",
            left=left_x+120,
            top=y_left,
            width=80,
            height=24,
        )
    
    def _create_field(self, root, left_x, y, row_h, label, prefix, unit, value, min_val, max_val, step):
        """Helper to create label + spinbox + unit."""
        StyledLabel(
            container=root,
            text=label,
            variable_name=f"{prefix}_lb",
            left=left_x+10,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        StyledSpinBox(
            container=root,
            variable_name=f"{prefix}_in",
            left=left_x+120,
            top=y,
            width=80,
            height=24,
            value=value,
            min_value=min_val,
            max_value=max_val,
            step=step,
        )
        if unit:
            StyledLabel(
                container=root,
                text=unit,
                variable_name=f"{prefix}_unit",
                left=left_x+210,
                top=y,
                width=40,
                height=row_h,
                font_size=100,
                flex=True,
                justify_content="left",
                color="#222",
            )
    
    def _create_right_column(self, root, right_x, y_right, row_h):
        """Create right column with Fine Align, Initial Positions, Ports, and Configuration."""
        # Fine Align Settings
        StyledLabel(
            container=root,
            text="Fine Align Settings",
            variable_name="fa_title",
            left=right_x,
            top=y_right,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y_right += 30
        
        # Fine Align fields
        self._create_field(root, right_x, y_right, row_h, "Window", "window", "um", 10.0, 1, 100, 1)
        self.fa_window_size = root.children["window_in"]
        
        y_right += row_h
        self._create_field(root, right_x, y_right, row_h, "Step", "fa_step", "um", 1.0, 0.1, 10, 0.1)
        self.fa_step_size = root.children["fa_step_in"]
        
        y_right += row_h
        self._create_field(root, right_x, y_right, row_h, "Max Iters", "max_iters", "", 10, 1, 100, 1)
        self.fa_max_iters = root.children["max_iters_in"]
        
        y_right += row_h
        self._create_field(root, right_x, y_right, row_h, "Timeout", "timeout", "s", 30, 1, 300, 1)
        self.fa_timeout = root.children["timeout_in"]
        
        y_right += 40
        
        # Initial Positions
        StyledLabel(
            container=root,
            text="Initial Positions",
            variable_name="init_title",
            left=right_x,
            top=y_right,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y_right += 30
        
        self._create_field(root, right_x, y_right, row_h, "Init X", "init_x", "um", 0.0, -50000, 50000, 1)
        self.init_x = root.children["init_x_in"]
        
        y_right += row_h
        self._create_field(root, right_x, y_right, row_h, "Init Y", "init_y", "um", 0.0, -50000, 50000, 1)
        self.init_y = root.children["init_y_in"]
        
        y_right += row_h
        self._create_field(root, right_x, y_right, row_h, "Init FA", "init_fa", "deg", 0.0, -360, 360, 0.1)
        self.init_fa = root.children["init_fa_in"]
        
        y_right += 40
        
        # Port Settings
        StyledLabel(
            container=root,
            text="Port Settings",
            variable_name="port_title",
            left=right_x,
            top=y_right,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y_right += 30
        
        self._create_field(root, right_x, y_right, row_h, "Stage Port", "stage_port", "", 7, 1, 99, 1)
        self.stage_port = root.children["stage_port_in"]
        
        y_right += row_h
        self._create_field(root, right_x, y_right, row_h, "Sensor Port", "sensor_port", "", 20, 1, 99, 1)
        self.sensor_port = root.children["sensor_port_in"]
        
        y_right += 40
        
        # Configuration Labels
        StyledLabel(
            container=root,
            text="Configuration Labels",
            variable_name="config_title",
            left=right_x,
            top=y_right,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y_right += 30
        
        # Stage Configuration
        StyledLabel(
            container=root,
            text="Stage Type",
            variable_name="stage_config_lb",
            left=right_x+10,
            top=y_right,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.stage_config_dd = StyledDropDown(
            container=root,
            text=["", "Thorlabs_controller", "Corvus_controller", "Dummy_controller"],
            variable_name="stage_config_dd",
            left=right_x+120,
            top=y_right,
            width=120,
            height=24,
        )
        
        # Sensor Configuration
        y_right += row_h
        StyledLabel(
            container=root,
            text="Sensor Type",
            variable_name="sensor_config_lb",
            left=right_x+10,
            top=y_right,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sensor_config_dd = StyledDropDown(
            container=root,
            text=["", "N7744A", "Dummy_sensor"],
            variable_name="sensor_config_dd",
            left=right_x+120,
            top=y_right,
            width=120,
            height=24,
        )
    
    def _create_save_buttons(self, root):
        """Create save buttons at bottom."""
        y_buttons = 450
        
        self.save_user_btn = StyledButton(
            container=root,
            text="Save User Defaults",
            variable_name="save_user_btn",
            left=50,
            top=y_buttons,
            width=160,
            height=35,
            normal_color="#28a745",
            press_color="#1e7e34",
            font_size=100,
        )

        self.save_project_btn = StyledButton(
            container=root,
            text="Save Project Settings",
            variable_name="save_project_btn",
            left=470,
            top=y_buttons,
            width=160,
            height=35,
            normal_color="#007bff",
            press_color="#0056b3",
            font_size=100,
        )

        # Wire up events
        self.save_user_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_save_user))
        self.save_project_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_save_project))

    # ---------------- EVENT HANDLERS ----------------

    def onclick_save_user(self):
        """Save current settings as user defaults."""
        try:
            # Build config from UI
            config = self._build_config_from_ui()
            
            # Save to user defaults via config manager
            if self.config_manager:
                self.config_manager.save_user_defaults(config)
                print(f"[Default_Settings] Saved user defaults for {self.current_user}")
            else:
                print("[Default_Settings] Config manager not initialized")
            
            # Also update shared_memory.json like other sub files
            self._save_to_shared_memory(config)
                
        except Exception as e:
            print(f"[Default_Settings] Error saving user defaults: {e}")

    def onclick_save_project(self):
        """Save current settings as project overrides."""
        try:
            # Build config from UI
            config = self._build_config_from_ui()
            
            # Save to project config via config manager
            if self.config_manager:
                self.config_manager.save_project_config(config)
                print(f"[Default_Settings] Saved project config for {self.current_user}/{self.current_project}")
            else:
                print("[Default_Settings] Config manager not initialized")
            
            # Also update shared_memory.json like other sub files
            self._save_to_shared_memory(config)
                
        except Exception as e:
            print(f"[Default_Settings] Error saving project config: {e}")

    def _save_to_shared_memory(self, config):
        """Save config sections to shared_memory.json using File utility like other sub files."""
        try:
            # Save each section to shared memory using the same pattern as other sub files
            for section, data in config.items():
                file = File("shared_memory", section, data)
                file.save()
            print(f"[Default_Settings] Updated shared_memory.json")
        except Exception as e:
            print(f"[Default_Settings] Error updating shared_memory.json: {e}")

    def _build_config_from_ui(self):
        """Build configuration dictionary from UI widget values."""
        try:
            config = {
                "Sweep": {
                    "power": float(self.sweep_power.get_value()),
                    "start": float(self.sweep_start.get_value()),
                    "end": float(self.sweep_end.get_value()),
                    "step": float(self.sweep_step.get_value()),
                },
                "AreaS": {
                    "x_size": float(self.area_x_size.get_value()),
                    "x_step": float(self.area_x_step.get_value()),
                    "y_size": float(self.area_y_size.get_value()),
                    "y_step": float(self.area_y_step.get_value()),
                    "pattern": str(self.area_pattern_dd.get_value()),
                },
                "FineA": {
                    "window_size": float(self.fa_window_size.get_value()),
                    "step_size": float(self.fa_step_size.get_value()),
                    "max_iters": int(self.fa_max_iters.get_value()),
                    "timeout_s": int(self.fa_timeout.get_value()),
                },
                "InitialPositions": {
                    "x": float(self.init_x.get_value()),
                    "y": float(self.init_y.get_value()),
                    "fa": float(self.init_fa.get_value()),
                },
                "Port": {
                    "stage": int(self.stage_port.get_value()),
                    "sensor": int(self.sensor_port.get_value()),
                },
                "Configuration": {
                    "stage": str(self.stage_config_dd.get_value()),
                    "sensor": str(self.sensor_config_dd.get_value()),
                }
            }
            return config
        except Exception as e:
            print(f"[Default_Settings] Error building config from UI: {e}")
            return {}


# ---- REMI SERVER ----
def main():
    start(DefaultSettingsConfig, address='0.0.0.0', port=7009,
          start_browser=False, multiple_instance=False)


if __name__ == '__main__':
    main()