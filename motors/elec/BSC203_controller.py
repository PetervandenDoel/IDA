from thorlabs_apt_device import BSC, list_devices
import re
from typing import Optional, Dict, Tuple, List
from time import monotonic
from motors.hal.motors_hal import MotorHAL, AxisType, Position


"""
Reimplementation of the BSC203 motor controller from PyOptomip:

https://github.com/SiEPIC/SiEPIClab/blob/master/pyOptomip/BSC203.py

To Fit HAL

Cameron Basara, 2025
"""

class BSC203Motor(MotorHAL):
    """
    BSC20x motor controller class
    where x e {0,1,2,3,4,5,6} representing the number of 
    controllable axis.

    Implementation specified for the BSC203, but works
    for any BSC20x device. 
    """

    # Controller bays are zero-based: X->0, Y->1, Z->2
    AXIS_MAP = {
        AxisType.X: 0,
        AxisType.Y: 1,
        AxisType.Z: 2,
        "AxisType.X": 0,
        "AxisType.Y": 1,
        "AxisType.Z": 2,
    }

    def __init__(self, ser_port: str, axes: List[AxisType]):
        super().__init__(axis=AxisType.ALL)
        assert 0 < len(axes) <= 3, "BSC203 supports 1-3 axes"
        self.ser_port = ser_port
        self.axes = axes

        self.inst: Optional[BSC] = None

        # Cached positions in um 
        self._position: Dict[AxisType, float] = {ax: 0.0 for ax in axes}
        # Homed flags per axis
        self._homed: Dict[AxisType, bool] = {ax: False for ax in axes}
        # Software limits per axis: (lo, hi). None means "no limit set"
        self._limits: Dict[AxisType, Optional[Tuple[float, float]]] = {ax: None for ax in axes}

    
    ########################################################################################
    #  DRV208 on NanoMax300
    #  Needs to be tuned and configured before the movement is usable
    #  Documentation:
    # https://oxxius.ru/upload/iblock/325/xkqz5fo2dl93978eq6rhbhbhusf7e2ik/ETN043208_D02.pdf
    #
    ########################################################################################
    
    # --- Connection ---

    def connect(self) -> bool:
        try:
            numbers = re.findall(r"[0-9]+", self.ser_port)
            com_port = "COM" + numbers[0]
            self.inst = BSC(serial_port=com_port, x=len(self.axes), serial_number=70317904, home=False)
            print(self.inst, "\n", type(self.inst), "\n", self.inst.__init__)
            self.inst.identify()
            print('Listing devices. . .')
            print(list_devices())
            print('\n')
            return True
        except Exception as e:
            print(f"[BSC203] Connection failed: {e}")
            self.inst = None
            return False

    def disconnect(self) -> bool:
        try:
            if self.inst:
                self.inst.close()
                self.inst = None
            return True
        except Exception as e:
            print(f"[BSC203] Disconnection failed: {e}")
            return False

    # --- Helpers ---

    def _bay(self, axis: AxisType) -> int:
        if axis not in self.axes:
            raise ValueError(f"Axis {axis} not initialized on this controller.")
        return self.AXIS_MAP[axis]

    def _within_limits(self, axis: AxisType, target_um: float) -> bool:
        lim = self._limits[axis]
        if lim is None:
            return True
        lo, hi = lim
        if target_um < lo or target_um > hi:
            print(f"[BSC203] Blocked: {axis.name} target {target_um} um out of limits {lo}..{hi} um")
            return False
        return True

    # --- Movement ---

    def move_relative(self, axis: AxisType, distance: float, velocity: Optional[float] = None) -> bool:
        """
        Relative move by distance (um). Checks (current + distance) against limits.
        """
        if not self.inst:
            raise RuntimeError("Controller not connected")

        bay = self._bay(axis)
        dest_um = self._position[axis].actual + distance
        if not self._within_limits(axis, dest_um):
            return False

        try:
            self.inst.move_relative(distance=int(distance * 1000), bay=bay, channel=0)
            self._position[axis] = Position(dest_um,dest_um,'um',monotonic)
            return True
        except Exception as e:
            print(f"[BSC203] move_relative({axis.name}) failed: {e}")
            return False

    def move_absolute(self, axis: AxisType, position: float, velocity: Optional[float] = None) -> bool:
        """
        Absolute move to position (um). Checks against limits.
        """
        if not self.inst:
            raise RuntimeError("Controller not connected")

        bay = self._bay(axis)
        if not self._within_limits(axis, position):
            return False

        try:
            self.inst.move_absolute(position=int(position * 1000), bay=bay, channel=0)
            self._position[axis] = position
            return True
        except Exception as e:
            print(f"[BSC203] move_absolute({axis.name}) failed: {e}")
            return False

    def stop(self, axis: AxisType) -> bool:
        """Stop given axis"""
        if not self.inst:
            return False
        bay = self._bay(axis)
        try:
            self.inst.stop(bay=bay, channel=0)
            return True
        except Exception as e:
            print(f"[BSC203] stop failed: {e}")
            return False

    def emergency_stop(self) -> bool:
        """Emergency stop all axis"""
        if not self.inst:
            return False
        try:
            for ax in self.axes:
                bay = self._bay(ax)
                self.inst.stop(immediate=True, bay=bay, channel=0)
            return True
        except Exception as e:
            print(f"[BSC203] stop failed: {e}")
            return False
     
    # --- Configuration ---
    async def get_config(self):
        """
        Retrieve config for all axis
        """
        if not self.inst:
            return False
        try:
            config = {}
            for ax in self.axes:
                bay = self._bay(ax)
                config[ax] = self.inst.status_[bay][0]
            return config
        except Exception as e:
            print(f"[BSC20x] get_config error: {e}")
            return None
        
    # Position
    def get_position(self, axis: AxisType) -> Optional[Position]:
        """
        Return current position in um.
        """
        if not self.inst:
            raise RuntimeError("Controller not connected")

        bay = self._bay(axis)
        try:
            # Get position from status dict
            pos = self.inst.status_[bay][0]["position"]
            self._position[axis] = Position(pos,pos,'um',monotonic())
            return self._position[axis]
        except Exception as e:
            # keep cached
            print(f"[BSC203] get_position error: {e}")
            return None
   
    # Movement config
    async def set_velocity(self, axis: AxisType, velocity:float):
        raise NotImplementedError
    async def set_acceleration(self, acceleration):
        return NotImplementedError
    async def get_state(self):
        raise NotImplementedError
    async def is_moving(self):
        raise NotImplementedError

    # --- Homing & Limits ---

    def home(self, axis: AxisType, direction: int = 0) -> bool:
        """
        Home an axis (drive to limit switch then zero).
        """
        if not self.inst:
            raise RuntimeError("Controller not connected")

        bay = self._bay(axis)
        try:
            self.inst.home(bay=bay, channel=0)
            self._position[axis] = 0.0
            self._homed[axis] = True
            return True
        except Exception as e:
            print(f"[BSC203] home({axis.name}) failed: {e}")
            return False

    def home_limits(self) -> bool:
        """
        Placeholder for full limit characterization. If you later add an API to
        probe negative/positive ends and measure travel, set per-axis limits here.
        """
        return True

    def set_zero(self, axis: AxisType) -> bool:
        """Set current position as zero (software)."""
        self._position[axis] = 0.0
        return True

    # Software limits 

    def set_limits(self, axis: AxisType, lo_um: Optional[float], hi_um: Optional[float]) -> None:
        """
        Set (lo, hi) in um for software travel limits. Use None,None to clear.
        """
        if lo_um is None or hi_um is None:
            self._limits[axis] = None
        else:
            if hi_um < lo_um:
                raise ValueError("hi_um must be >= lo_um")
            self._limits[axis] = (float(lo_um), float(hi_um))

    def get_limits(self, axis: AxisType) -> Optional[Tuple[float, float]]:
        """Return (lo, hi) in um, or None if not set."""
        return self._limits[axis]

    def at_min_limit(self, axis: AxisType) -> bool:
        lim = self._limits[axis]
        return lim is not None and self._position[axis] <= lim[0]

    def at_max_limit(self, axis: AxisType) -> bool:
        lim = self._limits[axis]
        return lim is not None and self._position[axis] >= lim[1]

from motors.hal.emotor_factory import register_driver
register_driver("BSC203_emotor", BSC203Motor)
