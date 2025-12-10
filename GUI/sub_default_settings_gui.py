import datetime
import json
import os
import threading

from remi import App, start
from GUI.lib_gui import *

SHARED_PATH = os.path.join("database", "shared_memory.json")


def update_detector_window_setting(name, payload):
    """Update detector window settings in shared_memory.json."""
    try:
        with open(SHARED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    dws = data.get("DetectorWindowSettings", {})
    if not isinstance(dws, dict):
        dws = {}

    # Overwrite the specific setting
    dws[name] = payload
    dws["Detector_Change"] = "1"
    data["DetectorWindowSettings"] = dws

    with open(SHARED_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class DefaultSettingsConfig(App):
    """User and project default settings configuration panel."""

    def __init__(self, *args, **kwargs):
        # Track shared_memory.json changes
        self._user_stime = None
        self._first_check = True
        # Track last user/project so we only reload when they change
        self._last_user = None
        self._last_project = None

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
        self.area_spiral_step = None
        self.area_pattern_dd = None
        self.area_primary_detector_dd = None
        self.area_plot_dd = None

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

        # Widgets - Detector Window Settings (4 slots with buttons)
        self.ch1_range = None
        self.ch1_ref = None
        self.ch2_range = None
        self.ch2_ref = None
        self.ch3_range = None
        self.ch3_ref = None
        self.ch4_range = None
        self.ch4_ref = None
        # Auto range buttons
        self.apply_auto_btn1 = None
        self.apply_auto_btn2 = None
        self.apply_auto_btn3 = None
        self.apply_auto_btn4 = None
        # Apply range/ref buttons
        self.apply_range_btn1 = None
        self.apply_ref_btn1 = None
        self.apply_range_btn2 = None
        self.apply_ref_btn2 = None
        self.apply_range_btn3 = None
        self.apply_ref_btn3 = None
        self.apply_range_btn4 = None
        self.apply_ref_btn4 = None

        # Buttons
        self.save_user_btn = None
        self.save_project_btn = None

        # Root container reference
        self._ui_container = None

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
        """
        Reload configuration ONLY when user/project changes.

        Fix for Bug #1:
        Previously, any write to shared_memory.json (including detector apply buttons)
        would trigger a full reload via _load_from_shared(), which overwrote the
        current UI state with defaults / disk values and reset things like
        Fine Align primary detector = Max.
        """
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
            # Inspect shared_memory to see if User/Project actually changed
            try:
                with open(SHARED_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                return

            new_user = data.get("User", self.current_user)
            new_project = data.get("Project", self.current_project)

            # Only reload if user or project changed
            if new_user != self.current_user or new_project != self.current_project:
                self.current_user = new_user
                self.current_project = new_project
                self._last_user = new_user
                self._last_project = new_project
                self._load_from_shared()
            # If only DetectorWindowSettings or other flags changed, we ignore it
            # to avoid blowing away local UI changes.

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

    def _set_spin_safely_by_name(self, widget_name, value):
        """Set a spinbox by name if available."""
        try:
            widget = getattr(self, widget_name, None)
            if widget is None:
                # Try to find in UI children if it's a dynamic widget
                container = getattr(self, "construct_ui", lambda: None)()
                if hasattr(container, "children") and widget_name in container.children:
                    widget = container.children[widget_name]
            if widget is not None and value is not None:
                widget.set_value(float(value))
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

    # ---------------- DATA LOADING ----------------

    def _load_from_shared(self):
        """Load current user/project and refresh config."""
        try:
            with open(SHARED_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.current_user = data.get("User", "Guest")
            self.current_project = data.get("Project", "MyProject")
            self._last_user = self.current_user
            self._last_project = self.current_project

            # Initialize config manager
            from GUI.lib_gui import UserConfigManager

            self.config_manager = UserConfigManager(self.current_user, self.current_project)

            # Load user defaults and project config separately
            self.user_defaults = self.config_manager.get_user_defaults()
            self.project_config = self.config_manager.get_project_overrides()

            # Update UI with current project settings (merged view)
            merged_config = self.config_manager.load_config()
            self._update_ui_from_config(merged_config)

            try:
                if getattr(self, "user_info_label", None) is not None:
                    self.user_info_label.set_text(
                        f"User: {self.current_user} | Project: {self.current_project}"
                    )
            except Exception:
                pass


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

        # pattern is stored lowercase in AreaS: "spiral" / "crosshair"
        pattern = str(area.get("pattern", "spiral")).lower()
        spiral = (pattern == "spiral")

        # Sizes
        self._set_spin_safely(self.area_x_size, area.get("x_size", 50.0))
        self._set_spin_safely(self.area_y_size, area.get("y_size", 50.0))

        # Steps: mirror area_scan behaviour
        if spiral:
            # For spiral, x_step == y_step == step_size
            step_val = area.get("x_step", area.get("y_step", 5.0))
            self._set_spin_safely(self.area_spiral_step, step_val)
            self._set_spin_safely(self.area_x_step, step_val)
            self._set_spin_safely(self.area_y_step, step_val)
        else:
            # Crosshair: independent x/y
            self._set_spin_safely(self.area_x_step, area.get("x_step", 5.0))
            self._set_spin_safely(self.area_y_step, area.get("y_step", 5.0))
            # keep spiral box sensible (e.g. match x_step)
            self._set_spin_safely(self.area_spiral_step, area.get("x_step", 5.0))

        # Pattern dropdown uses nice labels
        self._set_dropdown_safely(
            self.area_pattern_dd,
            "Spiral" if spiral else "Crosshair",
        )

        # Primary detector: stored as "ch1"/"ch2"/"max"
        pd = str(area.get("primary_detector", "max")).upper()
        if pd not in ("CH1", "CH2", "MAX"):
            pd = "MAX"
        try:
            self.area_primary_detector_dd.set_value(pd)
        except Exception:
            pass

        # Plot: "New" / "Previous"
        plot_val = area.get("plot", "New")
        if isinstance(plot_val, str):
            low = plot_val.lower()
            if low == "previous":
                plot_val = "Previous"
            else:
                plot_val = "New"
        try:
            self.area_plot_dd.set_value(plot_val)
        except Exception:
            pass



        # Fine align settings
        fine_a = config.get("FineA", {})
        self._set_spin_safely(self.fa_window_size, fine_a.get("window_size", 10.0))
        self._set_spin_safely(self.fa_step_size, fine_a.get("step_size", 1.0))
        self._set_spin_safely(self.fa_max_iters, fine_a.get("max_iters", 10))
        self._set_spin_safely(self.fa_min_grad_ss, fine_a.get("min_gradient_ss", 0.1))
        self._set_dropdown_safely(self.fa_primary_detector, fine_a.get("detector", "Max"))
        self._set_spin_safely(self.fa_ref_wl, fine_a.get("ref_wl", 1550.0))

        # Initial positions
        initial_pos = config.get("InitialPositions", {})
        self._set_spin_safely(self.init_fa, initial_pos.get("fa", 8.0))

        # Detector window settings (4 slots)
        detector_settings = config.get("DetectorWindowSettings", {})
        detector_list = []
        for i in range(1,5):
            detector_list.append(
                detector_settings.get(f'DetectorRange_Ch{i}', {}).get(
                    "range_dbm", -10
                )
            )
        self._set_spin_safely(self.ch1_range, detector_list[0])
        self._set_spin_safely(self.ch1_ref, detector_settings.get("ch1_ref", -30))
        self._set_spin_safely(self.ch2_range, detector_list[1])
        self._set_spin_safely(self.ch2_ref, detector_settings.get("ch2_ref", -30))
        self._set_spin_safely(self.ch3_range, detector_list[2])
        self._set_spin_safely(self.ch3_ref, detector_settings.get("ch3_ref", -30))
        self._set_spin_safely(self.ch4_range, detector_list[3])
        self._set_spin_safely(self.ch4_ref, detector_settings.get("ch4_ref", -30))

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
        # Proper 3-column layout based on other sub window patterns
        # Total width calculation: 240 + 240 + 240 = 720px (plus margins)
        root = StyledContainer(
            variable_name="default_settings_container",
            left=0,
            top=0,
            width=870,  # Increased from 750 to prevent overflow
            height=620,  # Height stays same
        )

        y = 10

        # Title
        StyledLabel(
            container=root,
            text=f"Default Settings",
            variable_name="title",
            left=10,
            top=y,
            width=930,  # Updated for new container width
            height=25,
            font_size=120,
            flex=True,
            justify_content="center",
            color="#222",
            bold=True,
        )

        y += 30

        # User/Project info
        self.user_info_label = StyledLabel(
            container=root,
            text=f"User: {self.current_user} | Project: {self.current_project}",
            variable_name="user_info",
            left=10,
            top=y,
            width=930,  # Updated for new container width
            height=20,
            font_size=90,
            flex=True,
            justify_content="center",
            color="#666",
        )


        y += 30

        # Set up 3-column layout with proper spacing (wider for bigger container)
        col_width = 300  # Increased width per column
        col1_x = 10      # Left column
        col2_x = 320     # Middle column (10 + 300 + 10)
        col3_x = 560     # Right column moved left by 30px (was 630)
        start_y = y

        # Create all three columns
        self._create_column1_sweep_area(root, col1_x, start_y, col_width)
        self._create_column2_fine_align_positions(root, col2_x, start_y, col_width)
        self._create_column3_detector_ports_config(root, col3_x, start_y, col_width)

        # Save buttons at bottom
        self._create_save_buttons(root)

        # Store reference for dynamic widget access
        self._ui_container = root
        return root

    def _create_column1_sweep_area(self, root, col_x, y, col_width):
        """Create column 1 with Sweep and Area Scan settings following area_scan pattern."""
        # Layout constants matching sub_area_scan_setting_gui.py:36-38 (adjusted for wider column)
        LBL_W, INP_W, UNIT_W = 90, 70, 50  # Increased widths
        LBL_X = col_x + 10
        INP_X = LBL_X + LBL_W + 10  # More spacing between label and input
        UNIT_X = INP_X + INP_W + 20  # Even more spacing to prevent overlap
        ROW = 30

        # Sweep Settings Section
        StyledLabel(
            container=root,
            text="Sweep Settings",
            variable_name="sweep_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += ROW

        # Power
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Power",
            "power",
            "dBm",
            0.0,
            -50,
            20,
            0.1,
        )
        self.sweep_power = root.children["power_in"]
        y += ROW

        # Start Wvl
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Start Wvl",
            "start",
            "nm",
            1540.0,
            1000,
            2000,
            0.1,
        )
        self.sweep_start = root.children["start_in"]
        y += ROW

        # End Wvl
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "End Wvl",
            "end",
            "nm",
            1580.0,
            1000,
            2000,
            0.1,
        )
        self.sweep_end = root.children["end_in"]
        y += ROW

        # Step Size
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Step Size",
            "step",
            "nm",
            0.001,
            0.0001,
            1.0,
            0.0001,
        )
        self.sweep_step = root.children["step_in"]
        y += ROW + 10

        # Area Scan Settings
        StyledLabel(
            container=root,
            text="Area Scan Settings",
            variable_name="area_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += ROW

        # X Size
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "X Size",
            "x_size",
            "um",
            50.0,
            1,
            1000,
            1,
        )
        self.area_x_size = root.children["x_size_in"]
        y += ROW

        # Y Size
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Y Size",
            "y_size",
            "um",
            50.0,
            1,
            1000,
            1,
        )
        self.area_y_size = root.children["y_size_in"]
        y += ROW

        # X Step
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "X Step",
            "x_step",
            "um",
            5.0,
            0.1,
            100,
            0.1,
        )
        self.area_x_step = root.children["x_step_in"]
        y += ROW

        # Y Step
        self._create_field_3col(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Y Step",
            "y_step",
            "um",
            5.0,
            0.1,
            100,
            0.1,
        )
        self.area_y_step = root.children["y_step_in"]
        y += ROW

        # Step Size for Spiral (like in sub_area_scan_setting_gui.py)
        self._create_field_3col(
            root, LBL_X, INP_X, UNIT_X, y, LBL_W, INP_W, UNIT_W,
            "Step Size (Spiral)", "spiral_step", "um", 5.0, 0.1, 100, 0.1
        )
        self.area_spiral_step = root.children["spiral_step_in"]
        y += ROW

        # Pattern dropdown
        StyledLabel(
            container=root,
            text="Pattern",
            variable_name="pattern_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_pattern_dd = StyledDropDown(
            container=root,
            text=["Spiral", "Crosshair"],
            variable_name="pattern_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24,
            position="absolute",
        )
        self.area_pattern_dd.set_value("Spiral")
        y += ROW

        # Primary Detector (CH1 / CH2 / MAX) – matches area_scan
        StyledLabel(
            container=root,
            text="Primary Detector",
            variable_name="area_primary_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_primary_detector_dd = StyledDropDown(
            container=root,
            text=["CH1", "CH2", "MAX"],
            variable_name="area_primary_detector_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24,
            position="absolute",
        )
        self.area_primary_detector_dd.set_value("MAX")
        y += ROW

        # Plot selector (New / Previous) – matches area_scan
        StyledLabel(
            container=root,
            text="Plot",
            variable_name="area_plot_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.area_plot_dd = StyledDropDown(
            container=root,
            text=["New", "Previous"],
            variable_name="area_plot_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W,
            height=24,
            position="absolute",
        )
        self.area_plot_dd.set_value("New")
        y += ROW + 15

        # Configuration Labels (moved from column 2)
        StyledLabel(
            container=root,
            text="Configuration Labels",
            variable_name="config_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # Stage Configuration dropdown
        StyledLabel(
            container=root,
            text="Stage",
            variable_name="stage_config_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.stage_config_dd = StyledDropDown(
            container=root,
            text=[
                "",
                "MMC100_controller",
                "Thorlabs_controller",
                "Corvus_controller",
                "Dummy_controller",
            ],
            variable_name="stage_config_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W + 40,  # Wider for dropdown
            height=24,
            position="absolute",
        )
        self.stage_config_dd.set_value("MMC100_controller")  # Set default
        y += ROW

        # Sensor Configuration dropdown
        StyledLabel(
            container=root,
            text="Sensor",
            variable_name="sensor_config_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.sensor_config_dd = StyledDropDown(
            container=root,
            text=["", "8164B_NIR", "N7744A", "Dummy_sensor"],
            variable_name="sensor_config_dd",
            left=INP_X,
            top=y,
            width=INP_W + UNIT_W + 40,  # Wider for dropdown
            height=24,
            position="absolute",
        )
        self.sensor_config_dd.set_value("8164B_NIR")  # Set default

    def _create_field_3col(
        self,
        root,
        lbl_x,
        inp_x,
        unit_x,
        y,
        lbl_w,
        inp_w,
        unit_w,
        label,
        prefix,
        unit,
        value,
        min_val,
        max_val,
        step,
    ):
        """Helper to create label + spinbox + unit in 3-column layout."""
        StyledLabel(
            container=root,
            text=label,
            variable_name=f"{prefix}_lb",
            left=lbl_x,
            top=y,
            width=lbl_w,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        StyledSpinBox(
            container=root,
            variable_name=f"{prefix}_in",
            left=inp_x,
            top=y,
            width=inp_w,
            height=24,
            value=value,
            min_value=min_val,
            max_value=max_val,
            step=step,
            position="absolute",
        )
        if unit:
            StyledLabel(
                container=root,
                text=unit,
                variable_name=f"{prefix}_unit",
                left=unit_x,
                top=y,
                width=unit_w,
                height=24,
                font_size=100,
                flex=True,
                justify_content="left",
                color="#222",
            )

    def _create_column2_fine_align_positions(self, root, col_x, y, col_width):
        """Create column 2 with Fine Align and Initial Positions following fine_align pattern."""
        # Layout constants matching sub_fine_align_setting_gui.py:45-70 (adjusted for wider column)
        LBL_X = col_x + 10
        INP_X = col_x + 90   # More spacing for labels
        UNIT_X = col_x + 160 # Even more spacing to prevent overlap
        LBL_W = 75           # Wider labels
        INP_W = 50
        UNIT_W = 40          # Wider units for better spacing
        ROW = 32  # Fine align uses 32px spacing

        # Fine Align Settings (matching sub_fine_align_setting_gui.py pattern)
        StyledLabel(
            container=root,
            text="Fine Align Settings",
            variable_name="fa_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # Window Size
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Window",
            "window",
            "um",
            10.0,
            1,
            100,
            1,
        )
        self.fa_window_size = root.children["window_in"]
        y += ROW

        # Step Size
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Step Size",
            "fa_step",
            "um",
            1.0,
            0.1,
            10,
            0.1,
        )
        self.fa_step_size = root.children["fa_step_in"]
        y += ROW

        # Max Iters
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Max Iters",
            "max_iters",
            "",
            10,
            1,
            50,
            1,
        )
        self.fa_max_iters = root.children["max_iters_in"]
        y += ROW

        # Min Grad SS (new from user changes)
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Min Grad SS",
            "min_grad_ss",
            "um",
            0.1,
            0.001,
            10,
            0.1,
        )
        self.fa_min_grad_ss = root.children["min_grad_ss_in"]
        y += ROW

        # Primary Detector dropdown (new from user changes)
        StyledLabel(
            container=root,
            text="Detector",
            variable_name="fa_detector_lb",
            left=LBL_X,
            top=y,
            width=LBL_W,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.fa_primary_detector = StyledDropDown(
            container=root,
            text=["ch1", "ch2", "Max"],
            variable_name="fa_detector_dd",
            left=INP_X,
            top=y,
            width=60,
            height=24,
            position="absolute",
        )
        y += ROW

        # Reference Wavelength (new from user changes)
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Ref WL",
            "ref_wl",
            "nm",
            1550.0,
            1450.0,
            1650.0,
            0.01,
        )
        self.fa_ref_wl = root.children["ref_wl_in"]
        y += ROW + 10

        # Initial Positions (simplified)
        StyledLabel(
            container=root,
            text="Initial Positions",
            variable_name="init_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # Init FA only (as per user's changes - removed init_x and init_y) - default 8 degrees
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Init FA",
            "init_fa",
            "deg",
            8.0,
            -360,
            360,
            0.1,
        )
        self.init_fa = root.children["init_fa_in"]
        y += ROW + 15

        # Port Settings (moved from column 3)
        StyledLabel(
            container=root,
            text="Port Settings",
            variable_name="port_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # Stage Port (int values)
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Stage Port",
            "stage_port",
            "",
            4,
            1,
            99,
            1,
        )
        self.stage_port = root.children["stage_port_in"]
        y += ROW

        # Sensor Port (int values)
        self._create_field_fine_align(
            root,
            LBL_X,
            INP_X,
            UNIT_X,
            y,
            LBL_W,
            INP_W,
            UNIT_W,
            "Sensor Port",
            "sensor_port",
            "",
            20,
            1,
            99,
            1,
        )
        self.sensor_port = root.children["sensor_port_in"]

    def _create_field_fine_align(
        self,
        root,
        lbl_x,
        inp_x,
        unit_x,
        y,
        lbl_w,
        inp_w,
        unit_w,
        label,
        prefix,
        unit,
        value,
        min_val,
        max_val,
        step,
    ):
        """Helper for fine align style fields."""
        StyledLabel(
            container=root,
            text=label,
            variable_name=f"{prefix}_lb",
            left=lbl_x,
            top=y,
            width=lbl_w,
            height=24,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        StyledSpinBox(
            container=root,
            variable_name=f"{prefix}_in",
            left=inp_x,
            top=y,
            width=inp_w,
            height=24,
            value=value,
            min_value=min_val,
            max_value=max_val,
            step=step,
            position="absolute",
        )
        if unit:
            StyledLabel(
                container=root,
                text=unit,
                variable_name=f"{prefix}_unit",
                left=unit_x,
                top=y,
                width=unit_w,
                height=24,
                font_size=100,
                flex=True,
                justify_content="left",
                color="#222",
            )

    def _create_column3_detector_ports_config(self, root, col_x, y, col_width):
        """Create column 3 with Detector Window Settings following sub_data_window_setting_gui.py pattern exactly."""
        # Layout constants adjusted for wider column and better spacing
        LBL_X = col_x     # Move Range/Ref labels more to the left
        INP_X = col_x + 70   # Input boxes
        UNIT_X = col_x + 150 # Unit labels
        BTN_X = col_x + 180  # Buttons - more space between inputs and buttons
        ROW = 30  # Row spacing

        # Detector Window Settings Title
        StyledLabel(
            container=root,
            text="Detector Window Settings",
            variable_name="detector_title",
            left=col_x,
            top=y,
            width=col_width,
            height=24,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#111",
            bold=True,
        )
        y += 30

        # =============== Channel 1 ===============
        StyledLabel(
            container=root,
            text="Slot 1",
            variable_name="ch1_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        # CH1 Range
        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch1_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch1_range = StyledSpinBox(
            container=root,
            variable_name="ch1_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch1_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn1 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn1",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH1 Reference
        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch1_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch1_ref = StyledSpinBox(
            container=root,
            variable_name="ch1_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch1_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn1 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn1",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH1 Auto Range
        self.apply_auto_btn1 = StyledButton(
            container=root,
            text="Auto Range CH1",
            variable_name="apply_auto_btn1",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW + 5

        # =============== Channel 2 ===============
        StyledLabel(
            container=root,
            text="Slot 2",
            variable_name="ch2_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        # CH2 Range
        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch2_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch2_range = StyledSpinBox(
            container=root,
            variable_name="ch2_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch2_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn2 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn2",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH2 Reference
        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch2_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch2_ref = StyledSpinBox(
            container=root,
            variable_name="ch2_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch2_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn2 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn2",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH2 Auto Range
        self.apply_auto_btn2 = StyledButton(
            container=root,
            text="Auto Range CH2",
            variable_name="apply_auto_btn2",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW + 5

        # =============== Channel 3 ===============
        StyledLabel(
            container=root,
            text="Slot 3",
            variable_name="ch3_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        # CH3 Range
        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch3_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch3_range = StyledSpinBox(
            container=root,
            variable_name="ch3_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch3_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn3 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn3",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH3 Reference
        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch3_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch3_ref = StyledSpinBox(
            container=root,
            variable_name="ch3_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch3_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn3 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn3",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH3 Auto Range
        self.apply_auto_btn3 = StyledButton(
            container=root,
            text="Auto Range CH3",
            variable_name="apply_auto_btn3",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW + 5

        # =============== Channel 4 ===============
        StyledLabel(
            container=root,
            text="Slot 4",
            variable_name="ch4_label",
            left=LBL_X,
            top=y,
            width=100,
            height=25,
            font_size=110,
            flex=True,
            justify_content="left",
            color="#222",
            bold=True,
        )
        y += 25

        # CH4 Range
        StyledLabel(
            container=root,
            text="Range",
            variable_name="ch4_range_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch4_range = StyledSpinBox(
            container=root,
            variable_name="ch4_range_in",
            left=INP_X,
            top=y,
            value=-10,
            width=60,
            height=24,
            min_value=-70,
            max_value=10,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch4_range_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_range_btn4 = StyledButton(
            container=root,
            text="Apply Range",
            variable_name="apply_range_btn4",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH4 Reference
        StyledLabel(
            container=root,
            text="Ref",
            variable_name="ch4_ref_lb",
            left=LBL_X,
            top=y,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )
        self.ch4_ref = StyledSpinBox(
            container=root,
            variable_name="ch4_ref_in",
            left=INP_X,
            top=y,
            value=-30,
            width=60,
            height=24,
            min_value=-100,
            max_value=0,
            step=1,
            position="absolute",
        )
        StyledLabel(
            container=root,
            text="dBm",
            variable_name="ch4_ref_unit",
            left=UNIT_X,
            top=y,
            width=30,
            height=25,
            font_size=100,
            flex=True,
            justify_content="left",
            color="#222",
        )
        self.apply_ref_btn4 = StyledButton(
            container=root,
            text="Apply Ref",
            variable_name="apply_ref_btn4",
            left=BTN_X,
            top=y,
            height=24,
            width=80,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )
        y += ROW

        # CH4 Auto Range
        self.apply_auto_btn4 = StyledButton(
            container=root,
            text="Auto Range CH4",
            variable_name="apply_auto_btn4",
            left=BTN_X,
            top=y,
            width=80,
            height=24,
            font_size=85,
            normal_color="#007BFF",
            press_color="#0056B3",
        )

        # Wire up events exactly like sub_data_window_setting_gui.py
        self.apply_auto_btn1.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch1_autorange)
        )
        self.apply_auto_btn2.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch2_autorange)
        )
        self.apply_auto_btn3.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch3_autorange)
        )
        self.apply_auto_btn4.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch4_autorange)
        )

        self.apply_range_btn1.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch1_range)
        )
        self.apply_ref_btn1.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch1_ref)
        )

        self.apply_range_btn2.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch2_range)
        )
        self.apply_ref_btn2.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch2_ref)
        )

        self.apply_range_btn3.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch3_range)
        )
        self.apply_ref_btn3.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch3_ref)
        )

        self.apply_range_btn4.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch4_range)
        )
        self.apply_ref_btn4.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_apply_ch4_ref)
        )

    # ================= CH1 EVENT HANDLERS =================
    def onclick_apply_ch1_autorange(self):
        """Apply auto range for CH1."""
        update_detector_window_setting("DetectorRange_Ch1", {})
        payload = {"Auto": 1}
        update_detector_window_setting("DetectorAutoRange_Ch1", payload)

    def onclick_apply_ch1_range(self):
        """Apply manual range for CH1."""
        update_detector_window_setting("DetectorAutoRange_Ch1", {})
        range_val = float(self.ch1_range.get_value())
        payload = {"range_dbm": range_val}
        update_detector_window_setting("DetectorRange_Ch1", payload)

    def onclick_apply_ch1_ref(self):
        """Apply reference for CH1."""
        ref_val = float(self.ch1_ref.get_value())
        payload = {"ref_dbm": ref_val}
        update_detector_window_setting("DetectorReference_Ch1", payload)

    # ================= CH2 EVENT HANDLERS =================
    def onclick_apply_ch2_autorange(self):
        """Apply auto range for CH2."""
        update_detector_window_setting("DetectorRange_Ch2", {})
        payload = {"Auto": 1}
        update_detector_window_setting("DetectorAutoRange_Ch2", payload)

    def onclick_apply_ch2_range(self):
        """Apply manual range for CH2."""
        update_detector_window_setting("DetectorAutoRange_Ch2", {})
        range_val = float(self.ch2_range.get_value())
        payload = {"range_dbm": range_val}
        update_detector_window_setting("DetectorRange_Ch2", payload)

    def onclick_apply_ch2_ref(self):
        """Apply reference for CH2."""
        ref_val = float(self.ch2_ref.get_value())
        payload = {"ref_dbm": ref_val}
        update_detector_window_setting("DetectorReference_Ch2", payload)

    # ================= CH3 EVENT HANDLERS =================
    def onclick_apply_ch3_autorange(self):
        """Apply auto range for CH3."""
        update_detector_window_setting("DetectorRange_Ch3", {})
        payload = {"Auto": 1}
        update_detector_window_setting("DetectorAutoRange_Ch3", payload)

    def onclick_apply_ch3_range(self):
        """Apply manual range for CH3."""
        update_detector_window_setting("DetectorAutoRange_Ch3", {})
        range_val = float(self.ch3_range.get_value())
        payload = {"range_dbm": range_val}
        update_detector_window_setting("DetectorRange_Ch3", payload)

    def onclick_apply_ch3_ref(self):
        """Apply reference for CH3."""
        ref_val = float(self.ch3_ref.get_value())
        payload = {"ref_dbm": ref_val}
        update_detector_window_setting("DetectorReference_Ch3", payload)

    # ================= CH4 EVENT HANDLERS =================
    def onclick_apply_ch4_autorange(self):
        """Apply auto range for CH4."""
        update_detector_window_setting("DetectorRange_Ch4", {})
        payload = {"Auto": 1}
        update_detector_window_setting("DetectorAutoRange_Ch4", payload)

    def onclick_apply_ch4_range(self):
        """Apply manual range for CH4."""
        update_detector_window_setting("DetectorAutoRange_Ch4", {})
        range_val = float(self.ch4_range.get_value())
        payload = {"range_dbm": range_val}
        update_detector_window_setting("DetectorRange_Ch4", payload)

    def onclick_apply_ch4_ref(self):
        """Apply reference for CH4."""
        ref_val = float(self.ch4_ref.get_value())
        payload = {"ref_dbm": ref_val}
        update_detector_window_setting("DetectorReference_Ch4", payload)

    def _create_save_buttons(self, root):
        """Create save buttons at bottom."""
        y_buttons = 550  # Adjusted for 4 detector slots

        self.save_user_btn = StyledButton(
            container=root,
            text="Save User Defaults",
            variable_name="save_user_btn",
            left=320,  # Adjusted for wider container
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
            left=540,  # Adjusted for wider container
            top=y_buttons,
            width=160,
            height=35,
            normal_color="#007bff",
            press_color="#0056b3",
            font_size=100,
        )

        # Wire up events
        self.save_user_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_save_user))
        self.save_project_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_save_project)
        )

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
                print(
                    f"[Default_Settings] Saved project config for {self.current_user}/{self.current_project}"
                )
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
            
            # Signal other GUIs to reload config
            flag = File("shared_memory", "LoadConfig", True)
            flag.save()
            
            print(f"[Default_Settings] Updated shared_memory.json")
        except Exception as e:
            print(f"[Default_Settings] Error updating shared_memory.json: {e}")

    def _get_widget_value_by_name(self, widget_name, default_value):
        """Get widget value by name, return default if not found."""
        try:
            # For detector settings widgets created dynamically
            container = getattr(self, "_ui_container", None)
            if container and hasattr(container, "children") and widget_name in container.children:
                return float(container.children[widget_name].get_value())
            return default_value
        except Exception:
            return default_value

    def _build_config_from_ui(self):
        """
        Build configuration dictionary from UI widget values.
        """
        # --- derive Area Scan fields so they match area_scan.onclick_confirm ---
        try:
            # Pattern
            pattern_raw = str(self.area_pattern_dd.get_value()) if self.area_pattern_dd else "Spiral"
            pattern_raw = pattern_raw.strip().lower()
            spiral = (pattern_raw == "spiral")

            # Steps
            if spiral:
                # For spiral, x_step == y_step == step_size
                try:
                    step_val = float(self.area_spiral_step.get_value())
                except Exception:
                    step_val = 5.0
                area_x_step = step_val
                area_y_step = step_val
            else:
                try:
                    area_x_step = float(self.area_x_step.get_value())
                except Exception:
                    area_x_step = 5.0
                try:
                    area_y_step = float(self.area_y_step.get_value())
                except Exception:
                    area_y_step = 5.0

            area_pattern = "spiral" if spiral else "crosshair"

            # Primary detector (store as ch1/ch2/max)
            try:
                primary_raw = str(self.area_primary_detector_dd.get_value())
            except Exception:
                primary_raw = "MAX"
            primary_norm = primary_raw.strip().upper()
            if primary_norm not in ("CH1", "CH2", "MAX"):
                primary_norm = "MAX"
            primary_token = primary_norm.lower()  # ch1/ch2/max

            # Plot ("New"/"Previous")
            try:
                plot_raw = str(self.area_plot_dd.get_value())
            except Exception:
                plot_raw = "New"
            if plot_raw.lower() == "previous":
                plot_norm = "Previous"
            else:
                plot_norm = "New"

        except Exception:
            # Fallbacks if anything in the above blows up
            area_x_step = 5.0
            area_y_step = 5.0
            area_pattern = "spiral"
            primary_token = "max"
            plot_norm = "New"

        # Defaults aligned with _update_ui_from_config
        config = {
            "Sweep": {
                "power": self._safe_float(self.sweep_power, 0.0),
                "start": self._safe_float(self.sweep_start, 1540.0),
                "end": self._safe_float(self.sweep_end, 1580.0),
                "step": self._safe_float(self.sweep_step, 0.001),
            },
            "AreaS": {
                "x_size": self._safe_float(self.area_x_size, 50.0),
                "x_step": float(area_x_step),
                "y_size": self._safe_float(self.area_y_size, 50.0),
                "y_step": float(area_y_step),
                # pattern stored lowercase so area_scan can use it directly
                "pattern": area_pattern,
                "primary_detector": primary_token,   # ch1/ch2/max
                "plot": plot_norm,                   # "New" or "Previous"
            },
            "FineA": {
                "window_size": self._safe_float(self.fa_window_size, 10.0),
                "step_size": self._safe_float(self.fa_step_size, 1.0),
                "max_iters": self._safe_int(self.fa_max_iters, 10),
                "min_gradient_ss": self._safe_float(self.fa_min_grad_ss, 0.1),
                "detector": self._safe_str(self.fa_primary_detector, "Max"),
                "ref_wl": self._safe_float(self.fa_ref_wl, 1550.0),
            },
            "InitialPositions": {
                "fa": self._safe_float(self.init_fa, 8.0),
            },
            "DetectorWindowSettings": {
                # CH1
                "DetectorAutoRange_Ch1": {},
                "DetectorRange_Ch1": {
                    "range_dbm": self._safe_int(self.ch1_range, -10),
                },
                "DetectorReference_Ch1": {
                    "ref_dbm": self._safe_int(self.ch1_ref, -30),
                },

                # CH2
                "DetectorAutoRange_Ch2": {},
                "DetectorRange_Ch2": {
                    "range_dbm": self._safe_int(self.ch2_range, -10),
                },
                "DetectorReference_Ch2": {
                    "ref_dbm": self._safe_int(self.ch2_ref, -30),
                },

                # CH3
                "DetectorAutoRange_Ch3": {},
                "DetectorRange_Ch3": {
                    "range_dbm": self._safe_int(self.ch3_range, -10),
                },
                "DetectorReference_Ch3": {
                    "ref_dbm": self._safe_int(self.ch3_ref, -30),
                },

                # CH4
                "DetectorAutoRange_Ch4": {},
                "DetectorRange_Ch4": {
                    "range_dbm": self._safe_int(self.ch4_range, -10),
                },
                "DetectorReference_Ch4": {
                    "ref_dbm": self._safe_int(self.ch4_ref, -30),
                },
                "Detector_Change": "1",
            },
            "Port": {
                "stage": self._safe_int(self.stage_port, 4),
                "sensor": self._safe_int(self.sensor_port, 20),
            },
            "Configuration": {
                "stage": self._safe_str(self.stage_config_dd, ""),
                "sensor": self._safe_str(self.sensor_config_dd, ""),
            },
        }
        return config



# ---- REMI SERVER ----
def main():
    start(
        DefaultSettingsConfig,
        address="0.0.0.0",
        port=7009,
        start_browser=False,
        multiple_instance=False,
    )


if __name__ == "__main__":
    configuration = {
        "config_project_name": "default_settings",
        "config_address": "0.0.0.0",
        "config_port": 7009,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/",
    }
    start(
        DefaultSettingsConfig,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"],
    )
