import warnings
# Filter spam warnings, but be aware 
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r".*pkg_resources is deprecated as an API.*",
)

from remi.gui import *
import os
import time
from multiprocessing import Process
import multiprocessing as mp
from time import sleep, monotonic
from motors.config.stage_position import *
from motors.config.stage_config import *
from motors.utils.shared_memory import *
from motors.hal.motors_hal import AxisType
import gc
import plotly.express as px
from pathlib import Path
import matplotlib.pyplot as plt
import shutil
import numpy as np
import pandas as pd
from scipy.io import savemat
from scipy.ndimage import gaussian_filter
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib, logging
matplotlib.use("QtAgg")
web_w = 0
web_h = 0
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
PROGRESS_PATH = BASE_DIR / "database" / "progress.json"
import tempfile 

_ORIG_WSGI_LOG = None
_ORIG_HTTP_LOG = None
_SILENCED = False

def _silence_remi_and_http_logs():
    global _ORIG_WSGI_LOG, _ORIG_HTTP_LOG, _SILENCED
    if _SILENCED:
        return

    for name in ("remi", "remi.server", "remi.request", "remi.gui",
                 "websocket", "websockets"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.CRITICAL)
        lg.propagate = False
        if not lg.handlers:
            lg.addHandler(logging.NullHandler())

    try:
        import wsgiref.simple_server as _wsgi
        if not hasattr(_wsgi.WSGIRequestHandler, "_orig_log_message"):
            _wsgi.WSGIRequestHandler._orig_log_message = _wsgi.WSGIRequestHandler.log_message
        _wsgi.WSGIRequestHandler.log_message = lambda *a, **k: None
        _ORIG_WSGI_LOG = _wsgi.WSGIRequestHandler._orig_log_message
    except Exception:
        pass

    try:
        import http.server as _http
        if not hasattr(_http.BaseHTTPRequestHandler, "_orig_log_message"):
            _http.BaseHTTPRequestHandler._orig_log_message = _http.BaseHTTPRequestHandler.log_message
        _http.BaseHTTPRequestHandler.log_message = lambda *a, **k: None
        _ORIG_HTTP_LOG = _http.BaseHTTPRequestHandler._orig_log_message
    except Exception:
        pass

    _SILENCED = True

def enable_remi_logs(level=logging.INFO):
    global _SILENCED
    try:
        import wsgiref.simple_server as _wsgi
        if hasattr(_wsgi.WSGIRequestHandler, "_orig_log_message"):
            _wsgi.WSGIRequestHandler.log_message = _wsgi.WSGIRequestHandler._orig_log_message
    except Exception:
        pass
    try:
        import http.server as _http
        if hasattr(_http.BaseHTTPRequestHandler, "_orig_log_message"):
            _http.BaseHTTPRequestHandler.log_message = _http.BaseHTTPRequestHandler._orig_log_message
    except Exception:
        pass

    for name in ("remi", "remi.server", "remi.request", "remi.gui",
                 "websocket", "websockets"):
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.propagate = True

    _SILENCED = False

if os.environ.get("REMI_QUIET", "1") != "0":
    _silence_remi_and_http_logs()

def apply_common_style(widget, left, top, width, height, position="absolute", percent=False):
    widget.css_position = position
    widget.css_left = f"{left}px"
    widget.css_top = f"{top}px"
    if percent:
        widget.css_width = f"{width}%"
        widget.css_height = f"{height}%"
    else:
        widget.css_width = f"{width}px"
        widget.css_height = f"{height}px"

class StyledContainer(Container):
    def __init__(self, variable_name, left, top, width=650, height=650, border=False, bg_color=False, color = "#707070",
                 position="absolute", percent=False, overflow=False, container=None, line="1.5px solid #888"):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.variable_name = variable_name
        if border:
            self.style["border"] = line
            self.style["border-radius"] = "4px"
        if bg_color:
            self.style["background-color"] = color
        if overflow:
            self.style.update({
                "overflow": "auto",
                "overflow-y": "scroll",
                "overflow-x": "hidden",
                "max-height": "320px",
                "scrollbar-width": "thin",
                "border-radius": "4px",
                "padding-right": "4px"
            })
        if container:
            container.append(self, self.variable_name)

class StyledButton(Button):
    def __init__(self, text, variable_name, left, top,
                 normal_color="#007BFF", press_color="#0056B3",
                 width=100, height=30, font_size=90,
                 position="absolute", percent=False, container=None):
        super().__init__(text)
        apply_common_style(self, left, top, width, height, position, percent)

        self.variable_name  = variable_name
        self.normal_color   = normal_color
        self.press_color    = press_color
        self.style.update({
            "background-color": normal_color,
            "color": "white",
            "border": "none",
            "border-radius": "4px",
            "box-shadow": "0 2px 5px rgba(0,0,0,0.2)",
            "cursor": "pointer",
            "font-size": f"{font_size}%"
        })

        self.onmousedown.do(lambda w,*a: w.style.update(
            {"background-color": self.press_color}))
        def _recover_and_call(w,*a):
            w.style.update({"background-color": self.normal_color})
            if hasattr(self, "_user_callback"):
                threading.Thread(
                    target=self._user_callback,
                    args=(w,*a),
                    daemon=True
                ).start()
        self.onmouseup.do(_recover_and_call)
        self.onmouseleave.do(lambda w,*a: w.style.update(
            {"background-color": self.normal_color}))

        if container:
            container.append(self, variable_name)

    def do_onclick(self, cb):
        #self._user_callback = cb
        self._user_callback = lambda *_: cb()


class StyledLabel(Label):
    def __init__(self, text, variable_name, left, top,
                 width=150, height=20, font_size=100, color="#444", align="left", position="absolute", percent=False,
                 bold=False, flex=False, justify_content="center", on_line=False, border=False, container=None):
        super().__init__(text)
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name
        if flex:
            self.style.update({
                "display": "flex",
                "justify-content": justify_content,
                "align-items": "center"
            })
        else:
            self.css_text_align = align
        self.style["color"] = color
        if bold:
            self.style["font-weight"] = "bold"
        if on_line:
            self.style["background-color"] = "white"
        if border:
            self.style["border"] = "1.5px solid #888"
            self.style["border-radius"] = "4px"
        if container:
            container.append(self, self.variable_name)

