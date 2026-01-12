import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from remi import start, App
import os, threading, webview
from GUI.lib_gui import *
from SMU.keithley2600_manager import Keithley2600Manager
from SMU.config.smu_config import SMUConfiguration
from motors.elec.BSC203_controller import BSC203Controller

shared_path = os.path.join("database", "shared_memory.json")

class elecprobe(App):
    # Class-level variables (shared across all instances)
    _smu_manager_instance = None
    _smu_initialized = False
    _bsc_controller_instance = None
    _bsc_initialized = False
    
    def __init__(self, *args, **kwargs):
        self._user_stime = None
        if "editing_mode" not in kwargs:
            super(elecprobe, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})
        
        # Initialize SMU Manager (only once for all instances)
        if not elecprobe._smu_initialized:
            self._init_smu()
            elecprobe._smu_initialized = True
        
        # Use the shared instance
        self.smu_manager = elecprobe._smu_manager_instance
        self.smu_connected = False
        
        # Initialize BSC203 Controller (only once for all instances)
        if not elecprobe._bsc_initialized:
            self._init_bsc()
            elecprobe._bsc_initialized = True
        
        # Use the shared BSC instance
        self.bsc_controller = elecprobe._bsc_controller_instance
        self.bsc_connected = False

    def idle(self):
        try:
            stime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            stime = None

        if stime != self._user_stime:
            self._user_stime = stime
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[Warn] read json failed: {e}")
        
        # Update SMU display if connected
        self._update_smu_display()
        
        # Update BSC203 positions if connected
        self._update_bsc_display()
    
    def _update_smu_display(self):
        """Update SMU measurement display"""
        if not self.smu_connected:
            return
        
        try:
            # Get measurements for all channels at once
            voltages = self.smu_manager.get_voltage()
            currents = self.smu_manager.get_current()
            resistances = self.smu_manager.get_resistance()
            
            if voltages and currents and resistances:
                # Update Channel A display
                if 'A' in voltages and 'A' in currents and 'A' in resistances:
                    self.chl_a_v.set_text(f"{voltages['A']:.4f}")
                    self.chl_a_i.set_text(f"{currents['A']*1e6:.4f}")  # Convert to µA
                    self.chl_a_o.set_text(f"{resistances['A']:.3e}")  # Scientific notation in Ω
                
                # Update Channel B display
                if 'B' in voltages and 'B' in currents and 'B' in resistances:
                    self.chl_b_v.set_text(f"{voltages['B']:.4f}")
                    self.chl_b_i.set_text(f"{currents['B']*1e6:.4f}")  # Convert to µA
                    self.chl_b_o.set_text(f"{resistances['B']:.3e}")  # Scientific notation in Ω
        except Exception as e:
            # Silently ignore errors to avoid spamming console during normal operation
            pass
    
    def _init_smu(self):
        """Initialize SMU Manager (singleton pattern)"""
        try:
            # Create SMU configuration with default address
            smu_config = SMUConfiguration(
                visa_address="GPIB0::26::INSTR",  # Default VISA address
                nplc=1.0,
                off_mode="NORMAL",
                debug=False
            )
            
            # Create SMU Manager instance and store in class variable
            elecprobe._smu_manager_instance = Keithley2600Manager(
                config=smu_config,
                use_shared_memory=False,
                debug=False
            )
            
            print("[SMU] SMU Manager created successfully")
            
        except Exception as e:
            print(f"[SMU] Initialization failed: {e}")
            elecprobe._smu_manager_instance = None
    
    def _init_bsc(self):
        """Initialize BSC203 Controller (singleton pattern)"""
        try:
            # Create BSC203 Controller instance and store in class variable
            elecprobe._bsc_controller_instance = BSC203Controller()
            print("[BSC203] Controller created successfully")
        except Exception as e:
            print(f"[BSC203] Initialization failed: {e}")
            elecprobe._bsc_controller_instance = None
    
    def connect_bsc(self):
        """Connect to BSC203 device"""
        if self.bsc_controller is None:
            print("[BSC203] Controller not initialized")
            return False
        
        try:
            print("[BSC203] Attempting to connect to device...")
            success = self.bsc_controller.connect()
            if success:
                self.bsc_connected = True
                print("[BSC203] ✓ BSC203 connected successfully")
                
                # Get device info
                try:
                    info = self.bsc_controller.get_device_info()
                    print(f"[BSC203] Device: {info['name']} (SN: {info['serial_number']})")
                except:
                    pass
                    
                # Set default safety limits (3mm = 3000um)
                try:
                    self.bsc_controller.set_limits('X', 0, 3)
                    self.bsc_controller.set_limits('Y', 0, 3)
                    self.bsc_controller.set_limits('Z', 0, 3)
                    print("[BSC203] Safety limits set (X/Y/Z: 0-3mm)")
                except Exception as e:
                    print(f"[BSC203] Warning: Could not set limits: {e}")
            else:
                self.bsc_connected = False
                print("[BSC203] ✗ BSC203 connection failed")
            return success
        except Exception as e:
            print(f"[BSC203] Connection error: {e}")
            self.bsc_connected = False
            return False
    
    def disconnect_bsc(self):
        """Disconnect from BSC203 device"""
        if self.bsc_controller and self.bsc_connected:
            try:
                self.bsc_controller.disconnect()
                self.bsc_connected = False
                print("[BSC203] BSC203 disconnected")
            except Exception as e:
                print(f"[BSC203] Disconnect error: {e}")
    
    def _update_bsc_display(self):
        """Update BSC203 position display"""
        if not self.bsc_connected:
            return
        
        try:
            positions = self.bsc_controller.get_all_positions()
            
            if positions:
                # Update X axis (convert mm to um)
                if 'X' in positions:
                    self.x_position_lb.set_text(f"{positions['X']*1000:.1f}")
                    limits = self.bsc_controller.get_limits('X')
                    self.x_limit_lb.set_text(f"lim: [0, {limits[1]*1000:.0f}]")
                
                # Update Y axis (convert mm to um)
                if 'Y' in positions:
                    self.y_position_lb.set_text(f"{positions['Y']*1000:.1f}")
                    limits = self.bsc_controller.get_limits('Y')
                    self.y_limit_lb.set_text(f"lim: [0, {limits[1]*1000:.0f}]")
                
                # Update Z axis (convert mm to um)
                if 'Z' in positions:
                    self.z_position_lb.set_text(f"{positions['Z']*1000:.1f}")
                    limits = self.bsc_controller.get_limits('Z')
                    self.z_limit_lb.set_text(f"lim: [0, {limits[1]*1000:.0f}]")
        except Exception as e:
            # Silently ignore errors
            pass
    
    def connect_smu(self):
        """Connect to SMU device"""
        if self.smu_manager is None:
            print("[SMU] Manager not initialized")
            return False
        
        try:
            print("[SMU] Attempting to connect to device...")
            print("[SMU] This may take a few seconds...")
            success = self.smu_manager.initialize()
            if success:
                self.smu_connected = True
                print("[SMU] ✓ SMU connected successfully")
                
                # Set default source mode to voltage for both channels
                try:
                    self.smu_manager.set_source_mode("voltage", "A")
                    self.smu_manager.set_source_mode("voltage", "B")
                    print("[SMU] Default source mode set to VOLTAGE for both channels")
                except Exception as e:
                    print(f"[SMU] Warning: Could not set default source mode: {e}")
            else:
                self.smu_connected = False
                print("[SMU] ✗ SMU connection failed")
                print("[SMU] Check:")
                print("  - Device is powered on")
                print("  - GPIB/USB cable is connected")
                print("  - GPIB address is correct (current: GPIB0::26::INSTR)")
                print("  - No other software is using the device")
            return success
        except Exception as e:
            print(f"[SMU] Connection error: {e}")
            self.smu_connected = False
            return False
    
    def disconnect_smu(self):
        """Disconnect from SMU device"""
        if self.smu_manager and self.smu_connected:
            try:
                self.smu_manager.disconnect()
                self.smu_connected = False
                print("[SMU] SMU disconnected")
            except Exception as e:
                print(f"[SMU] Disconnect error: {e}")

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def construct_ui(self):
        DELTA = 40
        LEFT_PANEL_W = 490  # wider left box so rows + Zero buttons fit cleanly
        LOCK_COL_LEFT = 18 + DELTA  # per-axis lock column (aligns with top lock icon)
        ICON_LEFT = 18  # big lock icon
        LABEL_LEFT = 38 + DELTA  # axis text column (left of readouts)
        POS_LEFT = 35 + DELTA  # position numeric readout
        UNIT_LEFT = 150 + DELTA  # unit next to readout
        BTN_L_LEFT = 185 + DELTA  # left jog button
        SPIN_LEFT = 245 + DELTA  # step spinbox
        BTN_R_LEFT = 345 + DELTA  # right jog button
        ROW_TOPS = [50, 85, 120, 155, 190]  # Adjusted for title bar
        ROW_H = 30

        elecprobe_container = StyledContainer(
            variable_name="instruments_container", left=0, top=0, height=590, width=1100, bg_color=True, color="#F5F5F5"
        )

        xyz_container = StyledContainer(
            container=elecprobe_container, variable_name="xyz_container", border=0,
            left=0, top=400, height=190, width=490
        )
        
        # BSC203 Title and Connect Button
        StyledLabel(
            container=xyz_container, text="BSC203 Stage Control", variable_name="bsc_title_lb",
            left=10, top=5, width=200, height=25, font_size=120, color="#222", position="absolute",
            flex=True, bold=True, justify_content="left"
        )
        
        self.bsc_connect_btn = StyledButton(
            container=xyz_container, variable_name="bsc_connect_btn", text="Connect",
            left=240, top=5, width=100, height=25, font_size=100,
            normal_color="#28a745", press_color="#1e7e34"
        )
        
        self.bsc_status_lb = StyledLabel(
            container=xyz_container, text="Not Connected", variable_name="bsc_status_lb",
            left=350, top=8, width=130, height=20, font_size=90, color="#dc3545", position="absolute",
            flex=True, justify_content="left"
        )

        smu_container = StyledContainer(
            container=elecprobe_container, variable_name="smu_container",
            left=500, top=0, height=590, width=600
        )

        smu_control_container = StyledContainer(
            container=smu_container, variable_name="smu_control_container", border=True,
            left=8, top=10, height=215, width=584
        )

        StyledLabel(
            container=smu_control_container, text="SMU Control", variable_name=f"smu_lb",
            left=30, top=-12, width=100, height=20, font_size=120, color="#222", position="absolute",
            flex=True, on_line=True
        )

        smu_sweep_container = StyledContainer(
            container=smu_container, variable_name="smu_sweep_container", border=True,
            left=8, top=250, height=200, width=584
        )

        StyledLabel(
            container=smu_sweep_container, text="Sweep Setting", variable_name=f"smu_lb",
            left=30, top=-12, width=112, height=20, font_size=120, color="#222", position="absolute",
            flex=True, on_line=True
        )

