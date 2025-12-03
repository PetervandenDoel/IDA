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
        self.fa_timeout = None
        
        
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
        
        
        # Port settings
        port = config.get("Port", {})
        self._set_spin_safely(self.stage_port, port.get("stage", 7))
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
            width=480,
            height=800,
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
            width=460,
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
            width=460,
            height=20,
            font_size=90,
            flex=True,
            justify_content="center",
            color="#666",
        )
        
        y += 35

        # Sweep Settings Section
        StyledLabel(
            container=root,
            text="Sweep Settings",
            variable_name="sweep_title",
            left=10,
            top=y,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y += 30

        # Power
        StyledLabel(
            container=root,
            text="Power",
            variable_name="power_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sweep_power = StyledSpinBox(
            container=root,
            variable_name="power_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=0.0,
            min_value=-50,
            max_value=20,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="power_unit",
            left=220,
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
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sweep_start = StyledSpinBox(
            container=root,
            variable_name="start_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=1540.0,
            min_value=1000,
            max_value=2000,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="start_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # End wavelength
        y += row_h
        StyledLabel(
            container=root,
            text="End Wvl",
            variable_name="end_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sweep_end = StyledSpinBox(
            container=root,
            variable_name="end_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=1580.0,
            min_value=1000,
            max_value=2000,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="end_unit",
            left=220,
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
            text="Step Size",
            variable_name="step_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sweep_step = StyledSpinBox(
            container=root,
            variable_name="step_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=0.001,
            min_value=0.0001,
            max_value=1.0,
            step=0.0001,
        )
        StyledLabel(
            container=root,
            text="nm",
            variable_name="step_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        y += 40

        # Area Scan Settings Section
        StyledLabel(
            container=root,
            text="Area Scan Settings",
            variable_name="area_title",
            left=10,
            top=y,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y += 30

        # X Size
        StyledLabel(
            container=root,
            text="X Size",
            variable_name="x_size_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_x_size = StyledSpinBox(
            container=root,
            variable_name="x_size_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=20.0,
            min_value=1,
            max_value=1000,
            step=1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="x_size_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # X Step
        y += row_h
        StyledLabel(
            container=root,
            text="X Step",
            variable_name="x_step_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_x_step = StyledSpinBox(
            container=root,
            variable_name="x_step_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=1.0,
            min_value=0.1,
            max_value=100,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="x_step_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Y Size
        y += row_h
        StyledLabel(
            container=root,
            text="Y Size",
            variable_name="y_size_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_y_size = StyledSpinBox(
            container=root,
            variable_name="y_size_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=20.0,
            min_value=1,
            max_value=1000,
            step=1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="y_size_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Y Step
        y += row_h
        StyledLabel(
            container=root,
            text="Y Step",
            variable_name="y_step_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_y_step = StyledSpinBox(
            container=root,
            variable_name="y_step_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=1.0,
            min_value=0.1,
            max_value=100,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="y_step_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Pattern
        y += row_h
        StyledLabel(
            container=root,
            text="Pattern",
            variable_name="pattern_lb",
            left=20,
            top=y,
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
            left=130,
            top=y,
            width=80,
            height=24,
        )

        y += 40

        # Fine Align Settings Section
        StyledLabel(
            container=root,
            text="Fine Align Settings",
            variable_name="fa_title",
            left=10,
            top=y,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y += 30

        # Window size
        StyledLabel(
            container=root,
            text="Window Size",
            variable_name="window_size_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.fa_window_size = StyledSpinBox(
            container=root,
            variable_name="window_size_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=10.0,
            min_value=1,
            max_value=100,
            step=1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="window_size_unit",
            left=220,
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
            text="Step Size",
            variable_name="fa_step_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.fa_step_size = StyledSpinBox(
            container=root,
            variable_name="fa_step_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=1.0,
            min_value=0.1,
            max_value=10,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="fa_step_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Max iterations
        y += row_h
        StyledLabel(
            container=root,
            text="Max Iters",
            variable_name="max_iters_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.fa_max_iters = StyledSpinBox(
            container=root,
            variable_name="max_iters_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=10,
            min_value=1,
            max_value=100,
            step=1,
        )

        y += 40

        # Initial Positions Section
        StyledLabel(
            container=root,
            text="Initial Positions",
            variable_name="init_title",
            left=10,
            top=y,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y += 30

        # Initial X Position
        StyledLabel(
            container=root,
            text="Initial X",
            variable_name="init_x_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.init_x = StyledSpinBox(
            container=root,
            variable_name="init_x_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=0.0,
            min_value=-50000,
            max_value=50000,
            step=1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="init_x_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Initial Y Position
        y += row_h
        StyledLabel(
            container=root,
            text="Initial Y",
            variable_name="init_y_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.init_y = StyledSpinBox(
            container=root,
            variable_name="init_y_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=0.0,
            min_value=-50000,
            max_value=50000,
            step=1,
        )
        StyledLabel(
            container=root,
            text="um",
            variable_name="init_y_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        # Initial FA Position
        y += row_h
        StyledLabel(
            container=root,
            text="Initial FA",
            variable_name="init_fa_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.init_fa = StyledSpinBox(
            container=root,
            variable_name="init_fa_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=0.0,
            min_value=-360,
            max_value=360,
            step=0.1,
        )
        StyledLabel(
            container=root,
            text="deg",
            variable_name="init_fa_unit",
            left=220,
            top=y,
            width=40,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )

        y += 40

        # VISA/Port Settings Section
        StyledLabel(
            container=root,
            text="Port Settings",
            variable_name="port_title",
            left=10,
            top=y,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y += 30

        # Stage Port
        StyledLabel(
            container=root,
            text="Stage Port",
            variable_name="stage_port_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.stage_port = StyledSpinBox(
            container=root,
            variable_name="stage_port_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=7,
            min_value=1,
            max_value=99,
            step=1,
        )

        # Sensor Port
        y += row_h
        StyledLabel(
            container=root,
            text="Sensor Port",
            variable_name="sensor_port_lb",
            left=20,
            top=y,
            width=100,
            height=row_h,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sensor_port = StyledSpinBox(
            container=root,
            variable_name="sensor_port_in",
            left=130,
            top=y,
            width=80,
            height=24,
            value=20,
            min_value=1,
            max_value=99,
            step=1,
        )

        y += 40

        # Configuration Section
        StyledLabel(
            container=root,
            text="Configuration Labels",
            variable_name="config_title",
            left=10,
            top=y,
            width=200,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        
        y += 30

        # Stage Configuration
        StyledLabel(
            container=root,
            text="Stage Type",
            variable_name="stage_config_lb",
            left=20,
            top=y,
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
            left=130,
            top=y,
            width=120,
            height=24,
        )

        # Sensor Configuration
        y += row_h
        StyledLabel(
            container=root,
            text="Sensor Type",
            variable_name="sensor_config_lb",
            left=20,
            top=y,
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
            left=130,
            top=y,
            width=120,
            height=24,
        )

        y += 50
        
        # Save buttons
        self.save_user_btn = StyledButton(
            container=root,
            text="Save User Defaults",
            variable_name="save_user_btn",
            left=50,
            top=y,
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
            left=270,
            top=y,
            width=160,
            height=35,
            normal_color="#007bff",
            press_color="#0056b3",
            font_size=100,
        )

        # Wire up events
        self.save_user_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_save_user))
        self.save_project_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_save_project))

        return root

    # ---------------- EVENT HANDLERS ----------------

    def onclick_save_user(self):
        """Save current settings as user defaults."""
        try:
            # Build config from UI
            config = self._build_config_from_ui()
            
            # Save as user defaults
            if self.config_manager:
                self.config_manager.save_user_defaults(config)
                print(f"[Default_Settings] Saved user defaults for {self.current_user}")
            else:
                print("[Default_Settings] Config manager not initialized")
                
        except Exception as e:
            print(f"[Default_Settings] Error saving user defaults: {e}")

    def onclick_save_project(self):
        """Save current settings as project overrides."""
        try:
            # Build config from UI
            config = self._build_config_from_ui()
            
            # Save as project config
            if self.config_manager:
                self.config_manager.save_project_config(config)
                print(f"[Default_Settings] Saved project config for {self.current_user}/{self.current_project}")
            else:
                print("[Default_Settings] Config manager not initialized")
                
        except Exception as e:
            print(f"[Default_Settings] Error saving project config: {e}")

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
                "InitialPositions": {},
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