class StyledDropDown(DropDown):
    def __init__(self, text, variable_name, left, top,
                 width=220, height=30, font_size=100, bg_color="#f9f9f9",
                 border="1px solid #aaa", border_radius="4px", padding="3px", position="absolute", percent=False, container=None):
        super().__init__()
        self.append(text)
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_font_size = f"{font_size}%"
        self.variable_name = variable_name
        self.style.update({
            "background-color": bg_color,
            "border": border,
            "border-radius": border_radius,
            "padding": padding
        })
        if container:
            container.append(self, self.variable_name)

class Terminal(TextInput):
    def __init__(self, container, variable_name, left, top, width=220, height=30, percent=False):
        super().__init__(singleline=False)
        self.timestamp = -1
        self.attr_src = ""
        apply_common_style(self, left, top, width, height, percent=percent)
        self.variable_name = variable_name
        self.style.update({
            "border": "1px solid #444",
            "background-color": "#1e1e1e",
            "color": "#f0f0f0",
            "font-family": "monospace",
            "font-size": "13px",
            "padding": "10px",
            "border-radius": "6px",
            "box-shadow": "0 0 6px rgba(0,0,0,0.3)",
            "overflow-y": "auto",
            "white-space": "pre-wrap"
        })
        container.append(self, self.variable_name)
        self.container = container

    def terminal_refresh(self):
        path = os.path.join(os.getcwd(), "log.txt")
        try:
            filetime = os.path.getmtime(path)
        except:
            filetime = -1
        if filetime > self.timestamp:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    log_text = f.read()
            except Exception as e:
                log_text = f"[Error reading log file] {e}"
            reversed_log = "\n".join(reversed(log_text.split("\n")))
            self.container.children["terminal_text"].set_text(reversed_log)
            self.timestamp = filetime

class StyledFileUploader(FileUploader):
    def __init__(self, variable_name, left, top, width=300, height=30, position="absolute", percent=False, container=None, savepath="./res/"):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_margin = "0px"
        self.multiple_selection_allowed = False
        self.savepath = savepath
        self.variable_name = variable_name
        if container:
            container.append(self, self.variable_name)

class StyledTable(Table):
    def __init__(self, variable_name, left, top, height, table_width, headers, widths, row, position="absolute", container=None):
        super().__init__()
        apply_common_style(self, left, top, table_width, height, position)
        self.variable_name = variable_name
        self.style.update({
            "table-layout": "fixed",
            "width": f"{table_width}px",
            "border-collapse": "collapse",
            "font-family": "Arial, sans-serif",
            "font-size": "13.5px",
            "color": "#2e2e2e",
            "line-height": "1.4"
        })
        trh = TableRow()
        for h, w in zip(headers, widths):
            trh.append(TableItem(h, style={
                "width": f"{w}px",
                "height": f"{height}px",
                "font-weight": "bold",
                "text-align": "center",
                "background-color": "#e4e9f0",
                "color": "#1a1a1a",
                "border-bottom": "2px solid #c8c8c8",
                "padding": "1px 2px"
            }))
        self.append(trh)
        for r in range(row - 1):
            tr = TableRow()
            bg = "#ffffff" if r % 2 == 0 else "#f6f7f9"
            for w in widths:
                tr.append(TableItem("", style={
                    "width": f"{w}px",
                    "height": f"{height}px",
                    "text-align": "right",
                    "background-color": bg,
                    "border-bottom": "1px solid #ebebeb",
                    "padding": "1px 2px"
                }))
            self.append(tr)
        if container:
            container.append(self, self.variable_name)

class StyledCheckBox(CheckBox):
    def __init__(self, variable_name, left, top, width=30, height=30, position="absolute", percent=False, container=None):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.css_margin = "5px"
        self.variable_name = variable_name
        if container:
            container.append(self, self.variable_name)

class StyledTextInput(TextInput):
    def __init__(self, variable_name, left, top, width=150, height=30, text="", position="absolute", percent=False, container=None):
        super().__init__()
        apply_common_style(self, left, top, width, height, position, percent)
        self.set_text(text)
        self.variable_name = variable_name
        self.style.update({
            "padding": "0 8px",
            "border": "1px solid #aaa",
            "border-radius": "4px",
            "box-shadow": "inset 0 1px 3px rgba(0,0,0,0.1)",
            "background-color": "#fafafa",
            "font-size": "15px",
            "color": "#333",
            "line-height": f"{height}px",
            "overflow": "hidden",
            "text-align": "center",
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
            "white-space": "nowrap",
            "overflow-x": "hidden",
            "overflow-y": "hidden",
            "resize": "none"
        })
        if container:
            container.append(self, self.variable_name)

class StyledImageBox(Image):
    def __init__(self, image_path, variable_name, left, top,
                 width=400, height=300, position="absolute", percent=False, container=None):
        super().__init__(image_path, width=width, height=height)
        apply_common_style(self, left, top, width, height, position, percent)
        self.variable_name = variable_name
        if container:
            container.append(self, self.variable_name)

class StyledSpinBox(SpinBox):
    def __init__(self, variable_name, left, top,
                 width=150, height=30, value=0,
                 step=1, min_value=None, max_value=None,
                 position="absolute", percent=False,
                 container=None):
        super().__init__()

        apply_common_style(self, left, top, width, height, position, percent)

        self.set_value(str(value))
        self.attr_step = str(step)
        if min_value is not None:
            self.attr_min = str(min_value)
        if max_value is not None:
            self.attr_max = str(max_value)

        self.variable_name = variable_name

        self.style.update({
            "padding-top": "0px",
            "padding-right": "0px",
            "padding-bottom": "0px",
            "padding-left": "15px",
            "border": "1px solid #aaa",
            "border-radius": "4px",
            "box-shadow": "inset 0 1px 3px rgba(0,0,0,0.1)",
            "background-color": "#fafafa",
            "font-size": "15px",
            "color": "#333",
            "line-height": f"{height}px",
            "text-align": "center",
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
            "white-space": "nowrap",
            "overflow": "hidden",
            "overflow-x": "hidden",
            "overflow-y": "hidden",
            "resize": "none"
        })

        if container:
            container.append(self, self.variable_name)

