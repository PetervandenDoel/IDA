from GUI.lib_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal, socket, os, json
from LDC.ldc_manager import LDCManager
from LDC.config.ldc_config import LDCConfiguration

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


class tec_control(App):
    # Class-level shared state
    _ldc_manager = None
    _manager_lock = threading.Lock()
    
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
        self.configuration = {}
        self.configuration_check = {}
        self.configuration_count = 0
        self.configure = None
        self.tec_window = None
        self.port = {}

        self.ld_sweep = {
            "start": 1.0,
            "end": 20.0,
            "step": 0.5,
            "dwell": 100,
            "trigger_delay": 10,
        }

        if "editing_mode" not in kwargs:
            super(tec_control, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    @property
    def ldc_manager(self):
        """Shared LDC manager across all instances"""
        return tec_control._ldc_manager
    
    @ldc_manager.setter
    def ldc_manager(self, value):
        tec_control._ldc_manager = value

    def idle(self):
        try:
            mtime = os.path.getmtime(command_path)
            stime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            mtime = None
            stime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.execute_command()

        if stime != self._user_stime:
            self._user_stime = stime
            try:
                with open(shared_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.configuration = data.get("Configuration", {})
                    self.configuration_check = data.get("Configuration_check", {})
                    self.port = data.get("Port", {})
            except Exception as e:
                print(f"[Warn] read json failed: {e}")

        self.after_configuration()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args) -> None:
        threading.Thread(target=target, args=args, daemon=True).start()

    def after_configuration(self):
        try:
            # Safety checks using .get()
            tec_config = self.configuration.get("tec", "")
            tec_check = self.configuration_check.get("tec", -1)
            tec_port = self.port.get("tec")
            
            with tec_control._manager_lock:
                if tec_config != "" and tec_control._ldc_manager is None and tec_check == 0:
                    self.configure = LDCConfiguration()
                    self.configure.visa_address = str(tec_port)
                    self.configure.driver_types = str(tec_config)
                    
                    manager = LDCManager(self.configure)
                    success = manager.initialize()

                    if success:
                        tec_control._ldc_manager = manager
                        self.configuration_check["tec"] = 2
                        File("shared_memory", "Configuration_check", self.configuration_check).save()
                        tec_control._ldc_manager.set_temperature(25.0)
                    else:
                        self.configuration_check["tec"] = 1
                        File("shared_memory", "Configuration_check", self.configuration_check).save()

                elif tec_config == "" and tec_control._ldc_manager is not None:
                    if tec_control._ldc_manager:
                        tec_control._ldc_manager.shutdown()
                        tec_control._ldc_manager = None
        except Exception as e:
            print(f"Nice exception: {e}")
        
    def construct_ui(self):
        try: 
            main_container = StyledContainer(
                container=None,
                variable_name="main_container",
                left=0, top=0,
                height=520,
                width=300
            )

            # === TEC Control Section ===
            tec_container = StyledContainer(
                container=main_container,
                variable_name="tec_container",
                left=0, top=0,
                height=100,
                width=300
            )

            self.tec_on_box = StyledCheckBox(
                container=tec_container,
                variable_name="tec_on_box",
                left=20, top=10,
                width=10, height=10,
                position="absolute"
            )

            StyledLabel(
                container=tec_container,
                text="TEC On",
                variable_name="tec_on_label",
                left=50, top=10,
                width=60, height=30,
                font_size=100,
                justify_content="left"
            )

            StyledLabel(
                container=tec_container,
                text="Temp [C]",
                variable_name="temp_label",
                left=0, top=55,
                width=80, height=25,
                font_size=100,
                justify_content="right"
            )

            self.minus_temp = StyledButton(
                container=tec_container,
                text="⮜",
                variable_name="temp_left_button",
                font_size=100,
                left=90, top=55,
                width=40, height=25
            )

            self.plus_temp = StyledButton(
                container=tec_container,
                text="⮞",
                variable_name="temp_right_button",
                font_size=100,
                left=212, top=55,
                width=40, height=25
            )

            self.temp_spinbox = StyledSpinBox(
                container=tec_container,
                variable_name="temp_input",
                left=135, top=55,
                min_value=15,
                max_value=75,
                value=25,
                step=0.1,
                width=57,
                height=24
            )

            # === LD Control Section ===
            ld_container = StyledContainer(
                container=main_container,
                variable_name="ld_container",
                left=0, top=110,
                height=160,
                width=300,
                border=True
            )

            StyledLabel(
                container=ld_container,
                text="LD Control",
                variable_name="ld_control_container",
                left=5, top=5,
                width=100, height=25,
                font_size=100
            )

            self.ld_on_box = StyledCheckBox(
                container=ld_container,
                variable_name="ld_on_box",
                left=20, top=25,
                width=10, height=10,
                position="absolute"
            )

            StyledLabel(
                container=ld_container,
                text="LD On",
                variable_name="ld_on_label",
                left=50, top=25,
                width=60, height=30,
                font_size=100,
                justify_content="left"
            )

            StyledLabel(
                container=ld_container,
                text="Current [mA]",
                variable_name="current_label",
                left=5, top=60,
                width=90, height=25,
                font_size=90
            )

            self.ld_current = StyledSpinBox(
                container=ld_container,
                variable_name="ld_current_input",
                left=100, top=60,
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=0.1,
                width=65,
                height=24
            )

            self.set_current_btn = StyledButton(
                container=ld_container,
                variable_name="set_current_btn",
                text="Set",
                left=185, top=60,
                width=50, height=25,
                font_size=90
            )

            StyledLabel(
                container=ld_container,
                text="I Limit [mA]",
                variable_name="current_lim_label",
                left=5, top=90,
                width=90, height=25,
                font_size=90
            )

            self.i_limit = StyledSpinBox(
                container=ld_container,
                variable_name="i_limit_input",
                left=100, top=90,
                min_value=0.1,
                max_value=500.0,
                value=100.0,
                step=1.0,
                width=65,
                height=24
            )

            self.set_i_limit_btn = StyledButton(
                container=ld_container,
                text="Set",
                variable_name="set_i_limit_btn",
                left=185, top=90,
                width=50, height=25,
                font_size=90
            )

            StyledLabel(
                container=ld_container,
                text="V Limit [V]",
                variable_name="voltage_lim_label",
                left=5, top=120,
                width=90, height=25,
                font_size=90
            )

            self.v_limit = StyledSpinBox(
                container=ld_container,
                variable_name="v_limit_input",
                left=100, top=120,
                min_value=0.1,
                max_value=10.0,
                value=2.5,
                step=0.1,
                width=65,
                height=24
            )

            self.set_v_limit_btn = StyledButton(
                container=ld_container,
                text="Set",
                variable_name="set_v_limit_btn",
                left=185, top=120,
                width=50, height=25,
                font_size=90
            )
            # === LD Current Sweep Section ===
            ld_sweep_container = StyledContainer(
                container=main_container,
                variable_name="ld_sweep_container",
                left=0, top=280,
                width=300, height=230,
                border=True
            )

            StyledLabel(
                container=ld_sweep_container,
                text="LD Current Sweep",
                variable_name="current_sweep_label",
                left=5, top=5,
                width=150, height=25,
                font_size=100
            )

            self.ld_sweep_btn = StyledButton(
                container=ld_sweep_container,
                text="Sweep",
                variable_name="ld_sweep_btn",
                left=215, top=5,
                width=70, height=25
            )

            StyledLabel(
                container=ld_sweep_container,
                text="Start [mA]",
                variable_name="start_sweep_label",
                left=5, top=45, width=85, height=25)
            
            self.ld_start = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_start",
                left=70, top=45,
                min_value=0.1, max_value=500,
                value=1.0, step=0.1,
                width=65, height=24
            )

            StyledLabel(
                container=ld_sweep_container,
                text="End [mA]",
                variable_name="end_sweep_label",
                left=155, top=45, width=70, height=25)
            self.ld_end = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_end",
                left=215, top=45,
                min_value=0.1, max_value=500,
                value=20.0, step=0.1,
                width=60, height=24
            )

            StyledLabel(
                container=ld_sweep_container,
                text="Step [mA]",
                variable_name="sweep_step_label",
                left=5, top=85, width=85, height=25)
            self.ld_step = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_step",
                left=70, top=85,
                min_value=0.01, max_value=50,
                value=0.5, step=0.01,
                width=65, height=24
            )

            StyledLabel(
                container=ld_sweep_container,
                text="Dwell [ms]", 
                variable_name="sweep_dwell_label",
                left=155, top=85, width=85, height=25)
            
            self.ld_dwell = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_dwell",
                left=220, top=85,
                min_value=10, max_value=10000,
                value=100, step=10,
                width=55, height=24
            )

            StyledLabel(
                container=ld_sweep_container,
                text="Trig Delay [ms]",
                variable_name="sweep_trig_label",
                left=5, top=125, width=110, height=25, font_size=85)
            
            self.ld_trig_delay = StyledSpinBox(
                container=ld_sweep_container,
                variable_name="ld_trig_delay",
                left=90, top=125,
                min_value=0, max_value=1000,
                value=10, step=1,
                width=55, height=24
            )

            self.ld_range_high = StyledCheckBox(
                container=ld_sweep_container,
                variable_name="ld_range_box",
                left=20, top=165,
                width=10, height=10,
                position="absolute"
            )

            StyledLabel(
                container=ld_sweep_container,
                text="High Range (>100mA)",
                variable_name="sweep_safety_label",
                left=50, top=165,
                width=180, height=25,
                font_size=90,
                justify_content="left"
            )

            # Wire up event handlers
            self.minus_temp.do_onclick(lambda *_: self.run_in_thread(self.onclick_minus_temp))
            self.plus_temp.do_onclick(lambda *_: self.run_in_thread(self.onclick_plus_temp))
            self.temp_spinbox.onchange.do(lambda e, v: self.run_in_thread(self.onchange_temp, e, v))
            self.tec_on_box.onchange.do(lambda e, v: self.run_in_thread(self.onchange_tec_box, e, v))
            
            self.ld_on_box.onchange.do(lambda e, v: self.run_in_thread(self.onchange_ld_box, e, v))
            self.set_current_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_current))
            self.set_i_limit_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_i_limit))
            self.set_v_limit_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_set_v_limit))
            
            self.ld_sweep_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_ld_sweep))
            self.ld_range_high.onchange.do(lambda e, v: self.run_in_thread(self.onchange_range, e, v))

            return main_container
        except Exception as e:
            print(f"Fine as well: {e}")
            import sys
            print(f"line: {sys.exc_info()[-1].tb_lineno}")    


    # === TEC Handlers ===
    
    def onclick_minus_temp(self):
        if not self.ldc_manager:
            return
        value = round(float(self.temp_spinbox.get_value()), 1)
        value = max(15.0, min(75.0, value - 0.1))
        self.temp_spinbox.set_value(value)
        self.ldc_manager.set_temperature(value)

    def onclick_plus_temp(self):
        if not self.ldc_manager:
            return
        value = round(float(self.temp_spinbox.get_value()), 1)
        value = max(15.0, min(75.0, value + 0.1))
        self.temp_spinbox.set_value(value)
        self.ldc_manager.set_temperature(value)

    def onchange_temp(self, emitter, value):
        if not self.ldc_manager:
            return
        self.ldc_manager.set_temperature(float(value))

    def onchange_tec_box(self, emitter, value):
        if not self.ldc_manager:
            return
        if value:
            self.ldc_manager.tec_on()
        else:
            self.ldc_manager.tec_off()

    # === LD Handlers ===
    
    def onchange_ld_box(self, emitter, value):
        if not self.ldc_manager:
            return
        
        # Safety: require TEC ON before enabling LD
        if value and not self.tec_on_box.get_value():
            print("LD enable blocked: TEC must be ON first")
            self.ld_on_box.set_value(False)
            return
        
        if value:
            self.ldc_manager.ldc_on()
        else:
            self.ldc_manager.ldc_off()

    def onclick_set_current(self):
        if not self.ldc_manager:
            return
        current = float(self.ld_current.get_value())
        self.ldc_manager.set_current(current)
        print(f"LD current set to {current} mA")

    def onclick_set_i_limit(self):
        if not self.ldc_manager:
            return
        limit = float(self.i_limit.get_value())
        self.ldc_manager.set_current_limit(limit)
        print(f"LD current limit set to {limit} mA")

    def onclick_set_v_limit(self):
        if not self.ldc_manager:
            return
        limit = float(self.v_limit.get_value())
        self.ldc_manager.set_voltage_limit(limit)
        print(f"LD voltage limit set to {limit} V")

    def onchange_range(self, emitter, value):
        if not self.ldc_manager:
            return
        self.ldc_manager.set_current_range(high=bool(value))
        print(f"LD range set to {'HIGH' if value else 'LOW'}")

    def onclick_ld_sweep(self):
        if not self.ldc_manager:
            return

        # Safety: require TEC ON
        if not self.tec_on_box.get_value():
            print("LD sweep blocked: TEC is OFF")
            return

        start_ma = float(self.ld_start.get_value())
        stop_ma = float(self.ld_end.get_value())
        step_ma = float(self.ld_step.get_value())
        dwell_ms = int(self.ld_dwell.get_value())
        trig_delay_ms = int(self.ld_trig_delay.get_value())

        print(f"Starting LD sweep: {start_ma}->{stop_ma} mA, step={step_ma}, dwell={dwell_ms}ms")
        
        self.ldc_manager.ld_current_sweep(
            start_ma=start_ma,
            stop_ma=stop_ma,
            step_ma=step_ma,
            dwell_ms=dwell_ms,
            trigger_delay_ms=trig_delay_ms,
        )

        print("LD sweep complete")

    def execute_command(self, path=command_path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                command = data.get("command", {})
        except Exception:
            return

        if "tec_on" in command:
            self.tec_on_box.set_value(1)
        if "tec_off" in command:
            self.tec_on_box.set_value(0)
        if "tec_temp" in command:
            self.temp_spinbox.set_value(command["tec_temp"])


def run_remi():
    start(
        tec_control,
        address="0.0.0.0",
        port=8002,
        start_browser=False,
        multiple_instance=False
    )


if __name__ == '__main__':
    threading.Thread(target=run_remi, daemon=True).start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    local_ip = '127.0.0.1'
    webview.create_window(
        'TEC Control',
        f'http://{local_ip}:8002',
        width=322,
        height=540,
        resizable=True,
        hidden=True
    )
    webview.start()