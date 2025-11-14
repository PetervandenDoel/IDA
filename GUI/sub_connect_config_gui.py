from GUI.lib_gui import *
from remi import start, App
import serial.tools.list_ports
import webview
import threading
import os
import pyvisa
import re
import time

"""
Scan all visa resources and refresh the drop down.
This calls the ResourceManager so I've hosted the 
subprocess on the clicking of the button found in

"GUI\main_instruments_gui.py"

I was a little concerned about the case where Users
do not click confirm, so I've added that functionality
when a user e"x"its.

Cameron Basara, 2025
"""

# Global vars for event handling
SHOULD_EXIT = False     # set True when user presses Confirm
MAIN_WINDOW = None    # assigned when WebView window is created

command_path = os.path.join("database", "command.json")

class connect_config(App):
    def __init__(self, *args, **kwargs):
        self.stage_dd = None
        self.sensor_dd = None
        self.tec_dd = None
        self.confirm_btn = None

        self._last_resources = []
        self._resource_map = {}   # display_label -> actual_resource_string

        if "editing_mode" not in kwargs:
            super(connect_config, self).__init__(
                *args,
                **{"static_file_path": {"my_res": "./res/"}}
            )

    # ------------------ REMI lifecycle ------------------

    def main(self):
        return self.construct_ui()

    def idle(self):
        """Periodic hardware rescan."""
        try:
            resources, mapping = self._scan_resources()
            need_refresh = (
                resources != self._last_resources
                or self.stage_dd is None
                or self.sensor_dd is None
                or self.tec_dd is None
            )

            if need_refresh:
                self._last_resources = resources
                self._resource_map = mapping

                if self.stage_dd:
                    self._refresh_dropdown(self.stage_dd, resources)
                if self.sensor_dd:
                    pass  # spinbox does not need refresh
                if self.tec_dd:
                    self._refresh_dropdown(self.tec_dd, resources)

        except Exception as e:
            print("[Connect Config][idle] Error:", e)
    
    # ------------------ UI construction ------------------

    def construct_ui(self):
        container = StyledContainer(
            variable_name="connect_config_setting_container",
            left=0, top=0, height=180, width=200
        )

        # ---- Stage ----
        StyledLabel(
            container=container,
            text="Stage",
            variable_name="stage",
            left=0, top=10, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.stage_dd = StyledDropDown(
            container=container,
            variable_name="stage_dd",
            text="N/A",
            left=70, top=10, width=100, height=25,
            position="absolute",
        )

        # ---- Sensor ----
        StyledLabel(
            container=container,
            text="Sensor",
            variable_name="sensor",
            left=0, top=45, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.sensor_dd = StyledSpinBox(
            container=container,
            variable_name="sensor_dd",
            value=20, max_value=100, min_value=0, step=1,
            left=70, top=45, width=83, height=25,
            position="absolute",
        )

        # ---- TEC ----
        StyledLabel(
            container=container,
            text="TEC",
            variable_name="tec",
            left=0, top=80, width=60, height=25,
            font_size=100, flex=True, justify_content="right", color="#222",
        )
        self.tec_dd = StyledDropDown(
            container=container,
            variable_name="tec_dd",
            text="N/A",
            left=70, top=80, width=100, height=25,
            position="absolute",
        )

        # ---- Confirm ----
        self.confirm_btn = StyledButton(
            container=container,
            text="Confirm",
            variable_name="confirm_btn",
            left=68, top=142, height=25, width=70,
            font_size=90,
        )

        self.confirm_btn.do_onclick(
            lambda *_: self._run_in_thread(self.onclick_confirm)
        )

        return container

    # ------------------ Helpers ------------------

    def _run_in_thread(self, target, *args):
        t = threading.Thread(target=target, args=args, daemon=True)
        t.start()

    def _scan_resources(self):
        resources = []
        mapping = {}

        try:
            rm = pyvisa.ResourceManager()
            visa_resources = rm.list_resources()
            rm.close()

            for r in visa_resources:
                if r not in mapping.values():
                    resources.append(r)
                    mapping[r] = r

        except Exception as e:
            print("[Connect Config][_scan_resources] VISA scan error:", e)

        resources = sorted(set(resources))

        if not resources:
            resources = ["N/A"]
            mapping["N/A"] = None

        return resources, mapping

    def _refresh_dropdown(self, dropdown, items):
        if dropdown is None:
            return

        dropdown.empty()

        if not items:
            dropdown.append("N/A")
            dropdown.set_value("N/A")
            return

        for item in items:
            dropdown.append(item)
        dropdown.set_value(items[0])

    # ------------------ Confirm logic ------------------

    def onclick_confirm(self):
        global SHOULD_EXIT

        try:
            # Stage resource
            stage_label = self.stage_dd.get_value()
            stage_resource = self._resource_map.get(stage_label, None)

            # Sensor numeric
            sensor_val = self.sensor_dd.get_value()
            try:
                sensor_num = int(sensor_val)
            except:
                sensor_num = None

            # TEC resource
            tec_label = self.tec_dd.get_value()
            tec_resource = self._resource_map.get(tec_label, None)

            config = {
                "stage": stage_resource,
                "sensor": sensor_num,
                "tec": tec_resource,
            }

            file = File("shared_memory", "Port", config)
            file.save()
            print("[Connect Config] Saved Port config:", config)

            SHOULD_EXIT = True   # signal destroy callback

        except Exception as e:
            print("[Connect Config][onclick_confirm] Error:", e)


# =============================================================================
#                WEBVIEW DESTROY CALLBACK (SAFE SHUTDOWN)
# =============================================================================

def close_and_exit(window):
    """Runs inside the webview event loop."""
    global SHOULD_EXIT

    # Wait for Confirm button to request exit
    while not SHOULD_EXIT:
        time.sleep(0.05)

    print("[Connect Config] Closing window...")

    try:
        window.destroy()
        time.sleep(0.1)
    except Exception as e:
        print("[Connect Config] Error destroying window:", e)

    print("[Connect Config] Window destroyed. Exiting.")
    os._exit(0)

def on_close():
        # print("User clicked 'X', shutting down Connect Config Gui")
        # print("Abrutly done, ignore err")
        os._exit(0)


# =============================================================================
#                MAIN LAUNCHER (REMI + WEBVIEW)
# =============================================================================

if __name__ == "__main__":
    configuration = {
        "config_address": "0.0.0.0",
        "config_port": 7005,
        "config_multiple_instance": False,
        "config_enable_file_cache": False,
    }

    # --- Run Remi (GUI logic) in a background thread ---
    def run_remi():
        start(
            connect_config,
            address=configuration["config_address"],
            port=configuration["config_port"],
            multiple_instance=configuration["config_multiple_instance"],
            enable_file_cache=configuration["config_enable_file_cache"],
            start_browser=False,
        )

    threading.Thread(target=run_remi, daemon=True).start()

    # --- Create main PyWebView window ---
    local_ip = "127.0.0.1"
    MAIN_WINDOW = webview.create_window(
        "Stage Control",
        f"http://{local_ip}:7005",
        width=217,
        height=224,
        resizable=True,
        on_top=True,
    )
    MAIN_WINDOW.events.closing += on_close

    # Start UI loop and attach our destroy callback
    webview.start(close_and_exit, MAIN_WINDOW)