class Memory():
    def __init__(self):
        self.x_pos = 0
        self.y_pos = 0
        self.z_pos = 0
        self.fr_pos = 0
        self.cp_pos = 0

    def writer_pos(self):
        shm, raw = open_shared_stage_position()
        sp = StagePosition(shared_struct=raw)
        # write into shared memory
        sp.set_positions(AxisType.X, 123.456)
        #sp.set_homed(AxisType.X)

        # Clean - explicitly delete the object first
        del sp
        del raw
        shm.close()

    def reader_pos(self):
        # give writer a moment
        # sleep(0.1)
        shm, raw = open_shared_stage_position("stage_position")
        sp = StagePosition(shared_struct=raw)
        self.x_pos = round(sp.x.position, 1)
        self.y_pos = round(sp.y.position, 1)
        self.z_pos = round(sp.z.position, 1)
        self.fr_pos = round(sp.fr.position, 1)
        self.cp_pos = round(sp.cp.position, 1)

        # Clean - explicitly delete the object first
        del sp
        del raw
        shm.close()

class File():
    def __init__(self, filename, data_name, data_info="", data_name2="", data_info2=""):
        self.filename = filename
        self.data_name = data_name
        self.data_name2 = data_name2
        self.data_info = data_info
        self.data_info2 = data_info2

    # def _safe_write(self, data, filepath):
    #     temp_filepath = filepath + ".tmp"
    #     with open(temp_filepath, "w", encoding="utf-8") as f:
    #         json.dump(data, f, indent=2)
    #     os.replace(temp_filepath, filepath)  # 原子替换
    def _safe_write(self, data, filepath):
        """
        Robust, cross-platform atomic write:
        - write to a unique temp file next to the target
        - flush + fsync
        - os.replace with a short Windows retry loop (handles transient EACCES)
        """
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        # Create a unique temp file next to the destination (prevents .tmp collisions)
        fd, tmp_path = tempfile.mkstemp(
            prefix=os.path.basename(filepath) + ".",
            suffix=".tmp",
            dir=os.path.dirname(filepath) or ".",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # On Windows, another reader/writer may briefly lock the dest.
            # Retry os.replace a few times with small backoff.
            for attempt in range(8):
                try:
                    os.replace(tmp_path, filepath)  # atomic on POSIX & Windows
                    tmp_path = None  # replaced successfully
                    break
                except PermissionError:
                    if os.name == "nt":
                        time.sleep(0.05 * (attempt + 1))  # 50ms, 100ms, ...
                        continue
                    raise
        finally:
            # If replace succeeded, tmp_path is gone; otherwise clean up
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except FileNotFoundError:
                    pass
    def save(self):
        filepath = os.path.join("database", f"{self.filename}.json")
        os.makedirs("database", exist_ok=True)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        data[self.data_name] = self.data_info
        if self.data_info2 != "":
            data[self.data_name2] = self.data_info2

        self._safe_write(data, filepath)

    def init(self):
        filepath = os.path.join("database", f"{self.filename}.json")
        os.makedirs("database", exist_ok=True)
        data = {
            "User": "Guest",
            "Project": "MyProject",
            "User_add": "Guest",
            "Image": "TSP/none.png",
            "Web": "",
            "FileFormat": {"csv": 1, "mat": 1, "png": 1, "pdf": 1},
            "FilePath": "",
            "Limit": {"x": "Yes", "y": "Yes", "z": "Yes", "chip": "Yes", "fiber": "Yes"},
            "FineA": {"window_size": 20, "step_size": 2, "max_iters": 10, "detector": 1, "timeout_s": 30},
            "AreaS": {"pattern": "spiral", "x_size": 20.0, "x_step": 1.0, "y_size": 20.0, "y_step": 1.0, "plot": "New"},
            "Sweep": {"wvl": 1550.0, "speed": 1.0, "power": 0.0, "step": 0.001, "start": 1500.0, "end": 1600.0, "done": "Laser On", "sweep": 0, "on": 0},
            "ScanPos": {"x": 0, "y": 0, "move": 0},
            "StagePos": {"x": 0, "y": 0},
            "AutoSweep": 0,
            "Configuration": {"stage": "", "sensor": "", "tec": ""},
            "Configuration_check": {"stage": 0, "sensor": 0, "tec": 0},
            "Port": {"stage": 7, "sensor": 20, "tec": 3},
            "DeviceName": "Default",
            "DeviceNum": 0
        }

        self._safe_write(data, filepath)


class UserConfigManager:
    """
    Class to manager user and project configuration settings on startup.

    mainframe_stage_control_gui.py uses this to load settings on startup.
    
    Extensible only for stage control and sensor control as of right now.
    """
    
    def __init__(self, user, project):
        self.user = user
        self.project = project
        module_dir = Path(__file__).resolve().parent
        base_userdata_dir = module_dir / "UserData"

        self.user_dir = base_userdata_dir / user
        self.project_dir = self.user_dir / project
        self.user_defaults_path = self.user_dir / "user_defaults.json"
        self.project_config_path = self.project_dir / "project_config.json"

        # self.user_dir = os.path.join("UserData", user)
        # self.project_dir = os.path.join("UserData", user, project)
        # self.user_defaults_path = os.path.join(self.user_dir, "user_defaults.json")
        # self.project_config_path = os.path.join(self.project_dir, "project_config.json")
        
        # Default configuration template
        self.default_config = {
            "Sweep": {
                "start": 1500.0,
                "end": 1600.0,
                "step": 0.001,
                "power": 0.0,
                "on": False,
                "done": "Laser On"
            },
            "DetectorWindowSettings": {},
            "AreaS": {
                "x_size": 50,
                "x_step": 5,
                "y_size": 50,
                "y_step": 5,
                "pattern": "spiral",
                "primary_detector": "MAX",
                "plot": "New"
            },
            "FineA": {
                "window_size": 10.0,
                "step_size": 1.0,
                "min_gradient_ss": 0.5,
                "max_iters": 10,
                "detector": "Max",
                "ref_wl": 1550.0,
                "timeout_s": 30
            },
            "InitialPositions": {},  # Applies no defaults
            "Configuration": {
                "stage": "",  # No config stored by default
                "sensor": ""  # No config stored by default
            }
        }
    
    def load_config(self):
        """
        Load merged configuration with hierarchy:
        1. Start with defaults
        2. Override with user defaults (if exists)
        3. Override with project config (if exists)
        """
        # Start with system defaults
        config = self._deep_copy_dict(self.default_config)
        
        # Load user defaults
        user_defaults = self._load_json_safe(self.user_defaults_path)
        if user_defaults:
            config = self._merge_configs(config, user_defaults)
        
        # Load project overrides
        project_config = self._load_json_safe(self.project_config_path)
        if project_config:
            config = self._merge_configs(config, project_config)
            
        return config
    
    def save_user_defaults(self, config_dict):
        """Save user-level default settings"""
        os.makedirs(self.user_dir, exist_ok=True)
        file_helper = File("user_defaults", "", "")
        file_helper._safe_write(config_dict, self.user_defaults_path)
    
    def save_project_config(self, config_dict):
        """Save project-specific configuration overrides"""
        os.makedirs(self.project_dir, exist_ok=True)
        file_helper = File("project_config", "", "")
        file_helper._safe_write(config_dict, self.project_config_path)
    
    def get_user_defaults(self):
        """Get only user-level defaults (without project overrides)"""
        config = self._deep_copy_dict(self.default_config)
        user_defaults = self._load_json_safe(self.user_defaults_path)
        if user_defaults:
            config = self._merge_configs(config, user_defaults)
        return config
    
    def get_project_overrides(self):
        """Get only project-specific overrides"""
        return self._load_json_safe(self.project_config_path) or {}
    
    def initialize_new_project(self, new_project_name):
        """
        Initialize a new project with user defaults.
        Called when a new project is created.
        """
        new_project_dir = os.path.join("UserData", self.user, new_project_name)
        os.makedirs(new_project_dir, exist_ok=True)
        os.makedirs(os.path.join(new_project_dir, "Spectrum"), exist_ok=True)
        os.makedirs(os.path.join(new_project_dir, "HeatMap"), exist_ok=True)
        
        # Copy user defaults to new project (so they can be customized)
        user_defaults = self.get_user_defaults()
        if user_defaults != self.default_config:  # Only if user has customized defaults
            new_project_config_path = os.path.join(new_project_dir, "project_config.json")
            file_helper = File("project_config", "", "")
            file_helper._safe_write(user_defaults, new_project_config_path)
    
    def _load_json_safe(self, filepath):
        """Safely load JSON file, return None if not found or invalid"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, PermissionError):
            return None
    
    def _deep_copy_dict(self, d):
        """Deep copy a dictionary"""
        import copy
        return copy.deepcopy(d)
    
    def _merge_configs(self, base, override):
        """
        Recursively merge configuration dictionaries.
        Override values take precedence over base values.
        """
        import copy
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    @staticmethod
    def get_config_for_user_project(user, project):
        """Convenience method to get config for any user/project combination"""
        manager = UserConfigManager(user, project)
        return manager.load_config()


class plot():
    def __init__(self, x=None, y=None, filename=None,
                 fileTime=None, user=None, name=None,
                 project=None, data=None, file_format=None,
                 xticks = None, yticks=None, pos_i=None,
                 slot_info: Optional[list] = None, destination_dir = {},
                 meta_data: Optional[Dict] = None
        ):
        if file_format is None:
            self.file_format = {"csv": 1, "mat": 1, "png": 1, "pdf": 1}
        else:
            self.file_format = file_format
        self.x = x
        self.y = y
        self.filename = filename
        self.fileTime = fileTime
        self.user = user
        self.name = name
        self.project = project
        self.data = data
        self.xticks = xticks
        self.yticks = yticks
        self.pos_i = pos_i
        self.slot_info = slot_info
        self.destination_dir = destination_dir
        self.meta_data = meta_data

    def heat_map(self):
        import os
        import numpy as np
        import matplotlib.pyplot as plt
        from mpl_toolkits.axes_grid1 import make_axes_locatable

        data = self.data
        if data is None:
            raise ValueError("self.data is None")

        # rows (y), cols (x)
        num_y, num_x = data.shape
        vmin = float(np.nanmin(data))
        vmax = float(np.nanmax(data))

        # --- step sizes (um) ---
        def _get_step(default_val):
            try:
                return float(default_val)
            except Exception:
                return None

        dx = _get_step(getattr(self, "xticks", None))
        dy = _get_step(getattr(self, "yticks", None))

        # If not present, look for config from area_s directly
        if dx is None and hasattr(self, "area_s"):
            dx = _get_step(self.area_s.get("x_step", None))
        if dy is None and hasattr(self, "area_s"):
            dy = _get_step(self.area_s.get("y_step", None))

        # Final fallback
        if dx is None: dx = 1.0
        if dy is None: dy = dx

        dx = abs(float(dx))
        dy = abs(float(dy))

        # --- coordinate centers  ---
        # spiral: center-origin
        mid_x = (num_x - 1) / 2.0
        mid_y = (num_y - 1) / 2.0

        # centers at (..., -dx, 0, +dx, ...) with (0,0) at grid midpoint
        x_centers = (np.arange(num_x, dtype=float) - mid_x) * dx
        y_centers = (np.arange(num_y, dtype=float) - mid_y) * dy

        # edges for imshow 'extent' (draw squares centered at centers)
        x_edge_min = x_centers[0] - 0.5 * dx
        x_edge_max = x_centers[-1] + 0.5 * dx
        y_edge_min = y_centers[0] - 0.5 * dy
        y_edge_max = y_centers[-1] + 0.5 * dy

        # clean -0.0 labels
        def _clean_zero(arr):
            arr = arr.copy()
            arr[np.isclose(arr, 0.0, atol=1e-12)] = 0.0
            return arr

        x_centers = _clean_zero(x_centers)
        y_centers = _clean_zero(y_centers)

        # --- helpers: exact, analytical mappings ---
        def clamp_idx(j, i):
            j = max(0, min(num_x - 1, int(j)))
            i = max(0, min(num_y - 1, int(i)))
            return j, i

        # index -> relative um used for plot / readout
        def idx_to_rel(j, i):
            px = (j - mid_x) * dx
            py = (i - mid_y) * dy
            return float(px), float(py)

        # relative um (plot coords) -> nearest index (column j, row i)
        def rel_to_idx(px, py):
            j = round(px / dx + mid_x)
            i = round(py / dy + mid_y)
            return clamp_idx(j, i)

        # --- draw ---
        fig, ax = plt.subplots(figsize=(7, 7))
        heat = ax.imshow(
            data,
            origin="lower",  # y increases upward
            cmap="gist_heat",
            vmin=vmin - 3,
            vmax=vmax + 1,
            interpolation="nearest",
            extent=[x_edge_min, x_edge_max, y_edge_min, y_edge_max],
            aspect="equal",
        )

        title = "Area Sweep Heat Map"
        ax.set_title(title, fontsize=16)
        ax.set_xlabel("X (um)")
        ax.set_ylabel("Y (um)")

        # Ticks at sample centers
        ax.set_xticks(x_centers)
        ax.set_yticks(y_centers)

        def _fmt_ticks(vals):
            out = []
            for v in vals:
                if abs(v) < 1e-9:
                    out.append("0")
                elif abs(v - round(v)) < 1e-9:
                    out.append(f"{int(round(v))}")
                else:
                    out.append(f"{v:.1f}")
            return out

        ax.set_xticklabels(_fmt_ticks(x_centers), fontsize=8)
        ax.set_yticklabels(_fmt_ticks(y_centers), fontsize=8)

        # Colorbar
        div = make_axes_locatable(ax)
        cax = div.append_axes("right", size="5%", pad=0.05)
        plt.colorbar(heat, cax=cax, label="Power (dBm)")

        # --- hover crosshair (snap to cell centers) ---
        # Start crosshair at center
        j0, i0 = int(round(mid_x)), int(round(mid_y))
        px0, py0 = idx_to_rel(j0, i0)

        vline = ax.axvline(px0, linestyle="--", linewidth=0.8, alpha=0.9)
        hline = ax.axhline(py0, linestyle="--", linewidth=0.8, alpha=0.9)
        info = ax.text(
            0.01, 0.99, "", transform=ax.transAxes, ha="left", va="top",
            fontsize=9, bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.6)
        )
        crosshair_visible = [True]

        def onmove(event):
            if not crosshair_visible[0] or event.inaxes != ax:
                return
            if event.xdata is None or event.ydata is None:
                return
            # pointer in plot coords (relative um)
            px, py = float(event.xdata), float(event.ydata)
            j, i = rel_to_idx(px, py)      # nearest cell
            px_c, py_c = idx_to_rel(j, i)  # exact center of that cell

            vline.set_xdata([px_c, px_c])
            hline.set_ydata([py_c, py_c])

            val = data[i, j]
            info.set_text(f"idx=({j},{i})  rel=({px_c:.1f},{py_c:.1f}) um  {val:.3f} dBm")
            fig.canvas.draw_idle()

        def onkey(event):
            if event.key == "x":
                crosshair_visible[0] = not crosshair_visible[0]
                for art in (vline, hline, info):
                    art.set_visible(crosshair_visible[0])
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", onmove)
        fig.canvas.mpl_connect("key_press_event", onkey)

        # --- click -> write ScanPos ---
        def onclick(event):
            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                return
            px, py = float(event.xdata), float(event.ydata)
            j, i = rel_to_idx(px, py)
            px_c, py_c = idx_to_rel(j, i)
            val = data[i, j]
            print(f"Clicked idx=({j},{i})  rel_center=({px_c:.1f},{py_c:.1f}) um  Value={val:.3f} dBm")

            # Emit both index (BL) and relative um (center for spiral)
            payload = {
                "x": j,
                "y": i,
                "x_index": j,         # explicit duplicate for clarity
                "y_index": i,
                "x_rel": px_c,        # um in the plot's coordinate frame
                "y_rel": py_c,
                "dx": dx,
                "dy": dy,
                "move": 1
            }
            File("shared_memory", "ScanPos", payload).save()

        fig.canvas.mpl_connect("button_press_event", onclick)

        fig.tight_layout(rect=[0, 0, 0.95, 1.0])
        plt.show()

        # --- save outputs ---
        out_dir = os.path.join(".", "UserData", self.user, self.project, "HeatMap")
        os.makedirs(out_dir, exist_ok=True)
        fig_path = os.path.join(out_dir, f"{self.filename}_{self.fileTime}.png")
        fig.savefig(fig_path, dpi=300)
        print(f"Saved heatmap figure: {fig_path}")
        csv_path = os.path.join(out_dir, f"{self.filename}_{self.fileTime}.csv")
        np.savetxt(csv_path, data, delimiter=",", fmt="%.4f")
        print(f"Saved heatmap data: {csv_path}")
        plt.close(fig)

    def _cleanup_old_plots(self, keep: int = 1) -> None:
        self.output_dir = Path("./res/spectral_sweep")
        files = sorted(
            (p for p in self.output_dir.glob("spectral_sweep_*.png")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for p in files[keep:]:
            try:
                p.unlink()
            except OSError:
                pass

    def generate_plots(self):
        x_axis = self.x
        y_values = self.y
        filename = self.filename
        fileTime = self.fileTime
        user = self.user
        name = self.name
        project = self.project
        if self.destination_dir == {}:
            path = os.path.join(".", "UserData", user, project, "Spectrum", name)
        else:
            path = self.destination_dir.get("dest_dir")
            path = os.path.join(path, "Spectrum", name)

        try:
            plots = {"Wavelength [nm]": x_axis}
            plotnames = []
            for element in range(0, len(y_values)):
                if self.slot_info is not None:
                    plotname = f'Detector {self.slot_info[element][0]}.{self.slot_info[element][1]+1}'
                else:
                    plotname = "Detector " + str(element + 1)
                plots[plotname] = y_values[element]
                plotnames.append(plotname)
            fig = px.line(plots, x="Wavelength [nm]", y=plotnames,
                          labels={'value': "Power [dBm]", 'x': "Wavelength [nm]"})
            if self.slot_info is not None:
                for i, slot, head in enumerate(self.slot_info):
                    fig.data[i].name = f'{slot}.{head}'
            else:
                for i in range(0, len(y_values)):
                    fig.data[i].name = str(i + 1)
            fig.update_layout(legend_title_text="Detector")
            output_html = os.path.join(path, f"{filename}_{fileTime}.html")
            os.makedirs(os.path.dirname(output_html), exist_ok=True)
            fig.write_html(output_html)

            # output_html2 = os.path.join(file_path, f"{filename}_{fileTime}.html")
            # os.makedirs(os.path.dirname(output_html2), exist_ok=True)
            # fig.write_html(output_html2)
        except Exception as e:
            try:
                print("Exception generating html plot")
                print(e)
            finally:
                e = None
                del e
        if self.file_format["csv"] == 1:
            try:
                df = pd.DataFrame({"Wavelength [nm]": x_axis})
                for element in range(len(y_values)):
                    df[f"Detector {element + 1}"] = y_values[element]
                output_csv = os.path.join(path, f"{filename}_{fileTime}.csv")
                os.makedirs(os.path.dirname(output_csv), exist_ok=True)
                df.to_csv(output_csv, index=False)

                # output_csv2 = os.path.join(file_path, f"{filename}_{fileTime}.csv")
                # os.makedirs(os.path.dirname(output_csv2), exist_ok=True)
                # df.to_csv(output_csv2, index=False)
            except Exception as e:
                print("Exception saving csv")
                print(e)

        if self.file_format["mat"] == 1:
            try:
                detectors_matrix = np.column_stack(y_values) if len(y_values) > 0 else np.empty((len(x_axis), 0))
                detector_names = [f"Detector {i + 1}" for i in range(len(y_values))]
                mat_dict = {
                    "wavelength_nm": np.asarray(x_axis),
                    "detectors_dbm": np.asarray(detectors_matrix),
                    "detector_names": np.array(detector_names, dtype=object),
                    "filename": np.array(filename, dtype=object),
                    "fileTime": np.array(fileTime, dtype=object),
                    "user": np.array(user, dtype=object),
                    "project": np.array(project, dtype=object),
                    "name": np.array(name, dtype=object),
                    "meta": self.meta_data,
                }
                output_mat = os.path.join(path, f"{filename}_{fileTime}.mat")
                os.makedirs(os.path.dirname(output_mat), exist_ok=True)
                savemat(output_mat, mat_dict)

                # output_mat2 = os.path.join(file_path, f"{filename}_{fileTime}.mat")
                # os.makedirs(os.path.dirname(output_mat2), exist_ok=True)
                # savemat(output_mat2, mat_dict)
            except Exception as e:
                print("Exception saving mat")
                print(e)

        try:
            image_dpi = 20
            plt.figure(figsize=(100 / image_dpi, 100 / image_dpi), dpi=image_dpi)
            for element in range(0, len(y_values)):
                plt.plot(x_axis, y_values[element], linewidth=0.2, label=f"{element+1}")
            plt.xlabel("Wavelength [nm]")
            plt.ylabel("Power [dBm]")
            plt.legend(title="Detector", fontsize=8, title_fontsize=9, ncol=2, loc='upper right')
            plt.tight_layout()

            if self.file_format["pdf"] == 1:
                output_pdf = os.path.join(path, f"{filename}_{fileTime}.pdf")
                os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
                plt.savefig(output_pdf, dpi=image_dpi)

                # output_pdf2 = os.path.join(file_path, f"{filename}_{fileTime}.pdf")
                # os.makedirs(os.path.dirname(output_pdf2), exist_ok=True)
                # plt.savefig(output_pdf2, dpi=image_dpi)

            if self.file_format["png"] == 1:
                output_png2 = os.path.join(path, f"{filename}_{fileTime}.png")
                os.makedirs(os.path.dirname(output_png2), exist_ok=True)
                plt.savefig(output_png2, dpi=300)

                # output_png3= os.path.join(file_path, f"{filename}_{fileTime}.png")
                # os.makedirs(os.path.dirname(output_png3), exist_ok=True)
                # plt.savefig(output_png3, dpi=300)

            output_png = os.path.join(".", "res", "spectral_sweep", f"{filename}_{fileTime}.png")
            os.makedirs(os.path.dirname(output_png), exist_ok=True)
            plt.savefig(output_png, dpi=300)
            self._cleanup_old_plots(keep=1)

            plt.close()
            file = File("shared_memory", "Image", f"spectral_sweep/{filename}_{fileTime}.png", "Web", output_html)
            file.save()
        except Exception as e:
            try:
                print("Exception generating pdf plot")
                print(e)
            finally:
                e = None
                del e

import numpy as np
import pandas as pd
from scipy.io import savemat
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import matplotlib.pyplot as plt


class plot_luna():
    """Handles OVA/Luna measurement plotting and saving"""
    def __init__(self, data_matrix, filename, fileTime, 
                 user, name, project, auto, file_format, 
                 destination_dir={}, meta_data=None):
        if file_format is None:
            self.file_format = {"csv": 1, "mat": 1, "png": 1, "pdf": 1}
        else:
            self.file_format = file_format
        
        self.data_matrix = data_matrix  # Tuple: (wavelength_array, list_of_24_measurement_arrays)
        self.filename = filename
        self.fileTime = fileTime
        self.user = user
        self.name = name
        self.project = project
        self.auto = auto
        self.destination_dir = destination_dir
        self.meta_data = meta_data
        
        # Extract columns for plotting (OVA data format)
        self.wavelength = data_matrix[0]          # Array of 65536 wavelengths
        self.measurements = data_matrix[1]         # List of 24 measurement arrays
        
        # Based on Luna OVA output.txt format, the measurements are:
        # Index 0: Frequency (GHz)
        # Index 1: Insertion Loss (dB)
        # Index 2: Group Delay (ps)   
        self.insertion_loss = self.measurements[1]  # Index 1
        self.group_delay = self.measurements[2]     # Index 2
        
        # All column names from Luna OVA output.txt
        self.column_names = [
            "Wavelength (nm)",
            "Frequency (GHz)",
            "Insertion Loss (dB)",
            "Group Delay (ps)",
            "Chromatic Dispersion (ps/nm)",
            "Polarization Dependent Loss (dB)",
            "Polarization Mode Dispersion (ps)",
            "Linear Phase Deviation (rad)",
            "Quadratic Phase Deviation (rad)",
            "JM Element a Amplitude",
            "JM Element b Amplitude",
            "JM Element c Amplitude",
            "JM Element d Amplitude",
            "JM Element a Phase (rad)",
            "JM Element b Phase (rad)",
            "JM Element c Phase (rad)",
            "JM Element d Phase (rad)",
            "Time (ns)",
            "Time Domain Amplitude (dB)",
            "Time Domain Wavelength (nm)",
            "Max Loss (dB)",
            "Min Loss (dB)",
            "Second Order PMD (ps^2)",
            "Phase Ripple Linear (rad)",
            "Phase Ripple Quadratic (rad)"
        ]

    def generate_plots(self):
        """Create HTML, CSV, MAT, PNG, PDF outputs"""
        
        # Determine save path
        if self.destination_dir == {}:
            path = os.path.join(".", "UserData", self.user, self.project, "OVA", self.name)
        else:
            path = self.destination_dir.get("dest_dir")
            path = os.path.join(path, "OVA", self.name)
        
        os.makedirs(path, exist_ok=True)
        
        # ========== HTML (Interactive Plotly with subplots) ==========
        try:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                subplot_titles=("Insertion Loss", "Group Delay"),
                vertical_spacing=0.12
            )
            
            # Top: Insertion Loss
            fig.add_trace(
                go.Scatter(x=self.wavelength, y=self.insertion_loss, 
                          mode='lines', name='Insertion Loss',
                          line=dict(color='#1f77b4', width=2)),
                row=1, col=1
            )
            
            # Bottom: Group Delay
            fig.add_trace(
                go.Scatter(x=self.wavelength, y=self.group_delay,
                          mode='lines', name='Group Delay',
                          line=dict(color='#ff7f0e', width=2)),
                row=2, col=1
            )
            
            fig.update_xaxes(title_text="Wavelength (nm)", row=2, col=1)
            fig.update_yaxes(title_text="Insertion Loss (dB)", row=1, col=1)
            fig.update_yaxes(title_text="Group Delay (ps)", row=2, col=1)
            
            fig.update_layout(height=700, showlegend=False, title_text="OVA Measurement")
            
            output_html = os.path.join(path, f"{self.filename}_{self.fileTime}.html")
            fig.write_html(output_html)
            print(f"Saved HTML: {output_html}")
        except Exception as e:
            print(f"Exception generating HTML plot: {e}")
            import traceback
            traceback.print_exc()
        
        # ========== CSV (ALL columns) ==========
        if self.file_format.get("csv", 0) == 1:
            try:
                # Convert wavelength and all 24 measurements to numpy arrays
                wavelength = np.asarray(self.wavelength)
                
                # Stack all measurements: first column = wavelength, then all 24 measurements
                # Shape will be (65536 rows, 25 columns)
                data_columns = [wavelength]
                for measurement in self.measurements:
                    data_columns.append(np.asarray(measurement))
                
                full_data = np.column_stack(data_columns)
                
                # Create DataFrame with proper column names
                df = pd.DataFrame(full_data, columns=self.column_names)
                output_csv = os.path.join(path, f"{self.filename}_{self.fileTime}.csv")
                df.to_csv(output_csv, index=False)
                print(f"Saved CSV with {full_data.shape[1]} columns x {full_data.shape[0]} rows: {output_csv}")
            except Exception as e:
                print(f"Exception saving CSV: {e}")
                import traceback
                traceback.print_exc()
        
        # ========== MAT (ALL data + metadata) ==========
        if self.file_format.get("mat", 0) == 1:
            try:
                # Build dictionary for MATLAB
                mat_dict = {
                    "wavelength_nm": np.asarray(self.wavelength),
                    "insertion_loss_db": np.asarray(self.insertion_loss),
                    "group_delay_ps": np.asarray(self.group_delay),
                }
                
                # Add all 24 measurement arrays with descriptive names
                for i, (measurement, col_name) in enumerate(zip(self.measurements, self.column_names[1:])):
                    # Create MATLAB-safe variable names (replace spaces/special chars with underscores)
                    safe_name = col_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
                    mat_dict[f"meas_{i:02d}_{safe_name}"] = np.asarray(measurement)
                
                # Add metadata
                mat_dict["column_labels"] = np.array(self.column_names, dtype=object)
                mat_dict["filename"] = self.filename
                mat_dict["fileTime"] = self.fileTime
                mat_dict["user"] = self.user
                mat_dict["project"] = self.project
                mat_dict["device_name"] = self.name
                
                if self.meta_data:
                    # Convert metadata dict to string for MATLAB compatibility
                    mat_dict["metadata"] = str(self.meta_data)
                
                output_mat = os.path.join(path, f"{self.filename}_{self.fileTime}.mat")
                savemat(output_mat, mat_dict)
                print(f"Saved MAT with {len(self.measurements)} measurement arrays: {output_mat}")
            except Exception as e:
                print(f"Exception saving MAT: {e}")
                import traceback
                traceback.print_exc()
        
        # ========== PNG/PDF (matplotlib) ==========
        try:
            fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
            
            # Top: Insertion Loss
            axes[0].plot(self.wavelength, self.insertion_loss, linewidth=1.5, color='#1f77b4')
            axes[0].set_ylabel("Insertion Loss (dB)", fontsize=12)
            axes[0].set_title("OVA Measurement", fontsize=14, fontweight='bold')
            axes[0].grid(True, alpha=0.3, linestyle='--')
            
            # Bottom: Group Delay
            axes[1].plot(self.wavelength, self.group_delay, linewidth=1.5, color='#ff7f0e')
            axes[1].set_xlabel("Wavelength (nm)", fontsize=12)
            axes[1].set_ylabel("Group Delay (ps)", fontsize=12)
            axes[1].grid(True, alpha=0.3, linestyle='--')
            
            plt.tight_layout()
            
            if self.file_format.get("png", 0) == 1:
                output_png = os.path.join(path, f"{self.filename}_{self.fileTime}.png")
                plt.savefig(output_png, dpi=300)
                print(f"Saved PNG: {output_png}")
                
                # Also save to ./res for GUI display
                res_png = os.path.join(".", "res", "ova_sweep", f"{self.filename}_{self.fileTime}.png")
                os.makedirs(os.path.dirname(res_png), exist_ok=True)
                plt.savefig(res_png, dpi=300)
            
            if self.file_format.get("pdf", 0) == 1:
                output_pdf = os.path.join(path, f"{self.filename}_{self.fileTime}.pdf")
                plt.savefig(output_pdf, dpi=300)
                print(f"Saved PDF: {output_pdf}")
            
            plt.close()
            
            # Update GUI reference for webview
            try:
                from GUI.lib_gui import File
                File("shared_memory", "Image", f"ova_sweep/{self.filename}_{self.fileTime}.png",
                     "Web", output_html).save()
            except ImportError:
                pass  # Skip if File class not available
        
        except Exception as e:
            print(f"Exception generating PNG/PDF: {e}")
            import traceback
            traceback.print_exc()

import sys
from multiprocessing import Event, Value
from ctypes import c_int
import time
import json
import os
from pathlib import Path

def reset_progress_file():
    """Initialize/clear the progress JSON so old runs don't show up."""
    try:
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "progress_percent": 0.0,
            "activity": "Starting task...",
            "eta_seconds": None,
        }
        with open(PROGRESS_PATH, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[Progress] Could not reset progress file: {e}")


def run_busy_dialog(done_val: Value, cancel_evt: Event, progress_config: dict = None):
    # print(f"[Dialog Process] Starting with PID {os.getpid()}")
    
    # Use simple tkinter instead of PyQt5
    try:
        import tkinter as tk
        from tkinter import ttk
        # print("[Dialog Process] Using tkinter for progress display")
        return _run_tkinter_progress(done_val, cancel_evt, progress_config)
    except Exception as e:
        print(f"[Dialog Process] Failed to create tkinter dialog: {e}")
        print("[Dialog Process] Falling back to console-based progress display...")
        return _run_console_progress(done_val, cancel_evt, progress_config)

def _run_tkinter_progress(done_val: Value, cancel_evt: Event, progress_config: dict = None):
    """Simple tkinter progress dialog"""
    import tkinter as tk
    from tkinter import ttk
    
    # print("[Progress Dialog] Creating progress dialog...")
    
    # 🔹 Reset progress so previous run's 100% doesn't flash
    reset_progress_file()
    
    root = tk.Tk()
    root.title("Process Progress")
    root.geometry("400x170")
    root.resizable(False, False)
    
    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 2
    root.geometry(f"+{x}+{y}")
    
    # Activity label
    activity_var = tk.StringVar(value="Starting task...")
    activity_label = tk.Label(root, textvariable=activity_var, font=("Arial", 10, "bold"))
    activity_label.pack(pady=10)
    
    # Progress bar
    progress_var = tk.DoubleVar(value=0.0)
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=350)
    progress_bar.pack(pady=5)
    
    # Percentage label
    percent_var = tk.StringVar(value="0.0%")
    percent_label = tk.Label(root, textvariable=percent_var)
    percent_label.pack(pady=2)
    
    # ETA label
    eta_var = tk.StringVar(value="ETA: --")
    eta_label = tk.Label(root, textvariable=eta_var)
    eta_label.pack(pady=2)
    
    def update_progress():
        if done_val.value == 1:
            progress_var.set(100)
            activity_var.set("Process completed!")
            percent_var.set("100%")
            eta_var.set("ETA: 0.0 s")
            root.after(1500, root.destroy)
            return

        try:
            if PROGRESS_PATH.exists():
                with open(PROGRESS_PATH, 'r') as f:
                    progress_data = json.load(f)
                
                progress = progress_data.get('progress_percent', 0.0)
                activity = progress_data.get('activity', 'In progress...')
                eta_seconds = progress_data.get('eta_seconds', None)
                
                progress_var.set(progress)
                activity_var.set(activity)
                percent_var.set(f"{progress:.1f}%")
                
                if eta_seconds is not None:
                    eta_var.set(f"ETA: {eta_seconds:.1f} s")
                else:
                    eta_var.set("ETA: --")
        except Exception as e:
            print(f"[Progress Dialog] Error reading progress: {e}")
        
        root.after(200, update_progress)
    
    def on_cancel():
        print("[Progress Dialog] Cancel requested")
        with done_val.get_lock():
            done_val.value = -1
        cancel_evt.set()
        root.destroy()
    
    cancel_btn = tk.Button(root, text="Cancel", command=on_cancel)
    cancel_btn.pack(pady=5)
    
    root.after(100, update_progress)
    
    # print("[Progress Dialog] Starting dialog event loop...")
    root.mainloop()
    # print("[Progress Dialog] Dialog closed")

