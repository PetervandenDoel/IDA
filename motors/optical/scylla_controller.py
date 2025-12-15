import asyncio
from typing import Optional
from motors.hal.motors_hal import (
    MotorHAL, AxisType, MotorState, Position, MotorConfig, MotorEventType
)

import sys
sys.path.insert(0, r'C:\Users\mlpadmin\Documents\Github\SiEPIC\DreamsLab')
from dreamslab.drivers.motor import MLPMotor


"""
Very limited capabilites, must have access to a
computer with the Dreamslab repo on it as it 
contains IP not available for open source usage

Implements MotorHAL for Scylla controller with initialization 
and relative movement support.


Cameron Basara, 2025
"""


class ScyllaController(MotorHAL):
    """Scylla motor controller implementing relative movement only."""
    # Axis Mapping
    AXIS_MAP = {
        AxisType.X: 0,  # Chan 0
        AxisType.Y: 1,  # Chan 1
        AxisType.Z: 2
    }    

    def __init__(self, axis: AxisType, port: str):
        """
        Initialize Scylla controller.
        
        Args:
            axis: Axis type this controller manages
            port: Serial port path (e.g., '/dev/ttyUSB0')
        """
        super().__init__(axis)
        self.m = None  # Motor connection to call API
        self.port = port
        self._serial = None
        self._position = 0.0
        self._state = MotorState.IDLE
    
    # Initialization
    async def connect(self) -> bool:
        """Connect to Scylla controller."""
        try:
            # Init axis using API
            self.m = MLPMotor(chan=self.AXIS_MAP[self.axis])
            return True
        except Exception as e:
            return False
    
    async def disconnect(self) -> Optional[bool]:
        """Disconnect from controller."""
        # TODO: Close serial connection
        return True
    
    # Movement
    async def move_absolute(self, position: float, velocity: Optional[float] = None) -> bool:
        """Not implemented - Scylla uses relative moves only."""
        raise NotImplementedError("Scylla controller only supports relative moves")
    
    async def move_relative(self, distance: float, velocity: Optional[float] = None) -> bool:
        """
        Execute relative move.
        
        Args:
            distance: Distance to move in current units
            velocity: Optional velocity override
            
        Returns:
            True if move command accepted
        """
        # For now, call MLP API
        self.m.move(distance=distance)
        return True
    
    async def stop(self) -> bool:
        """Stop current movement."""
        # TODO: Send stop command
        self._state = MotorState.STOPPED
        self._emit_event(MotorEventType.MOVE_STOPPED)
        return True
    
    async def emergency_stop(self) -> bool:
        """Emergency stop - fastest possible halt."""
        # TODO: Send emergency stop command
        return await self.stop()
    
    # Status
    async def get_position(self) -> Position:
        """Get current position."""
        # TODO: Query actual position from controller
        return Position(
            theoretical=self._position,
            actual=self._position,
            units="um",
            timestamp=asyncio.get_event_loop().time()
        )
    
    async def get_state(self) -> MotorState:
        """Get controller state."""
        # TODO: Query actual state from controller
        return self._state
    
    async def is_moving(self) -> bool:
        """Check if motor is moving."""
        return self._state == MotorState.MOVING
    
    # Configuration
    async def set_velocity(self, velocity: float) -> bool:
        """Set movement velocity."""
        # TODO: Send velocity command
        return True
    
    async def set_acceleration(self, acceleration: float) -> bool:
        """Set acceleration."""
        # TODO: Send acceleration command
        return True
    
    async def get_config(self) -> MotorConfig:
        """Get motor configuration."""
        # TODO: Return actual config from controller
        return MotorConfig(
            max_velocity=1000.0,
            max_acceleration=500.0,
            position_limits=(-10000.0, 10000.0),
            units="um",
            step_size_x=0.1,
            step_size_y=0.1,
            step_size_z=0.1,
            step_size_fr=0.01,
            step_size_cr=0.01
        )
    
    # Homing
    async def home(self, direction: int = 0) -> bool:
        """Not implemented - Scylla uses relative positioning."""
        raise NotImplementedError("Scylla does not support homing")
    
    async def home_limits(self) -> bool:
        """Not implemented."""
        raise NotImplementedError("Scylla does not support limit homing")
    
    async def set_zero(self) -> bool:
        """Set current position as zero."""
        # TODO: Send zero command or reset internal tracking
        self._position = 0.0
        return True
    
# Register driver
from motors.hal.stage_factory import register_driver
register_driver("scylla_controller", ScyllaController)