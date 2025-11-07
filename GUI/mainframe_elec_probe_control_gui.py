from remi import start, App
import os, threading, webview
from GUI.lib_gui import *

shared_path = os.path.join("database", "shared_memory.json")

class elecprobe(App):
    def __init__(self, *args, **kwargs):
        self._user_stime = None
        if "editing_mode" not in kwargs:
            super(elecprobe, self).__init__(*args, **{"static_file_path": {"my_res": "./res/"}})

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
        ROW_TOPS = [45, 85, 125, 165, 205]
        ROW_H = 30

        elecprobe_container = StyledContainer(
            variable_name="instruments_container", left=0, top=0, height=590, width=1100, bg_color=True, color="#F5F5F5"
        )

        xyz_container = StyledContainer(
            container=elecprobe_container, variable_name="xyz_container", border=0,
            left=0, top=400, height=190, width=490
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
            ("R (KΩ)", "o", 137),
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
            container=smu_control_container, variable_name="set_output", text=["A", "B"],
            left=105, top=15, width=80, height=25
        )

        self.set_output_on = StyledButton(
            container=smu_control_container, variable_name="set_output_on", text="ON",
            left=195, top=15, width=50, height=25
        )

        self.set_output_off = StyledButton(
            container=smu_control_container, variable_name="set_output_off", text="OFF",
            left=250, top=15, width=50, height=25
        )

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

            StyledLabel(
                container=smu_control_container,
                text=label,
                variable_name=f"set_lb_{i}",
                left=5, top=top_pos, width=145, height=25,
                font_size=110, color="#222", position="absolute",
                flex=True, justify_content="left"
            )

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
        position_texts = ["0", "0", "0"]
        position_unit = ["um", "um", "um"]
        init_value = ["10.0", "10.0", "10.0"]

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

        #self.tec_configure_btn.do_onclick(lambda *_: self.run_in_thread(self.onclick_configure_btn))

        self.elecprobe_container = elecprobe_container
        return elecprobe_container

def run_remi():
    start(
        elecprobe,
        address="0.0.0.0",
        port=8004,
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
        f"http://{local_ip}:8004",
        width=1022+100,
        height=756-110,
        resizable=True,
        hidden=False,
    )
    webview.start()