def _run_console_progress(done_val: Value, cancel_evt: Event, progress_config: dict = None):
    """Console-based progress display when PyQt5 is not available"""
    # print("[Console Progress] Starting console progress monitor...")
    start_time = time.time()
    last_progress = -1
    
    while done_val.value != 1:
        try:
            # Read progress file
            if PROGRESS_PATH.exists():
                with open(PROGRESS_PATH, 'r') as f:
                    progress_data = json.load(f)
                
                progress = progress_data.get('progress_percent', 0)
                activity = progress_data.get('activity', 'In progress...')
                eta_seconds = progress_data.get('eta_seconds', None)
                
                # Only print updates when progress changes significantly
                if abs(progress - last_progress) > 5 or time.time() - start_time > 10:
                    elapsed = time.time() - start_time
                    eta_str = f", ETA: {eta_seconds:.1f}s" if eta_seconds is not None else ""
                    print(f"[Progress] {progress:.1f}% - {activity} (elapsed: {elapsed:.1f}s{eta_str})")
                    last_progress = progress
                    start_time = time.time()  # Reset timer after printing
            
            time.sleep(0.5)  # Check every 500ms
            
        except Exception as e:
            print(f"[Console Progress] Error reading progress: {e}")
            time.sleep(1.0)
    
    print("[Console Progress] Process completed!")
    time.sleep(2.0)  # Keep visible for 2 seconds after completion
