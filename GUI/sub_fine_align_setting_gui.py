from GUI.lib_gui import *
from remi import start, App

command_path = os.path.join("database", "command.json")


class fine_align(App):
    def __init__(self, *args, **kwargs):
        self._user_mtime = None
        self._first_command_check = True
        if "editing_mode" not in kwargs:
            super(fine_align, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    def idle(self):
        try:
            mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            mtime = None

        if self._first_command_check:
            self._user_mtime = mtime
            self._first_command_check = False
            return

        if mtime != self._user_mtime:
            self._user_mtime = mtime
            self.execute_command()

    def main(self):
        return self.construct_ui()

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    def construct_ui(self):
        fine_align_setting_container = StyledContainer(
            variable_name="fine_align_setting_container",
            left=0,
            top=0,
            height=242,   # 210 + 32 to account for shifted Confirm + new ref_wl row
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
            container=fine_align_setting_container, text="",  # iterations have no 'um'
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

        self.detector = StyledDropDown(
            container=fine_align_setting_container,
            variable_name="detector",
            text=["ch1", "ch2", "Max"],
            left=80, top=138,
            width=60, height=25,
            position="absolute"
        )

        # ----- Ref WL (inserted between Detector and Confirm) -----
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

        # ----- Confirm button (shifted down by one row) -----
        self.confirm_btn = StyledButton(
            container=fine_align_setting_container, text="Confirm",
            variable_name="confirm_btn",
            left=68, top=202,   # was 174, now 174 + 32
            height=25, width=70,
            font_size=90
        )

        self.confirm_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_confirm))

        self.fine_align_setting_container = fine_align_setting_container
        return fine_align_setting_container

    def onclick_confirm(self):
        value = {
            "window_size": float(self.window_size.get_value()),
            "step_size": float(self.step_size.get_value()),
            "max_iters": int(self.max_iters.get_value()),
            "min_gradient_ss": float(self.min_grad_ss.get_value()),
            "detector": str(self.detector.get_value()),
            "ref_wl": float(self.ref_wl.get_value())
        }
        file = File("shared_memory", "FineA", value)
        file.save()
        print("Confirm Fine Align Setting")
        import webview
        # Set to a hidden window
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
