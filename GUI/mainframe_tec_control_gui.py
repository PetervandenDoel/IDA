from GUI.lib_gui import *
from remi.gui import *
from remi import start, App
import threading, webview, signal, socket, os, json
from LDC.ldc_manager import LDCManager
from LDC.config.ldc_config import LDCConfiguration

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


class tec_control(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._user_stime = None
        self._first_command_check = True
        self.configuration = {}
        self.configuration_check = {}
        self.configuration_count = 0
        self.configure = None
        self.ldc_manager = None
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
        if self.configuration["tec"] != "" and self.configuration_count == 0 and self.configuration_check["tec"] == 0:
            self.configure = LDCConfiguration()
            self.configure.visa_address = str(self.port['tec'])
            self.configure.driver_types = str(self.configuration['tec'])
            self.ldc_manager = LDCManager(self.configure)
            success = self.ldc_manager.initialize()

            if success:
                self.configuration_count = 1
                self.configuration_check["tec"] = 2
                File("shared_memory", "Configuration_check", self.configuration_check).save()

                self.ldc_manager.set_temperature(25.0)

                self.tec_window = webview.create_window(
                    'TEC Control',
                    f'http://{local_ip}:8002',
                    width=322 + web_w,
                    height=280 + web_h,
                    x=800, y=100,
                    resizable=True,
                    hidden=False
                )
            else:
                self.configuration_count = 0
                self.configuration_check["tec"] = 1
                File("shared_memory", "Configuration_check", self.configuration_check).save()

        elif self.configuration["tec"] == "" and self.configuration_count == 1:
            self.configuration_count = 0
            if self.tec_window:
                self.tec_window.destroy()
                self.tec_window = None
                self.ldc_manager.shutdown()

    def construct_ui(self):
        sensor_control_container = StyledContainer(
            container=None,
            variable_name="sensor_control_container",
            left=0, top=0,
            height=260,
            width=300
        )

        self.on_box = StyledCheckBox(
            container=sensor_control_container,
            variable_name="on_box",
            left=20, top=10,
            width=10, height=10,
            position="absolute"
        )

        StyledLabel(
            container=sensor_control_container,
            text="On",
            variable_name="on_label",
            left=50, top=10,
            width=40, height=30,
            font_size=100,
            justify_content="left"
        )

        StyledLabel(
            container=sensor_control_container,
            text="Tem [C]",
            variable_name="wvl_label",
            left=0, top=55,
            width=80, height=25,
            font_size=100,
            justify_content="right"
        )

        self.minus_tem = StyledButton(
            container=sensor_control_container,
            text="⮜",
            variable_name="wvl_left_button",
            font_size=100,
            left=90, top=55,
            width=40, height=25
        )

        self.plus_tem = StyledButton(
            container=sensor_control_container,
            text="⮞",
            variable_name="wvl_right_button",
            font_size=100,
            left=222, top=55,
            width=40, height=25
        )

        self.tem = StyledSpinBox(
            container=sensor_control_container,
            variable_name="wvl_input",
            left=135, top=55,
            min_value=0,
            max_value=100,
            value=25,
            step=0.1,
            width=65,
            height=24
        )

        self.minus_tem.do_onclick(lambda *_: self.run_in_thread(self.onclick_minus_tem))
        self.plus_tem.do_onclick(lambda *_: self.run_in_thread(self.onclick_plus_tem))
        self.tem.onchange.do(lambda e, v: self.run_in_thread(self.onchange_tem, e, v))
        self.on_box.onchange.do(lambda e, v: self.run_in_thread(self.onchange_box, e, v))

        ld_sweep_container = StyledContainer(
            container=sensor_control_container,
            left=0, top=100,
            width=300, height=140,
            border=True
        )

        StyledLabel(
            container=ld_sweep_container,
            text="LD Current Sweep",
            left=5, top=5,
            width=150, height=25,
            font_size=100
        )

        self.ld_sweep_btn = StyledButton(
            container=ld_sweep_container,
            text="Sweep",
            left=215, top=5,
            width=70, height=25
        )

        StyledLabel(ld_sweep_container, "Start [mA]", left=5, top=45, width=85, height=25)
        self.ld_start = StyledSpinBox(
            ld_sweep_container,
            left=95, top=45,
            min_value=0.1, max_value=500,
            value=1.0, step=0.1,
            width=65, height=24
        )

        StyledLabel(ld_sweep_container, "End [mA]", left=165, top=45, width=70, height=25)
        self.ld_end = StyledSpinBox(
            ld_sweep_container,
            left=235, top=45,
            min_value=0.1, max_value=500,
            value=20.0, step=0.1,
            width=65, height=24
        )

        StyledLabel(ld_sweep_container, "Step [mA]", left=5, top=85, width=85, height=25)
        self.ld_step = StyledSpinBox(
            ld_sweep_container,
            left=95, top=85,
            min_value=0.01, max_value=50,
            value=0.5, step=0.01,
            width=65, height=24
        )

        StyledLabel(ld_sweep_container, "Dwell [ms]", left=165, top=85, width=85, height=25)
        self.ld_dwell = StyledSpinBox(
            ld_sweep_container,
            left=255, top=85,
            min_value=10, max_value=10000,
            value=100, step=10,
            width=55, height=24
        )

        self.ld_sweep_btn.do_onclick(
            lambda *_: self.run_in_thread(self.onclick_ld_sweep)
        )

        self.sensor_control_container = sensor_control_container
        return sensor_control_container

    def onclick_minus_tem(self):
        value = round(float(self.tem.get_value()), 1)
        value = max(0.0, min(100.0, value - 0.1))
        self.tem.set_value(value)
        self.ldc_manager.set_temperature(value)

    def onclick_plus_tem(self):
        value = round(float(self.tem.get_value()), 1)
        value = max(0.0, min(100.0, value + 0.1))
        self.tem.set_value(value)
        self.ldc_manager.set_temperature(value)

    def onchange_tem(self, emitter, value):
        self.ldc_manager.set_temperature(float(value))

    def onchange_box(self, emitter, value):
        if value:
            self.ldc_manager.tec_on()
        else:
            self.ldc_manager.tec_off()

    def onclick_ld_sweep(self):
        if not self.ldc_manager:
            return

        # Safety: require TEC ON
        if not self.on_box.get_value():
            print("LD sweep blocked: TEC is OFF")
            return

        self.ldc_manager.ld_current_sweep(
            start_ma=float(self.ld_start.get_value()),
            stop_ma=float(self.ld_end.get_value()),
            step_ma=float(self.ld_step.get_value()),
            dwell_ms=int(self.ld_dwell.get_value()),
            trigger_delay_ms=self.ld_sweep["trigger_delay"],
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
            self.on_box.set_value(1)
        if "tec_off" in command:
            self.on_box.set_value(0)
        if "tec_tem" in command:
            self.tem.set_value(command["tec_tem"])


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
        height=280,
        resizable=True,
        hidden=True
    )
    webview.start()
