import asyncio
import time
from typing import Optional, Dict, Tuple

import pyvisa as visa

from motors.hal.motors_hal import (
    MotorHAL, AxisType, MotorState, Position, MotorConfig, MotorEventType
)

"""
Reimplementation of the CorvusEco motor controller from PyOptomip:
https://github.com/SiEPIC/SiEPIClab/blob/master/pyOptomip/CorvusEco.py

To fit HAL interface while preserving legacy command semantics.

**Credit to original author**
@author: Stephen Lin
Last updated: July 15, 2014

Cameron Basara, 2025
"""

class CorvusEcoController(MotorHAL):
    """
    Stage controller for ITL09 Corvus Eco multi-axis controller.
    
    This controller manages up to 3 axes (X, Y, Z) simultaneously.
    """
    
    AXIS_MAPPING = {
        AxisType.X: 1,
        AxisType.Y: 2,
        AxisType.Z: 3,
    }

    def __init__(
        self,
        axis: list[AxisType],
        visa_address: str,
        velocity_um_s: float = 5000.0,
        acceleration_um_s2: float = 20000.0,
        position_limits_um: Tuple[float, float] = (-50000.0, 50000.0),
        step_size: Optional[Dict[str, float]] = None,
        status_poll_interval: float = 0.05,
        enable_closed_loop: bool = True,
        resource_manager: Optional[visa.ResourceManager] = None,
    ):
        """
        Initialize Corvus HAL interface.
        
        Args:
            axis: List of axes to control (e.g., [AxisType.X, AxisType.Y, AxisType.Z])
            visa_address: VISA resource string (e.g. 'ASRL3::INSTR')
            velocity_um_s: Default velocity in um/s
            acceleration_um_s2: Default acceleration in um/s2
            position_limits_um: Software limits (min, max) in um
            step_size: Step sizes for each axis (optional)
            status_poll_interval: Polling period for motion status (seconds)
            enable_closed_loop: Enable encoder closed-loop control
            resource_manager: Existing VISA RM to reuse (optional)
        """
        # Validate axes
        for ax in axis:
            if ax not in (AxisType.X, AxisType.Y, AxisType.Z):
                raise ValueError(f"CorvusEco supports X/Y/Z only, got {ax}")
        
        if not 1 <= len(axis) <= 3:
            raise ValueError(f"CorvusEco requires 1-3 axes, got {len(axis)}")
        
        # Store first axis for HAL compatibility, but track all
        super().__init__(axis[0])
        self._axes = axis
        self._num_axes = len(axis)

        # Configuration
        self._addr = visa_address
        self._vel = float(velocity_um_s)
        self._acc = float(acceleration_um_s2)
        self._limits = position_limits_um
        self._poll_dt = status_poll_interval
        self._closed_loop = enable_closed_loop
        
        # Step sizes with defaults
        default_steps = {
            "step_size_x": 1.0,
            "step_size_y": 1.0,
            "step_size_z": 1.0,
            "step_size_fr": 0.1,  # N/A
            "step_size_cr": 0.1   # N/A
        }
        if step_size:
            default_steps.update(step_size)
        self._step = default_steps

        # IO/State
        self._external_rm = resource_manager
        self._rm: Optional[visa.ResourceManager] = None
        self._inst = None
        self._connected = False
        
        # Position tracking for all 3 axes (even if not enabled)
        self._position_um = [0.0, 0.0, 0.0]
        self._move_in_progress = False

    # --- Low-level I/O helpers ---
    def _write(self, cmd: str) -> None:
        if not self._inst:
            raise RuntimeError("Not connected")
        self._inst.write(cmd)

    def _query(self, cmd: str) -> str:
        if not self._inst:
            raise RuntimeError("Not connected")
        return self._inst.query(cmd)

    def _read(self) -> str:
        if not self._inst:
            raise RuntimeError("Not connected")
        return self._inst.read()

    def _get_error(self) -> str:
        """Get error code from controller (legacy showErr)."""
        try:
            self._write('ge')
            error_code = self._read().strip()
            return f"Error Code: {error_code} (Refer to Manual Page 165)"
        except Exception as e:
            return f"Failed to retrieve error: {e}"

    def _build_triplet(self, **axis_values) -> str:
        """
        Build position triplet string for Corvus commands.
        
        Args:
            axis_values: Keyword args like x=10.0, y=5.0, z=0.0
            
        Returns:
            String like "10.000000 5.000000 0.000000"
        """
        triplet = [
            axis_values.get('x', 0.0),
            axis_values.get('y', 0.0),
            axis_values.get('z', 0.0)
        ]
        return f"{triplet[0]:.6f} {triplet[1]:.6f} {triplet[2]:.6f}"

    # --- Initialization ---

    async def connect(self) -> bool:
        """
        Connect to Corvus controller.
        """
        try:
            # Use external RM if provided, else create new one
            self._rm = self._external_rm or visa.ResourceManager()
            
            # Open resource
            self._inst = self._rm.open_resource(self._addr)
            
            try:
                self._inst.baud_rate = 57600
            except Exception:
                pass
            self._write('identify')
            try:
                id_response = self._read()
                print(f"[CorvusEco] Connected: {id_response.strip()}")
            except Exception:
                print("[CorvusEco] Identify command sent")

            # Set dimension and enable axes
            self._write(f'{self._num_axes} setdim')
            
            # Enable/disable each axis
            all_axes = [AxisType.X, AxisType.Y, AxisType.Z]
            enabled_set = set(self._axes)
            for axis_type in all_axes:
                axis_num = self.AXIS_MAPPING[axis_type]
                enable = 1 if axis_type in enabled_set else 0
                self._write(f'{enable} {axis_num} setaxis')
            
            print(f"[CorvusEco] Enabled {self._num_axes} axis/axes: {[ax.name for ax in self._axes]}")

            # Set units to microns for virtual axis (0) and all physical axes (1-3)
            for axis_num in range(0, 4):
                self._write(f'1 {axis_num} setunit')
            print("[CorvusEco] Units set to microns (um)")

            # Set acceleration function to 0 (no special accel curve)
            self._write('0 setaccelfunc')

            # Set output port
            self._write('1 setout')

            # Set trigger out
            # out trig [time][polarity][output]
            self._write('10 0 1 ot')


            # Enable closed-loop if requested
            if self._closed_loop:
                for axis_num in range(1, self._num_axes + 1):
                    self._write(f'1 {axis_num} setcloop')
                print("[CorvusEco] Closed-loop enabled")

            # Set initial velocity and acceleration
            self._write(f'{self._vel:.6f} sv')
            self._write(f'{self._acc:.6f} sa')
            
            # Optional: read back values
            try:
                vel_readback = self._query('gv').strip()
                acc_readback = self._query('ga').strip()
                print(f"[CorvusEco] Velocity: {vel_readback} um/s, Acceleration: {acc_readback} um/s2")
            except Exception:
                pass

            self._connected = True
            return True

        except Exception as e:
            print(f"[CorvusEco] Connection failed: {e}")
            if self._inst:
                try:
                    self._inst.close()
                except Exception:
                    pass
            if self._rm and not self._external_rm:
                try:
                    self._rm.close()
                except Exception:
                    pass
            return False

    async def disconnect(self) -> Optional[bool]:
        """Disconnect from controller."""
        try:
            if self._inst:
                self._inst.close()
                print("[CorvusEco] Disconnected")
            
            if self._rm and not self._external_rm:
                try:
                    self._rm.close()
                except Exception:
                    pass
            
            self._connected = False
            return True
        except Exception as e:
            print(f"[CorvusEco] Disconnect error: {e}")
            return False

    async def move_absolute(self, position: float, velocity: Optional[float] = None) -> bool:
        """Move to absolute position (converts to relative move)."""
        current_pos = await self.get_position()
        delta = position - current_pos.actual
        return await self.move_relative(delta, velocity)

    async def move_relative(self, distance: float, velocity: Optional[float] = None) -> bool:
        """
        Perform relative move on primary axis.
        
        Constructs triplet command "x y z r" with movement only on the primary axis.
        """
        try:
            # Determine which axis to move
            axis_idx = self.AXIS_MAPPING[self.axis]
            current = self._position_um[axis_idx]
            target = current + distance

            # Enforce software limits
            lo, hi = self._limits
            if not (lo <= target <= hi):
                error_msg = f"Move to {target:.2f} um violates limits [{lo}, {hi}]"
                self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
                return False

            # Override velocity if specified
            if velocity is not None:
                self._write(f'{velocity:.6f} sv')

            self._emit_event(MotorEventType.MOVE_STARTED, {
                "axis": self.axis.name,
                "distance_um": distance,
                "target_um": target
            })

            self._move_in_progress = True

            # Build triplet command with movement only on the specified axis
            kwargs = {['x', 'y', 'z'][axis_idx]: distance}
            cmd = f"{self._build_triplet(**kwargs)} r"
            self._write(cmd)

            # Wait for move completion
            start_time = time.time()
            timeout = 60.0
            
            while True:
                try:
                    status = self._query('st').strip()
                    moving = (int(status) & 1) == 1
                    if not moving:
                        break
                except Exception:
                    # Fallback: check if we're within settle band
                    try:
                        positions = self._read_position_triplet()
                        if abs(positions[axis_idx] - target) <= 0.5:
                            break
                    except Exception:
                        pass
                
                if time.time() - start_time > timeout:
                    error_msg = f"Move timeout after {timeout}s"
                    self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
                    self._move_in_progress = False
                    return False
                
                await asyncio.sleep(self._poll_dt)

            # Update position tracker
            self._position_um[axis_idx] = target

            self._move_in_progress = False
            self._emit_event(MotorEventType.MOVE_COMPLETE, {"position_um": target})
            
            return True

        except Exception as e:
            error_msg = f"Move failed: {e}\n{self._get_error()}"
            print(f"[CorvusEco] {error_msg}")
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
            self._move_in_progress = False
            return False

    async def move_multi_axis(self, distances: Dict[AxisType, float], velocity: Optional[float] = None) -> bool:
        """
        Move multiple axes simultaneously.
        
        Args:
            distances: Dict mapping AxisType to distance (e.g., {AxisType.X: 10.0, AxisType.Y: 5.0})
            velocity: Optional velocity override
            
        Returns:
            True if successful
        """
        try:
            # Build movement dict
            move_kwargs = {}
            targets = {}
            
            for axis_type, distance in distances.items():
                if axis_type not in self._axes:
                    print(f"[CorvusEco] Warning: {axis_type.name} not enabled, skipping")
                    continue
                
                axis_idx = self.AXIS_MAPPING[axis_type]
                axis_name = ['x', 'y', 'z'][axis_idx]
                
                current = self._position_um[axis_idx]
                target = current + distance
                
                # Check limits
                lo, hi = self._limits
                if not (lo <= target <= hi):
                    error_msg = f"{axis_type.name} move to {target:.2f} um violates limits [{lo}, {hi}]"
                    self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
                    return False
                
                move_kwargs[axis_name] = distance
                targets[axis_idx] = target

            if not move_kwargs:
                return True  # Nothing to move

            # Override velocity if specified
            if velocity is not None:
                self._write(f'{velocity:.6f} sv')

            self._emit_event(MotorEventType.MOVE_STARTED, {
                "axes": list(distances.keys()),
                "distances_um": distances,
                "targets_um": targets
            })

            self._move_in_progress = True

            # Execute coordinated move
            cmd = f"{self._build_triplet(**move_kwargs)} r"
            self._write(cmd)

            # Wait for completion
            start_time = time.time()
            timeout = 60.0
            
            while True:
                try:
                    status = self._query('st').strip()
                    moving = (int(status) & 1) == 1
                    if not moving:
                        break
                except Exception:
                    break
                
                if time.time() - start_time > timeout:
                    self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": "Move timeout"})
                    self._move_in_progress = False
                    return False
                
                await asyncio.sleep(self._poll_dt)

            # Update positions
            for axis_idx, target in targets.items():
                self._position_um[axis_idx] = target

            self._move_in_progress = False
            self._emit_event(MotorEventType.MOVE_COMPLETE, {"targets_um": targets})
            
            return True

        except Exception as e:
            error_msg = f"Multi-axis move failed: {e}\n{self._get_error()}"
            print(f"[CorvusEco] {error_msg}")
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": error_msg})
            self._move_in_progress = False
            return False

    async def stop(self) -> bool:
        """Stop motion immediately."""
        try:
            # Decelerate to zero velocity
            self._write('0 sv')
            
            # Restore original velocity
            await asyncio.sleep(0.1)
            self._write(f'{self._vel:.6f} sv')
            
            self._move_in_progress = False
            self._emit_event(MotorEventType.MOVE_STOPPED, {})
            return True
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": f"Stop failed: {e}"})
            return False

    async def emergency_stop(self) -> bool:
        """Emergency stop."""
        return await self.stop()

    async def get_position(self) -> Position:
        """Query current position for the primary axis."""
        try:
            positions = self._read_position_triplet()
            self._position_um = positions
            
            axis_idx = self.AXIS_MAPPING[self.axis]
            actual = positions[axis_idx]
            
            return Position(
                theoretical=actual,
                actual=actual,
                units="um",
                timestamp=time.time()
            )
        except Exception as e:
            print(f"[CorvusEco] get_position error: {e}")
            axis_idx = self.AXIS_MAPPING[self.axis]
            cached = self._position_um[axis_idx]
            return Position(cached, cached, "um", time.time())

    async def get_all_positions(self) -> Dict[AxisType, float]:
        """Get positions for all enabled axes."""
        try:
            positions = self._read_position_triplet()
            self._position_um = positions
            
            result = {}
            for axis_type in self._axes:
                axis_idx = self.AXIS_MAPPING[axis_type]
                result[axis_type] = positions[axis_idx]
            
            return result
        except Exception as e:
            print(f"[CorvusEco] get_all_positions error: {e}")
            return {ax: self._position_um[self.AXIS_MAPPING[ax]] for ax in self._axes}

    def _read_position_triplet(self) -> list[float]:
        """Read position triplet from controller. Returns [x, y, z] in microns."""
        self._write('pos')
        response = self._read().strip()
        values = list(map(float, response.split()))
        
        # Pad with zeros if needed
        while len(values) < 3:
            values.append(0.0)
        
        return values[:3]

    async def get_state(self) -> MotorState:
        """Query motion state."""
        try:
            status = self._query('st').strip()
            moving = (int(status) & 1) == 1
            return MotorState.MOVING if moving else MotorState.IDLE
        except Exception:
            return MotorState.MOVING if self._move_in_progress else MotorState.IDLE

    async def is_moving(self) -> bool:
        """Check if motor is moving."""
        return (await self.get_state()) == MotorState.MOVING

    async def set_velocity(self, velocity: float) -> bool:
        """Set velocity for all axes (global setting)."""
        try:
            self._write(f'{velocity:.6f} sv')
            self._vel = velocity
            return True
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": f"set_velocity failed: {e}"})
            return False

    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration for all axes (global setting)."""
        try:
            self._write(f'{acceleration:.6f} sa')
            self._acc = acceleration
            return True
        except Exception as e:
            self._emit_event(MotorEventType.ERROR_OCCURRED, {"error": f"set_acceleration failed: {e}"})
            return False

    async def get_config(self) -> MotorConfig:
        """Return current motor configuration."""
        return MotorConfig(
            max_velocity=self._vel,
            max_acceleration=self._acc,
            position_limits=self._limits,
            units="um",
            **self._step
        )

    async def home(self, direction: int = 0) -> bool:
        """
        Home the axis.
        
        Not implemented - Corvus Eco controller does not provide a standard
        homing command in the command set.
        """
        print("[CorvusEco] Homing not supported by Corvus Eco hardware")
        raise NotImplementedError(
            "Corvus Eco controller does not provide homing commands. "
            "Manual homing or physical limit switches may be required."
        )

    async def home_limits(self) -> bool:
        """
        Home to limits.
        
        Not implemented - Corvus Eco controller does not provide limit
        homing functionality.
        """
        print("[CorvusEco] Limit homing not supported by Corvus Eco hardware")
        raise NotImplementedError(
            "Corvus Eco controller does not provide limit homing. "
            "Use manual positioning or external limit detection."
        )

    async def set_zero(self) -> bool:
        """Set current position as zero (software only)."""
        axis_idx = self.AXIS_MAPPING[self.axis]
        self._position_um[axis_idx] = 0.0
        print(f"[CorvusEco] Zero position set for {self.axis.name}")
        return True

    async def set_zero_all(self) -> bool:
        """Set all axis positions to zero (software only)."""
        self._position_um = [0.0, 0.0, 0.0]
        print("[CorvusEco] All positions zeroed")
        return True


# Register driver with factory
from motors.hal.stage_factory import register_driver
register_driver("CorvusEco_controller", CorvusEcoController)