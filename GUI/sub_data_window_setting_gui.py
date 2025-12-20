from GUI.lib_gui import *
from remi import start, App
import datetime
import json
import os
import threading

command_path = os.path.join("database", "command.json")
shared_path = os.path.join("database", "shared_memory.json")


def update_detector_window_setting(mf, slot, setting_type, value):
    """Update detector window settings in compact structure.
    
    Args:
        mf: mainframe number (0 or 1)
        slot: slot number (1-4)
        setting_type: 'range', 'ref', or 'auto_range'
        value: setting value
    """
    try:
        with open(shared_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    # Initialize DetectorWindowSettings if needed
    if "DetectorWindowSettings" not in data:
        data["DetectorWindowSettings"] = {}
    
    dws = data["DetectorWindowSettings"]
    
    # Initialize MF section if needed
    mf_key = f"mf{mf}"
    if mf_key not in dws:
        dws[mf_key] = {}
    
    # Initialize slot settings if needed
    slot_str = str(slot)
    if slot_str not in dws[mf_key]:
        dws[mf_key][slot_str] = {}
    
    # Update the specific setting
    dws[mf_key][slot_str][setting_type] = value
    dws["Detector_Change"] = "1"

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
        update all MF0/MF1 range/ref spin boxes.
        """
        try:
            with open(shared_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        dws = data.get("DetectorWindowSettings", {})
        if not isinstance(dws, dict):
            return

        # Load MF0 settings
        mf0_data = dws.get("mf0", {})
        for slot in range(1, 5):
            slot_data = mf0_data.get(str(slot), {})
            range_widget = getattr(self, f'mf0_ch{slot}_range', None)
            ref_widget = getattr(self, f'mf0_ch{slot}_ref', None)
            
            self._set_spin_safely(range_widget, slot_data.get("range", -10))
            self._set_spin_safely(ref_widget, slot_data.get("ref", -30))

        # Load MF1 settings
        mf1_data = dws.get("mf1", {})
        for slot in range(1, 5):
            slot_data = mf1_data.get(str(slot), {})
            range_widget = getattr(self, f'mf1_ch{slot}_range', None)
            ref_widget = getattr(self, f'mf1_ch{slot}_ref', None)
            
            self._set_spin_safely(range_widget, slot_data.get("range", -10))
            self._set_spin_safely(ref_widget, slot_data.get("ref", -30))

    # ------------------------------------------------------
    # UI construction
    # ------------------------------------------------------
    def construct_ui(self):
        data_window_container = StyledContainer(
            variable_name="data_window_container", left=0, top=0, height=800, width=280
        )
        
        # =============== MAINFRAME 0 HEADER ===============
        StyledLabel(
            container=data_window_container, text="MAINFRAME 0",
            variable_name="mf0_header", left=10, top=5,
            width=260, height=25, font_size=120, flex=True,
            justify_content="center", color="#000", bold=True,
            background_color="#E8F4FD"
        )

        # =============== MF0 Slots ===============
        for slot in range(1, 5):
            base_y = 30 + (slot - 1) * 90  # 90px spacing per slot
            
            # Slot label
            StyledLabel(
                container=data_window_container, text=f"Slot {slot}",
                variable_name=f"mf0_ch{slot}_label", left=10, top=base_y,
                width=100, height=25, font_size=110, flex=True,
                justify_content="left", color="#222", bold=True
            )

            # Range controls
            StyledLabel(
                container=data_window_container, text="Range",
                variable_name=f"mf0_ch{slot}_range_lb", left=10, top=base_y + 25,
                width=60, height=25, font_size=100, flex=True,
                justify_content="right", color="#222"
            )

            setattr(self, f'mf0_ch{slot}_range', StyledSpinBox(
                container=data_window_container, variable_name=f"mf0_ch{slot}_range_in",
                left=80, top=base_y + 25, value=-10, width=60, height=24,
                min_value=-70, max_value=10, step=1, position="absolute"
            ))

            StyledLabel(
                container=data_window_container, text="dBm",
                variable_name=f"mf0_ch{slot}_range_unit", left=150, top=base_y + 25,
                width=30, height=25, font_size=100, flex=True,
                justify_content="left", color="#222"
            )

            # Ref controls
            StyledLabel(
                container=data_window_container, text="Ref",
                variable_name=f"mf0_ch{slot}_ref_lb", left=10, top=base_y + 50,
                width=60, height=25, font_size=100, flex=True,
                justify_content="right", color="#222"
            )

            setattr(self, f'mf0_ch{slot}_ref', StyledSpinBox(
                container=data_window_container, variable_name=f"mf0_ch{slot}_ref_in",
                left=80, top=base_y + 50, value=-30, width=60, height=24,
                min_value=-100, max_value=0, step=1, position="absolute"
            ))

            StyledLabel(
                container=data_window_container, text="dBm",
                variable_name=f"mf0_ch{slot}_ref_unit", left=150, top=base_y + 50,
                width=30, height=25, font_size=100, flex=True,
                justify_content="left", color="#222"
            )

            # Buttons
            setattr(self, f'mf0_apply_range_btn{slot}', StyledButton(
                container=data_window_container, text="Range",
                variable_name=f"mf0_apply_range_btn{slot}", left=190, top=base_y + 25,
                height=24, width=60, font_size=80,
                normal_color="#007BFF", press_color="#0056B3"
            ))

            setattr(self, f'mf0_apply_ref_btn{slot}', StyledButton(
                container=data_window_container, text="Ref",
                variable_name=f"mf0_apply_ref_btn{slot}", left=190, top=base_y + 50,
                height=24, width=60, font_size=80,
                normal_color="#007BFF", press_color="#0056B3"
            ))

            setattr(self, f'mf0_apply_auto_btn{slot}', StyledButton(
                container=data_window_container, text="Auto",
                variable_name=f"mf0_apply_auto_btn{slot}", left=190, top=base_y + 75,
                width=60, height=20, font_size=80,
                normal_color="#28A745", press_color="#1E7E34"
            ))

        # =============== MAINFRAME 1 HEADER ===============
        StyledLabel(
            container=data_window_container, text="MAINFRAME 1",
            variable_name="mf1_header", left=10, top=395,
            width=260, height=25, font_size=120, flex=True,
            justify_content="center", color="#000", bold=True,
            background_color="#FFF3E0"
        )

        # =============== MF1 Slots ===============
        for slot in range(1, 5):
            base_y = 420 + (slot - 1) * 90  # 90px spacing per slot, offset from MF0
            
            # Slot label
            StyledLabel(
                container=data_window_container, text=f"Slot {slot}",
                variable_name=f"mf1_ch{slot}_label", left=10, top=base_y,
                width=100, height=25, font_size=110, flex=True,
                justify_content="left", color="#222", bold=True
            )

            # Range controls
            StyledLabel(
                container=data_window_container, text="Range",
                variable_name=f"mf1_ch{slot}_range_lb", left=10, top=base_y + 25,
                width=60, height=25, font_size=100, flex=True,
                justify_content="right", color="#222"
            )

            setattr(self, f'mf1_ch{slot}_range', StyledSpinBox(
                container=data_window_container, variable_name=f"mf1_ch{slot}_range_in",
                left=80, top=base_y + 25, value=-10, width=60, height=24,
                min_value=-70, max_value=10, step=1, position="absolute"
            ))

            StyledLabel(
                container=data_window_container, text="dBm",
                variable_name=f"mf1_ch{slot}_range_unit", left=150, top=base_y + 25,
                width=30, height=25, font_size=100, flex=True,
                justify_content="left", color="#222"
            )

            # Ref controls
            StyledLabel(
                container=data_window_container, text="Ref",
                variable_name=f"mf1_ch{slot}_ref_lb", left=10, top=base_y + 50,
                width=60, height=25, font_size=100, flex=True,
                justify_content="right", color="#222"
            )

            setattr(self, f'mf1_ch{slot}_ref', StyledSpinBox(
                container=data_window_container, variable_name=f"mf1_ch{slot}_ref_in",
                left=80, top=base_y + 50, value=-30, width=60, height=24,
                min_value=-100, max_value=0, step=1, position="absolute"
            ))

            StyledLabel(
                container=data_window_container, text="dBm",
                variable_name=f"mf1_ch{slot}_ref_unit", left=150, top=base_y + 50,
                width=30, height=25, font_size=100, flex=True,
                justify_content="left", color="#222"
            )

            # Buttons
            setattr(self, f'mf1_apply_range_btn{slot}', StyledButton(
                container=data_window_container, text="Range",
                variable_name=f"mf1_apply_range_btn{slot}", left=190, top=base_y + 25,
                height=24, width=60, font_size=80,
                normal_color="#007BFF", press_color="#0056B3"
            ))

            setattr(self, f'mf1_apply_ref_btn{slot}', StyledButton(
                container=data_window_container, text="Ref",
                variable_name=f"mf1_apply_ref_btn{slot}", left=190, top=base_y + 50,
                height=24, width=60, font_size=80,
                normal_color="#007BFF", press_color="#0056B3"
            ))

            setattr(self, f'mf1_apply_auto_btn{slot}', StyledButton(
                container=data_window_container, text="Auto",
                variable_name=f"mf1_apply_auto_btn{slot}", left=190, top=base_y + 75,
                width=60, height=20, font_size=80,
                normal_color="#28A745", press_color="#1E7E34"
            ))

        # Wire up events for MF0
        for slot in range(1, 5):
            getattr(self, f'mf0_apply_auto_btn{slot}').do_onclick(
                lambda *_, s=slot: self.run_in_thread(self.onclick_apply_mf0_autorange, s))
            getattr(self, f'mf0_apply_range_btn{slot}').do_onclick(
                lambda *_, s=slot: self.run_in_thread(self.onclick_apply_mf0_range, s))
            getattr(self, f'mf0_apply_ref_btn{slot}').do_onclick(
                lambda *_, s=slot: self.run_in_thread(self.onclick_apply_mf0_ref, s))

        # Wire up events for MF1
        for slot in range(1, 5):
            getattr(self, f'mf1_apply_auto_btn{slot}').do_onclick(
                lambda *_, s=slot: self.run_in_thread(self.onclick_apply_mf1_autorange, s))
            getattr(self, f'mf1_apply_range_btn{slot}').do_onclick(
                lambda *_, s=slot: self.run_in_thread(self.onclick_apply_mf1_range, s))
            getattr(self, f'mf1_apply_ref_btn{slot}').do_onclick(
                lambda *_, s=slot: self.run_in_thread(self.onclick_apply_mf1_ref, s))

        self.data_window_container = data_window_container
        return data_window_container

    # ================= MF0 Event Handlers =================
    def onclick_apply_mf0_autorange(self, slot):
        update_detector_window_setting(0, slot, "auto_range", True)
        update_detector_window_setting(0, slot, "range", None)  # Clear manual range

    def onclick_apply_mf0_range(self, slot):
        range_widget = getattr(self, f'mf0_ch{slot}_range')
        range_val = float(range_widget.get_value())
        update_detector_window_setting(0, slot, "range", range_val)
        update_detector_window_setting(0, slot, "auto_range", False)

    def onclick_apply_mf0_ref(self, slot):
        ref_widget = getattr(self, f'mf0_ch{slot}_ref')
        ref_val = float(ref_widget.get_value())
        update_detector_window_setting(0, slot, "ref", ref_val)

    # ================= MF1 Event Handlers =================
    def onclick_apply_mf1_autorange(self, slot):
        update_detector_window_setting(1, slot, "auto_range", True)
        update_detector_window_setting(1, slot, "range", None)  # Clear manual range

    def onclick_apply_mf1_range(self, slot):
        range_widget = getattr(self, f'mf1_ch{slot}_range')
        range_val = float(range_widget.get_value())
        update_detector_window_setting(1, slot, "range", range_val)
        update_detector_window_setting(1, slot, "auto_range", False)

    def onclick_apply_mf1_ref(self, slot):
        ref_widget = getattr(self, f'mf1_ch{slot}_ref')
        ref_val = float(ref_widget.get_value())
        update_detector_window_setting(1, slot, "ref", ref_val)

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

            # Handle old command format if needed
            # (Can be removed in future versions)

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