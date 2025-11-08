from GUI.lib_gui import *
from remi import start, App
import serial.tools.list_ports
import threading
import os
import pyvisa
import re

command_path = os.path.join("database", "command.json")


class connect_config(App):
    def __init__(self, *args, **kwargs):
        # UI elements
        self.stage_dd = None
        self.sensor_dd = None
        self.tec_dd = None
        self.confirm_btn = None

        # Cache for detected resources
        self._last_resources = []
        self._resource_map = {}   # display_label -> actual_resource_string

        if "editing_mode" not in kwargs:
            super(connect_config, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ---------- REMI lifecycle ----------

    def main(self):
        return self.construct_ui()

    def idle(self):
        """
        Periodically rescan available interfaces and update dropdowns
        when something actually changes.
        """
        try:
            resources, mapping = self._scan_resources()
            need_refresh = (
                resources != self._last_resources
                or self.stage_dd is None
                or self.tec_dd is None
                or self.sensor_dd is None
            )

            if need_refresh:
                self._last_resources = resources
                self._resource_map = mapping

                # Guard: widgets might not be ready on first idle calls
                if self.stage_dd is not None:
                    self._refresh_dropdown(self.stage_dd, resources)
                if self.sensor_dd is not None:
                    self._refresh_dropdown(self.sensor_dd, resources)
                if self.tec_dd is not None:
                    self._refresh_dropdown(self.tec_dd, resources)

        except Exception as e:
            # Never let idle die silently
            print("[Connect Config][idle] Error:", e)

    # ---------- UI construction ----------

    def construct_ui(self):
        connect_config_setting_container = StyledContainer(
            variable_name="connect_config_setting_container",
            left=0,
            top=0,
            height=180,
            width=200,
        )

        # ---- Stage ----
        StyledLabel(
            container=connect_config_setting_container,
            text="Stage",
            variable_name="stage",
            left=0,
            top=10,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )

        self.stage_dd = StyledDropDown(
            container=connect_config_setting_container,
            variable_name="stage_dd",
            text="N/A",
            left=70,
            top=10,
            width=100,
            height=25,
            position="absolute",
        )

        # ---- Sensor ----
        StyledLabel(
            container=connect_config_setting_container,
            text="Sensor",
            variable_name="sensor",
            left=0,
            top=45,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )

        self.sensor_dd = StyledSpinBox(
            container=connect_config_setting_container,
            variable_name="sensor_dd",
            value=20,
            max_value=100,
            min_value=0,
            step=1,
            left=70,
            top=45,
            width=83,
            height=25,
            position="absolute",
        )

        # ---- TEC ----
        StyledLabel(
            container=connect_config_setting_container,
            text="TEC",
            variable_name="tec",
            left=0,
            top=80,
            width=60,
            height=25,
            font_size=100,
            flex=True,
            justify_content="right",
            color="#222",
        )

        self.tec_dd = StyledDropDown(
            container=connect_config_setting_container,
            variable_name="tec_dd",
            text="N/A",
            left=70,
            top=80,
            width=100,
            height=25,
            position="absolute",
        )

        # ---- Confirm button ----
        self.confirm_btn = StyledButton(
            container=connect_config_setting_container,
            text="Confirm",
            variable_name="confirm_btn",
            left=68,
            top=142,
            height=25,
            width=70,
            font_size=90,
        )

        self.confirm_btn.do_onclick(
            lambda *_: self._run_in_thread(self.onclick_confirm)
        )

        self.connect_config_setting_container = connect_config_setting_container
        return connect_config_setting_container

    # ---------- Helpers ----------

    def _run_in_thread(self, target, *args):
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()

    def _scan_resources(self):
        """
        Discover available IO resources.

        Returns:
            resources: [display_label, ...]
            mapping:   {display_label: actual_resource_string}
        """
        resources = []
        mapping = {}

        # --- VISA resources (GPIB/ASRL/etc.) ---
        try:
            rm = pyvisa.ResourceManager()
            visa_resources = rm.list_resources()
            rm.close()

            for r in visa_resources:
                # Only add non-duplicates
                # GPIB0::14::INSTR, ASRL3::INSTR, USB0::...
                if r not in mapping.values():
                    label = r
                    resources.append(label)
                    mapping[label] = r

        except Exception as e:
            print("[Connect config][_scan_resources] VISA scan error:", e)

        # Clean UI
        resources = sorted(set(resources))

        # Ensure at least one option
        if not resources:
            resources = ["N/A"]
            mapping["N/A"] = None

        return resources, mapping

    def _refresh_dropdown(self, dropdown, items):
        if dropdown is None:
            return

        # Skip non-dropdown widgets
        if not hasattr(dropdown, "append"):
            return

        dropdown.empty()

        if not items:
            dropdown.append("N/A")
            dropdown.set_value("N/A")
            return

        for item in items:
            dropdown.append(item)
        dropdown.set_value(items[0])

    # ---------- Confirm logic ----------

    def onclick_confirm(self):
        try:
            # Stage
            stage_label = self.stage_dd.get_value() if self.stage_dd else "N/A"
            stage_resource = self._resource_map.get(stage_label)
            if stage_label == "N/A":
                stage_resource = None

            # Sensor (numeric SpinBox)
            # TODO: Add for multiple NIR devs
            sensor_val = self.sensor_dd.get_value() if self.sensor_dd else None
            try:
                sensor_num = int(sensor_val) if sensor_val is not None else None
            except Exception:
                sensor_num = None

            # TEC
            tec_label = self.tec_dd.get_value() if self.tec_dd else "N/A"
            tec_resource = self._resource_map.get(tec_label)
            if tec_label == "N/A":
                tec_resource = None

            # print("Stage resource:", stage_resource)
            # print("Sensor numeric:", sensor_num)
            # print("TEC resource:", tec_resource)

            config = {
                "stage": stage_resource,
                "sensor": sensor_num,
                "tec": tec_resource,
            }

            file = File("shared_memory", "Port", config)
            file.save()
            print("[Connect Config] Saved Port config:", config)

        except Exception as e:
            print("[Connect Config][onclick_confirm] Error:", e)


if __name__ == "__main__":
    configuration = {
        "config_project_name": "connect_config",
        "config_address": "0.0.0.0",
        "config_port": 7005,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
        "config_start_browser": False,
        "config_resourcepath": "./res/",
    }

    start(
        connect_config,
        address=configuration["config_address"],
        port=configuration["config_port"],
        multiple_instance=configuration["config_multiple_instance"],
        enable_file_cache=configuration["config_enable_file_cache"],
        start_browser=configuration["config_start_browser"],
    )
