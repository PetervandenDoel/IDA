from GUI.lib_gui import *
from remi import start, App
import datetime
import json
import os
import threading

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


def update_detector_window_setting(name, payload):
    try:
        with open(shared_path, "r", encoding="utf-8") as f:
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

    with open(shared_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class data_window(App):
    def __init__(self, *args, **kwargs):
        # Track modification times of command.json and shared_memory.json
        self._cmd_mtime = None
        self._shared_mtime = None
        self._first_command_check = True
        self._first_shared_check = True

        if "editing_mode" not in kwargs:
            super(data_window, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------
    @staticmethod
    def _set_spin_safely(widget, value):
        """Safely set a SpinBox value if value is not None."""
        if widget is None or value is None:
            return
        try:
            widget.set_value(float(value))
        except Exception:
            try:
                widget.set_value(value)
            except Exception:
                pass

    def idle(self):
        # ---------------- command.json watcher ----------------
        try:
            cmd_mtime = os.path.getmtime(command_path)
        except FileNotFoundError:
            cmd_mtime = None

        if self._first_command_check:
            self._cmd_mtime = cmd_mtime
            self._first_command_check = False
        elif cmd_mtime != self._cmd_mtime:
            self._cmd_mtime = cmd_mtime
            self.execute_command()

        # ---------------- shared_memory.json watcher ----------------
        try:
            shared_mtime = os.path.getmtime(shared_path)
        except FileNotFoundError:
            shared_mtime = None

        if self._first_shared_check:
            self._shared_mtime = shared_mtime
            self._first_shared_check = False
        elif shared_mtime != self._shared_mtime:
            self._shared_mtime = shared_mtime
            self._load_from_shared()

    def main(self):
        ui = self.construct_ui()
        # Load initial values from shared_memory.json (DetectorWindowSettings)
        self._load_from_shared()
        return ui

    def run_in_thread(self, target, *args):
        threading.Thread(target=target, args=args, daemon=True).start()

    # ------------------------------------------------------
    # Load from shared_memory.json → DetectorWindowSettings
    # ------------------------------------------------------
    def _load_from_shared(self):
        """
        Read DetectorWindowSettings from shared_memory.json and
        update the CH1–CH4 range/ref spin boxes.
        """
        try:
            with open(shared_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        dws = data.get("DetectorWindowSettings", {})
        if not isinstance(dws, dict):
            return

        # CH1
        ch1_range = dws.get("DetectorRange_Ch1", {})
        ch1_ref = dws.get("DetectorReference_Ch1", {})
        self._set_spin_safely(self.ch1_range, ch1_range.get("range_dbm"))
        self._set_spin_safely(self.ch1_ref, ch1_ref.get("ref_dbm"))

        # CH2
        ch2_range = dws.get("DetectorRange_Ch2", {})
        ch2_ref = dws.get("DetectorReference_Ch2", {})
        self._set_spin_safely(self.ch2_range, ch2_range.get("range_dbm"))
        self._set_spin_safely(self.ch2_ref, ch2_ref.get("ref_dbm"))

        # CH3
        ch3_range = dws.get("DetectorRange_Ch3", {})
        ch3_ref = dws.get("DetectorReference_Ch3", {})
        self._set_spin_safely(self.ch3_range, ch3_range.get("range_dbm"))
        self._set_spin_safely(self.ch3_ref, ch3_ref.get("ref_dbm"))

        # CH4
        ch4_range = dws.get("DetectorRange_Ch4", {})
        ch4_ref = dws.get("DetectorReference_Ch4", {})
        self._set_spin_safely(self.ch4_range, ch4_range.get("range_dbm"))
        self._set_spin_safely(self.ch4_ref, ch4_ref.get("ref_dbm"))

    # ------------------------------------------------------
    # UI construction
    # ------------------------------------------------------
    def construct_ui(self):
        data_window_container = StyledContainer(
            variable_name="data_window_container", left=0, top=0, height=520, width=280
        )

        # =============== Channel 1 ===============                                                                                 
        StyledLabel(
            container=data_window_container, text="Slot 1",
            variable_name="ch1_label", left=10, top=15,
            width=100, height=25, font_size=110, flex=True,
            justify_content="left", color="#222", bold=True
        )

        # Row spacing: 30 px
        StyledLabel(
            container=data_window_container, text="Range",
            variable_name="ch1_range_lb", left=10, top=50,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch1_range = StyledSpinBox(
            container=data_window_container, variable_name="ch1_range_in",
            left=80, top=50, value=-10, width=60, height=24,
            min_value=-70, max_value=10, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch1_range_unit", left=160, top=50,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        StyledLabel(
            container=data_window_container, text="Ref",
            variable_name="ch1_ref_lb", left=10, top=80,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch1_ref = StyledSpinBox(
            container=data_window_container, variable_name="ch1_ref_in",
            left=80, top=80, value=-30, width=60, height=24,
            min_value=-100, max_value=0, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch1_ref_unit", left=160, top=80,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        # Buttons shifted accordingly
        self.apply_range_btn = StyledButton(
            container=data_window_container, text="Apply Range",
            variable_name="apply_range_btn", left=190, top=50,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_ref_btn = StyledButton(
            container=data_window_container, text="Apply Ref",
            variable_name="apply_ref_btn", left=190, top=80,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_auto_btn1 = StyledButton(
            container=data_window_container, text="Auto Range CH1",
            variable_name="apply_auto_btn1", left=190, top=110,
            width=80, height=24, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        # =============== Channel 2 ===============
        StyledLabel(
            container=data_window_container, text="Slot 2",
            variable_name="ch2_label", left=10, top=140,
            width=100, height=25, font_size=110, flex=True,
            justify_content="left", color="#222", bold=True
        )

        StyledLabel(
            container=data_window_container, text="Range",
            variable_name="ch2_range_lb", left=10, top=170,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch2_range = StyledSpinBox(
            container=data_window_container, variable_name="ch2_range_in",
            left=80, top=170, value=-10, width=60, height=24,
            min_value=-70, max_value=10, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch2_range_unit", left=160, top=170,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        StyledLabel(
            container=data_window_container, text="Ref",
            variable_name="ch2_ref_lb", left=10, top=200,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch2_ref = StyledSpinBox(
            container=data_window_container, variable_name="ch2_ref_in",
            left=80, top=200, value=-30, width=60, height=24,
            min_value=-100, max_value=0, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch2_ref_unit", left=160, top=200,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        self.apply_range_btn2 = StyledButton(
            container=data_window_container, text="Apply Range",
            variable_name="apply_range_btn2", left=190, top=170,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_ref_btn2 = StyledButton(
            container=data_window_container, text="Apply Ref",
            variable_name="apply_ref_btn2", left=190, top=200,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_auto_btn2 = StyledButton(
            container=data_window_container, text="Auto Range CH2",
            variable_name="apply_auto_btn2", left=190, top=230,
            width=80, height=24, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        # =============== Channel 3 ===============
        StyledLabel(
            container=data_window_container, text="Slot 3",
            variable_name="ch3_label", left=10, top=265,
            width=100, height=25, font_size=110, flex=True,
            justify_content="left", color="#222", bold=True
        )

        StyledLabel(
            container=data_window_container, text="Range",
            variable_name="ch3_range_lb", left=10, top=295,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch3_range = StyledSpinBox(
            container=data_window_container, variable_name="ch3_range_in",
            left=80, top=295, value=-10, width=60, height=24,
            min_value=-70, max_value=10, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch3_range_unit", left=160, top=295,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        StyledLabel(
            container=data_window_container, text="Ref",
            variable_name="ch3_ref_lb", left=10, top=325,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch3_ref = StyledSpinBox(
            container=data_window_container, variable_name="ch3_ref_in",
            left=80, top=325, value=-30, width=60, height=24,
            min_value=-100, max_value=0, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch3_ref_unit", left=160, top=325,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        self.apply_range_btn3 = StyledButton(
            container=data_window_container, text="Apply Range",
            variable_name="apply_range_btn3", left=190, top=295,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_ref_btn3 = StyledButton(
            container=data_window_container, text="Apply Ref",
            variable_name="apply_ref_btn3", left=190, top=325,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_auto_btn3 = StyledButton(
            container=data_window_container, text="Auto Range CH3",
            variable_name="apply_auto_btn3", left=190, top=355,
            width=80, height=24, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        # =============== Channel 4 ===============
        StyledLabel(
            container=data_window_container, text="Slot 4",
            variable_name="ch4_label", left=10, top=390,
            width=100, height=25, font_size=110, flex=True,
            justify_content="left", color="#222", bold=True
        )

        StyledLabel(
            container=data_window_container, text="Range",
            variable_name="ch4_range_lb", left=10, top=420,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch4_range = StyledSpinBox(
            container=data_window_container, variable_name="ch4_range_in",
            left=80, top=420, value=-10, width=60, height=24,
            min_value=-70, max_value=10, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch4_range_unit", left=160, top=420,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        StyledLabel(
            container=data_window_container, text="Ref",
            variable_name="ch4_ref_lb", left=10, top=450,
            width=60, height=25, font_size=100, flex=True,
            justify_content="right", color="#222"
        )

        self.ch4_ref = StyledSpinBox(
            container=data_window_container, variable_name="ch4_ref_in",
            left=80, top=450, value=-30, width=60, height=24,
            min_value=-100, max_value=0, step=1, position="absolute"
        )

        StyledLabel(
            container=data_window_container, text="dBm",
            variable_name="ch4_ref_unit", left=160, top=450,
            width=30, height=25, font_size=100, flex=True,
            justify_content="left", color="#222"
        )

        self.apply_range_btn4 = StyledButton(
            container=data_window_container, text="Apply Range",
            variable_name="apply_range_btn4", left=190, top=420,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_ref_btn4 = StyledButton(
            container=data_window_container, text="Apply Ref",
            variable_name="apply_ref_btn4", left=190, top=450,
            height=24, width=80, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        self.apply_auto_btn4 = StyledButton(
            container=data_window_container, text="Auto Range CH4",
            variable_name="apply_auto_btn4", left=190, top=480,
            width=80, height=24, font_size=85,
            normal_color="#007BFF", press_color="#0056B3"
        )

        # Wire up events
        self.apply_auto_btn1.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch1_autorange))
        self.apply_auto_btn2.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch2_autorange))
        self.apply_auto_btn3.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch3_autorange))
        self.apply_auto_btn4.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch4_autorange))

        self.apply_range_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch1_range))
        self.apply_ref_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch1_ref))

        self.apply_range_btn2.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch2_range))
        self.apply_ref_btn2.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch2_ref))

        self.apply_range_btn3.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch3_range))
        self.apply_ref_btn3.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch3_ref))

        self.apply_range_btn4.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch4_range))
        self.apply_ref_btn4.do_onclick(lambda *_: self.run_in_thread(self.onclick_apply_ch4_ref))

        self.data_window_container = data_window_container
        return data_window_container

    # ================= CH1 =================
    def onclick_apply_ch1_autorange(self):
        # Clear manual range, set auto range
        update_detector_window_setting("DetectorRange_Ch1", {})
        payload = {
            "Auto": 1
        }
        update_detector_window_setting("DetectorAutoRange_Ch1", payload)

    def onclick_apply_ch1_range(self):
        # Clear auto range, set manual range
        update_detector_window_setting("DetectorAutoRange_Ch1", {})
        range_val = float(self.ch1_range.get_value())
        payload = {
            "range_dbm": range_val
        }
        update_detector_window_setting("DetectorRange_Ch1", payload)

    def onclick_apply_ch1_ref(self):
        ref_val = float(self.ch1_ref.get_value())
        payload = {
            "ref_dbm": ref_val
        }
        update_detector_window_setting("DetectorReference_Ch1", payload)

    # ================= CH2 =================
    def onclick_apply_ch2_autorange(self):
        update_detector_window_setting("DetectorRange_Ch2", {})
        payload = {
            "Auto": 1
        }
        update_detector_window_setting("DetectorAutoRange_Ch2", payload)

    def onclick_apply_ch2_range(self):
        update_detector_window_setting("DetectorAutoRange_Ch2", {})
        range_val = float(self.ch2_range.get_value())
        payload = {
            "range_dbm": range_val
        }
        update_detector_window_setting("DetectorRange_Ch2", payload)

    def onclick_apply_ch2_ref(self):
        ref_val = float(self.ch2_ref.get_value())
        payload = {
            "ref_dbm": ref_val
        }
        update_detector_window_setting("DetectorReference_Ch2", payload)

    # ================= CH3 =================
    def onclick_apply_ch3_autorange(self):
        update_detector_window_setting("DetectorRange_Ch3", {})
        payload = {
            "Auto": 1
        }
        update_detector_window_setting("DetectorAutoRange_Ch3", payload)

    def onclick_apply_ch3_range(self):
        update_detector_window_setting("DetectorAutoRange_Ch3", {})
        range_val = float(self.ch3_range.get_value())
        payload = {
            "range_dbm": range_val
        }
        update_detector_window_setting("DetectorRange_Ch3", payload)

    def onclick_apply_ch3_ref(self):
        ref_val = float(self.ch3_ref.get_value())
        payload = {
            "ref_dbm": ref_val
        }
        update_detector_window_setting("DetectorReference_Ch3", payload)

    # ================= CH4 =================
    def onclick_apply_ch4_autorange(self):
        update_detector_window_setting("DetectorRange_Ch4", {})
        payload = {
            "Auto": 1
        }
        update_detector_window_setting("DetectorAutoRange_Ch4", payload)

    def onclick_apply_ch4_range(self):
        update_detector_window_setting("DetectorAutoRange_Ch4", {})
        range_val = float(self.ch4_range.get_value())
        payload = {
            "range_dbm": range_val
        }
        update_detector_window_setting("DetectorRange_Ch4", payload)

    def onclick_apply_ch4_ref(self):
        ref_val = float(self.ch4_ref.get_value())
        payload = {
            "ref_dbm": ref_val
        }
        update_detector_window_setting("DetectorReference_Ch4", payload)

    def execute_command(self, path=command_path):
        dw = 0
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
            if key.startswith("data_window") and record == 0:
                dw = 1
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
            elif key.startswith("fa_set") or record == 1:
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

            elif key == "data_ch1_range":
                self.ch1_range.set_value(val)
            elif key == "data_ch1_ref":
                self.ch1_ref.set_value(val)
            elif key == "data_ch2_range":
                self.ch2_range.set_value(val)
            elif key == "data_ch2_ref":
                self.ch2_ref.set_value(val)
            elif key == "data_ch3_range":
                self.ch3_range.set_value(val)
            elif key == "data_ch3_ref":
                self.ch3_ref.set_value(val)
            elif key == "data_ch4_range":
                self.ch4_range.set_value(val)
            elif key == "data_ch4_ref":
                self.ch4_ref.set_value(val)

        if dw == 1:
            print("data window record")
            file = File("command", "command", new_command)
            file.save()


if __name__ == "__main__":
    configuration = {
        "config_project_name": "data_window",
        "config_address": "0.0.0.0",
        "config_port": 7006,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/"
    }
    start(
        data_window,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"]
    )