# Sweep Setting --------------------------------------------------------------------------------------------------------
        StyledLabel(
            container=smu_sweep_container, text="Independent Variable", variable_name=f"set_sweep_var_lb",
            left=5, top=10, width=150, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.set_sweep_var = StyledDropDown(
            container=smu_sweep_container, variable_name="set_sweep_var", text=["V", "I"],
            left=158, top=10, width=142, height=25
        )

        StyledLabel(
            container=smu_sweep_container, text="SMU Output", variable_name=f"set_sweep_output_lb",
            left=340, top=10, width=85, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.set_sweep_output = StyledDropDown(
            container=smu_sweep_container, variable_name="set_sweep_output", text=["A", "B"],
            left=432, top=10, width=142, height=25
        )

        sweep_params = [
            ("Set Sweep Min", "set_sweep_min", "V", 42),
            ("Set Sweep Max", "set_sweep_max", "V", 74),
            ("Set Sweep Resolution", "set_sweep_resolution", "mV", 106),
        ]

        for text, var_prefix, unit, top in sweep_params:
            StyledLabel(
                container=smu_sweep_container,
                text=text,
                variable_name=f"{var_prefix}_lb",
                left=5, top=top, width=160, height=25,
                font_size=110, color="#222", position="absolute",
                flex=True, justify_content="left"
            )

            setattr(self, f"{var_prefix}_sb", StyledSpinBox(
                container=smu_sweep_container,
                variable_name=f"{var_prefix}_sb",
                max_value=30, min_value=-30, value=0.0, step=0.1,
                left=180, top=top, width=180, height=24
            ))

            StyledLabel(
                container=smu_sweep_container,
                text=unit,
                variable_name=f"{var_prefix}_unit",
                left=400, top=top, width=30, height=25,
                font_size=110, color="#222", position="absolute",
                flex=True, justify_content="left"
            )

        StyledLabel(
            container=smu_sweep_container, text="Plot Type", variable_name="set_sweep_plot_lb",
            left=5, top=150, width=70, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.set_sweep_iv_box = StyledCheckBox(
            container=smu_sweep_container, variable_name="set_sweep_iv_box", left=140, top=148, width=12, height=12
        )

        StyledLabel(
            container=smu_sweep_container, text="IV/VI", variable_name="set_sweep_iv_lb",
            left=170, top=150, width=70, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.set_sweep_riv_box = StyledCheckBox(
            container=smu_sweep_container, variable_name="set_sweep_riv_box", left=290, top=148, width=12, height=12
        )

        StyledLabel(
            container=smu_sweep_container, text="RV/RI", variable_name="set_sweep_riv_lb",
            left=320, top=150, width=70, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.set_sweep_piv_box = StyledCheckBox(
            container=smu_sweep_container, variable_name="set_sweep_piv_box", left=440, top=148, width=12, height=12
        )

        StyledLabel(
            container=smu_sweep_container, text="PV/PI", variable_name="set_sweep_piv_lb",
            left=470, top=150, width=70, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.sweep_btn = StyledButton(
            container=smu_container, variable_name="sweep_btn", text="Sweep",
            left=245, top=500, width=100, height=40, font_size=120
        )

        # Display --------------------------------------------------------------------------------------------------------------
        StyledContainer(
            container=smu_control_container, variable_name="smu_line", left=310, top=10, width=0, height=195,
            border=True, line="1.5px dashed #ccc"
        )

        channel_headers = [
            ("A", 360),
            ("B", 470),
        ]

        for ch, left in channel_headers:
            StyledLabel(
                container=smu_control_container,
                text=f"Channel {ch}",
                variable_name=f"chl_{ch.lower()}_lb",
                left=left, top=25, width=110, height=25,
                font_size=110, color="#222", position="absolute",
                flex=True
            )

        metric_labels = [
            ("V (V)", "v", 57),
            ("I (µA)", "i", 97),
            ("R (Ω)", "o", 137),
        ]

        for text, suffix, top in metric_labels:
            StyledLabel(
                container=smu_control_container,
                text=text,
                variable_name=f"read_{suffix}_lb",
                left=320, top=top, width=50, height=25,
                font_size=110, color="#222", position="absolute",
                flex=True, justify_content="left"
            )

        for ch, left in channel_headers:
            ch_lower = ch.lower()
            for _, suffix, top in metric_labels:
                var_name = f"chl_{ch_lower}_{suffix}"
                setattr(self, var_name,
                        StyledLabel(
                            container=smu_control_container,
                            text="0.0",
                            variable_name=var_name,
                            left=left, top=top, width=110, height=25,
                            font_size=110, color="#222", position="absolute",
                            flex=True
                        ))

# Setting --------------------------------------------------------------------------------------------------------------
        StyledLabel(
            container=smu_control_container, text="SMU Output", variable_name=f"smu_output_lb",
            left=5, top=15, width=100, height=25, font_size=110, color="#222", position="absolute",
            flex=True, justify_content="left"
        )

        self.set_output = StyledDropDown(
            container=smu_control_container, variable_name="set_output", text=["A", "B", "All"],
            left=105, top=15, width=80, height=25
        )

        # Mode dropdown (V or I)
        self.set_mode = StyledDropDown(
            container=smu_control_container, variable_name="set_mode", text=["V", "I"],
            left=195, top=15, width=50, height=25
        )

        # Toggle button (starts as "On", toggles between "On" and "Off")
        self.set_output_toggle = StyledButton(
            container=smu_control_container, variable_name="set_output_toggle", text="On",
            left=250, top=15, width=50, height=25
        )
        self._output_state = False  # Track output state (False = Off, True = On)

        labels = [
            "Set Voltage (V)",
            "Set Current (µA)",
            "Set Voltage Lim (V)",
            "Set Current Lim (µA)",
            "Set Power Lim (mW)"
        ]
        names = ["voltage", "current", "v_limit", "i_limit", "p_limit"]

        base_top = 47
        spacing = 32

        for i, (label, name) in enumerate(zip(labels, names)):
            top_pos = base_top + i * spacing

            label_widget = StyledLabel(
                container=smu_control_container,
                text=label,
                variable_name=f"set_lb_{i}",
                left=5, top=top_pos, width=145, height=25,
                font_size=110, color="#222", position="absolute",
                flex=True, justify_content="left"
            )
            setattr(self, f"set_{name}_lb", label_widget)

            setattr(self, f"set_{name}_sb",
                StyledSpinBox(
                    container=smu_control_container,
                    variable_name=f"{name}_sb",
                    max_value=30, min_value=0, value=0.0, step=0.1,
                    left=158, top=top_pos, width=70, height=24
                )
            )

            setattr(self, f"set_{name}_bt",
                StyledButton(
                    container=smu_control_container,
                    variable_name=f"{name}_bt",
                    text="SET",
                    left=250, top=top_pos, width=50, height=25
                )
            )

# Movement Control -----------------------------------------------------------------------------------------------------
        labels = ["X", "Y", "Z"]
        left_arrows = ["⮜", "⮟", "Down"]
        right_arrows = ["⮞", "⮝", "Up"]
        var_prefixes = ["x", "y", "z"]
        position_texts = ["0.000", "0.000", "0.000"]
        position_unit = ["um", "um", "um"]
        init_value = ["100.0", "100.0", "50.0"]  # Default step in um

        for i in range(3):
            prefix = var_prefixes[i]
            top = ROW_TOPS[i]

            # per-axis lock checkbox (aligned with header icon)
            setattr(self, f"{prefix}_lock", StyledCheckBox(
                container=xyz_container, variable_name=f"{prefix}_lock",
                left=LOCK_COL_LEFT, top=top, width=12, height=12
            ))

            # axis label (left column)
            StyledLabel(
                container=xyz_container, text=labels[i], variable_name=f"{prefix}_label",
                left=LABEL_LEFT, top=top, width=55, height=ROW_H,
                font_size=100, color="#222", flex=True, bold=True, justify_content="center"
            )

            # position readout + unit (next column)
            setattr(self, f"{prefix}_position_lb", StyledLabel(
                container=xyz_container, text=position_texts[i], variable_name=f"{prefix}_position_lb",
                left=POS_LEFT + 50, top=top, width=70, height=ROW_H, font_size=100, color="#222",
                flex=True, bold=True, justify_content="left"
            ))
            setattr(self, f"{prefix}_limit_lb", StyledLabel(
                container=xyz_container, text="lim: N/A", variable_name=f"{prefix}_limit_lb",
                left=POS_LEFT, top=top + 22, width=100, height=20, font_size=70, color="#666",
                flex=True, justify_content="right"
            ))
            setattr(self, f"{prefix}_position_unit", StyledLabel(
                container=xyz_container, text=position_unit[i], variable_name=f"{prefix}_position_unit",
                left=UNIT_LEFT, top=top, width=40, height=ROW_H, font_size=100, color="#222",
                flex=True, bold=True, justify_content="left"
            ))

            # jog controls (shifted right)
            setattr(self, f"{prefix}_left_btn", StyledButton(
                container=xyz_container, text=left_arrows[i], variable_name=f"{prefix}_left_button", font_size=100,
                left=BTN_L_LEFT, top=top, width=50, height=ROW_H, normal_color="#007BFF", press_color="#0056B3"
            ))
            setattr(self, f"{prefix}_input", StyledSpinBox(
                container=xyz_container, variable_name=f"{prefix}_step", min_value=0, max_value=1000,
                value=init_value[i], step=0.1, left=SPIN_LEFT, top=top, width=73, height=ROW_H, position="absolute"
            ))
            setattr(self, f"{prefix}_right_btn", StyledButton(
                container=xyz_container, text=right_arrows[i], variable_name=f"{prefix}_right_button", font_size=100,
                left=BTN_R_LEFT, top=top, width=50, height=ROW_H, normal_color="#007BFF", press_color="#0056B3"
            ))

        # Initialize controls to voltage mode (default) without resetting params yet
        self._update_controls_for_mode("V", reset_params=False)
        
        # Bind SMU button events
        self.set_output_toggle.do_onclick(lambda *_: self.run_in_thread(self.onclick_output_toggle))
        self.set_mode.onchange.do(lambda widget, value: self.run_in_thread(self.on_mode_change, value))
        
        # Bind SET buttons for each parameter
        self.set_voltage_bt.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_voltage))
        self.set_current_bt.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_current))
        self.set_v_limit_bt.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_v_limit))
        self.set_i_limit_bt.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_i_limit))
        self.set_p_limit_bt.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_p_limit))
        
        # Bind BSC203 movement buttons
        self.bsc_connect_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_bsc_connect_toggle))
        self.x_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move_axis, 'X', 1))  # Reversed
        self.x_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move_axis, 'X', -1))  # Reversed
        self.y_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move_axis, 'Y', -1))
        self.y_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move_axis, 'Y', 1))
        self.z_left_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move_axis, 'Z', -1))
        self.z_right_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_move_axis, 'Z', 1))

        self.elecprobe_container = elecprobe_container
        return elecprobe_container
    
    # === SMU Control Event Handlers ===
    
    def _get_channels(self):
        """Get list of channels based on dropdown selection"""
        selection = self.set_output.get_value()
        if selection == "All":
            return ["A", "B"]
        else:
            return [selection]
    
    def _update_controls_for_mode(self, mode, reset_params=True):
        """Enable/disable controls based on source mode"""
        print(f"[DEBUG] _update_controls_for_mode called: mode={mode}, reset_params={reset_params}")
        
        if mode == "V":
            # Voltage mode: enable voltage controls, disable current controls
            self.set_voltage_lb.set_enabled(True)
            self.set_voltage_sb.set_enabled(True)
            self.set_voltage_bt.set_enabled(True)
            self.set_i_limit_lb.set_enabled(True)
            self.set_i_limit_sb.set_enabled(True)
            self.set_i_limit_bt.set_enabled(True)
            
            self.set_current_lb.set_enabled(False)
            self.set_current_sb.set_enabled(False)
            self.set_current_bt.set_enabled(False)
            self.set_v_limit_lb.set_enabled(False)
            self.set_v_limit_sb.set_enabled(False)
            self.set_v_limit_bt.set_enabled(False)
                    
        elif mode == "I":
            # Current mode: enable current controls, disable voltage controls
            self.set_current_lb.set_enabled(True)
            self.set_current_sb.set_enabled(True)
            self.set_current_bt.set_enabled(True)
            self.set_v_limit_lb.set_enabled(True)
            self.set_v_limit_sb.set_enabled(True)
            self.set_v_limit_bt.set_enabled(True)
            
            self.set_voltage_lb.set_enabled(False)
            self.set_voltage_sb.set_enabled(False)
            self.set_voltage_bt.set_enabled(False)
            self.set_i_limit_lb.set_enabled(False)
            self.set_i_limit_sb.set_enabled(False)
            self.set_i_limit_bt.set_enabled(False)
    
    def on_mode_change(self, new_mode):
        """Handle mode dropdown change - update UI controls only"""
        # Update UI controls based on mode (no parameter reset, no source mode change)
        self._update_controls_for_mode(new_mode, reset_params=False)
        
        print(f"[SMU] UI switched to {new_mode} mode")
    
    def onclick_output_toggle(self):
        """Toggle SMU output ON/OFF"""
        if not self.smu_connected:
            # Try to connect first
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot toggle output: Not connected")
                return
        
        try:
            channels = self._get_channels()
            mode = self.set_mode.get_value()  # Get selected mode (V or I)
            button_text = self.set_output_toggle.get_text()
            
            if button_text == "On":
                # Button shows "On", so turn output ON
                # First set the source mode based on dropdown selection
                for channel in channels:
                    if mode == "V":
                        self.smu_manager.set_source_mode("voltage", channel)
                    elif mode == "I":
                        self.smu_manager.set_source_mode("current", channel)
                
                # Update controls to match mode (don't reset params here, just enable/disable)
                self._update_controls_for_mode(mode, reset_params=False)
                
                for channel in channels:
                    success = self.smu_manager.output_on(channel)
                    if success:
                        print(f"[SMU] Channel {channel} output ON (mode: {mode})")
                    else:
                        print(f"[SMU] Failed to turn on channel {channel}")
                
                self._output_state = True
                self.set_output_toggle.set_text("Off")
            else:
                # Button shows "Off", so turn output OFF
                for channel in channels:
                    success = self.smu_manager.output_off(channel)
                    if success:
                        print(f"[SMU] Channel {channel} output OFF")
                    else:
                        print(f"[SMU] Failed to turn off channel {channel}")
                
                self._output_state = False
                self.set_output_toggle.set_text("On")
        except Exception as e:
            print(f"[SMU] Output toggle error: {e}")
    
    def onclick_output_on(self):
        """Turn on SMU output"""
        if not self.smu_connected:
            # Try to connect first
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot turn on output: Not connected")
                return
        
        try:
            channel = self.set_output.get_value()  # Get selected channel (A or B)
            success = self.smu_manager.output_on(channel)
            if success:
                print(f"[SMU] Channel {channel} output ON")
            else:
                print(f"[SMU] Failed to turn on channel {channel}")
        except Exception as e:
            print(f"[SMU] Output ON error: {e}")
    
    def onclick_output_off(self):
        """Turn off SMU output"""
        if not self.smu_connected:
            print("[SMU] Cannot turn off output: Not connected")
            return
        
        try:
            channel = self.set_output.get_value()  # Get selected channel (A or B)
            success = self.smu_manager.output_off(channel)
            if success:
                print(f"[SMU] Channel {channel} output OFF")
            else:
                print(f"[SMU] Failed to turn off channel {channel}")
        except Exception as e:
            print(f"[SMU] Output OFF error: {e}")
    
    def onclick_set_voltage(self):
        """Set voltage for selected channel"""
        if not self.smu_connected:
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot set voltage: Not connected")
                return
        
        try:
            channels = self._get_channels()
            voltage = float(self.set_voltage_sb.get_value())
            for channel in channels:
                # Set source mode to voltage before setting voltage
                self.smu_manager.set_source_mode("voltage", channel)
                success = self.smu_manager.set_voltage(voltage, channel)
                if success:
                    print(f"[SMU] Channel {channel} voltage set to {voltage} V")
                else:
                    print(f"[SMU] Failed to set voltage for channel {channel}")
        except Exception as e:
            print(f"[SMU] Set voltage error: {e}")
    
    def onclick_set_current(self):
        """Set current for selected channel"""
        if not self.smu_connected:
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot set current: Not connected")
                return
        
        try:
            channels = self._get_channels()
            current = float(self.set_current_sb.get_value()) / 1e6  # Convert µA to A
            for channel in channels:
                # Set source mode to current before setting current
                self.smu_manager.set_source_mode("current", channel)
                success = self.smu_manager.set_current(current, channel)
                if success:
                    print(f"[SMU] Channel {channel} current set to {current*1e6} µA")
                else:
                    print(f"[SMU] Failed to set current for channel {channel}")
        except Exception as e:
            print(f"[SMU] Set current error: {e}")
    
    def onclick_set_v_limit(self):
        """Set voltage limit for selected channel"""
        if not self.smu_connected:
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot set voltage limit: Not connected")
                return
        
        try:
            channels = self._get_channels()
            v_limit = float(self.set_v_limit_sb.get_value())
            for channel in channels:
                success = self.smu_manager.set_voltage_limit(v_limit, channel)
                if success:
                    print(f"[SMU] Channel {channel} voltage limit set to {v_limit} V")
                else:
                    print(f"[SMU] Failed to set voltage limit for channel {channel}")
        except Exception as e:
            print(f"[SMU] Set voltage limit error: {e}")
    
    def onclick_set_i_limit(self):
        """Set current limit for selected channel"""
        if not self.smu_connected:
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot set current limit: Not connected")
                return
        
        try:
            channels = self._get_channels()
            i_limit = float(self.set_i_limit_sb.get_value()) / 1e6  # Convert µA to A
            for channel in channels:
                success = self.smu_manager.set_current_limit(i_limit, channel)
                if success:
                    print(f"[SMU] Channel {channel} current limit set to {i_limit*1e6} µA")
                else:
                    print(f"[SMU] Failed to set current limit for channel {channel}")
        except Exception as e:
            print(f"[SMU] Set current limit error: {e}")
    
    def onclick_set_p_limit(self):
        """Set power limit for selected channel"""
        if not self.smu_connected:
            success = self.connect_smu()
            if not success:
                print("[SMU] Cannot set power limit: Not connected")
                return
        
        try:
            channels = self._get_channels()
            p_limit = float(self.set_p_limit_sb.get_value()) / 1000  # Convert mW to W
            for channel in channels:
                success = self.smu_manager.set_power_limit(p_limit, channel)
                if success:
                    print(f"[SMU] Channel {channel} power limit set to {p_limit*1000} mW")
                else:
                    print(f"[SMU] Failed to set power limit for channel {channel}")
        except Exception as e:
            print(f"[SMU] Set power limit error: {e}")
    
    # === BSC203 Movement Event Handlers ===
    
    def onclick_bsc_connect_toggle(self):
        """Toggle BSC203 connection"""
        if self.bsc_connected:
            # Disconnect
            self.disconnect_bsc()
            self.bsc_connect_btn.set_text("Connect")
            self.bsc_connect_btn.normal_color = '#28a745'
            self.bsc_connect_btn.press_color = '#1e7e34'
            self.bsc_connect_btn.style['background-color'] = '#28a745'
            self.bsc_status_lb.set_text("Not Connected")
            self.bsc_status_lb.style['color'] = '#dc3545'
        else:
            # Connect
            success = self.connect_bsc()
            if success:
                self.bsc_connect_btn.set_text("Disconnect")
                self.bsc_connect_btn.normal_color = '#dc3545'
                self.bsc_connect_btn.press_color = '#bd2130'
                self.bsc_connect_btn.style['background-color'] = '#dc3545'
                self.bsc_status_lb.set_text("Connected")
                self.bsc_status_lb.style['color'] = '#28a745'
            else:
                self.bsc_status_lb.set_text("Connection Failed")
                self.bsc_status_lb.style['color'] = '#dc3545'
    
    def onclick_move_axis(self, axis: str, direction: int):
        """Handle axis movement button click
        
        Args:
            axis: Axis name ('X', 'Y', 'Z')
            direction: -1 for left/down, 1 for right/up
        """
        if not self.bsc_connected:
            print(f"[BSC203] Cannot move {axis}: Not connected")
            return
        
        # Check if axis is locked
        axis_lower = axis.lower()
        lock_widget = getattr(self, f"{axis_lower}_lock", None)
        if lock_widget and lock_widget.get_value():
            print(f"[BSC203] Cannot move {axis}: Axis is locked")
            return
        
        # Get step size from spinbox (in um, convert to mm)
        step_widget = getattr(self, f"{axis_lower}_input", None)
        if not step_widget:
            print(f"[BSC203] Cannot get step size for {axis}")
            return
        
        step_um = float(step_widget.get_value())
        step_mm = step_um / 1000.0  # Convert um to mm
        distance = step_mm * direction
        
        try:
            print(f"[BSC203] Moving {axis} by {step_um * direction:.1f} um...")
            success = self.bsc_controller.move_relative(axis, distance, wait=True)
            
            if success:
                # Update position display immediately
                pos = self.bsc_controller.get_position(axis)
                print(f"[BSC203] {axis} moved to {pos*1000:.1f} um")
            else:
                print(f"[BSC203] Failed to move {axis}")
                
        except Exception as e:
            print(f"[BSC203] Error moving {axis}: {e}")

def run_remi():
    start(
        elecprobe,
        address="0.0.0.0",
        port=8011,
        start_browser=False,
        multiple_instance=False,
        enable_file_cache=False,
    )

def get_local_ip():
    """Automatically detect local LAN IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Fake connect to get route IP
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"  # fallback

if __name__ == "__main__":
    threading.Thread(target=run_remi, daemon=True).start()
    #local_ip = get_local_ip()
    local_ip = "127.0.0.1"
    webview.create_window(
        "Main Window",
        f"http://{local_ip}:8011",
        width=1022+100,
        height=756-110,
        resizable=True,
        hidden=False,
    )
    webview.start()