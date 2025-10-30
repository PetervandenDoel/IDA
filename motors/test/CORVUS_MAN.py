from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration
from motors.hal.motors_hal import AxisType
import asyncio

# Stage config creation
cfg = StageConfiguration()

cfg.driver_types = {
    AxisType.X: "Corvus_controller",
    AxisType.Y: "Corvus_controller",
    AxisType.Z: "Corvus_controller",
    AxisType.ROTATION_FIBER: "Corvus_controller",
    AxisType.ROTATION_CHIP: "Corvus_controller"
}
cfg.velocities = {
    AxisType.X: 5000,
    AxisType.Y: 5000,
    AxisType.Z: 5000,
    AxisType.ROTATION_FIBER: 5000,
    AxisType.ROTATION_CHIP: 5000
}
cfg.accelerations = {
    AxisType.X: 500,
    AxisType.Y: 500,
    AxisType.Z: 500,
    AxisType.ROTATION_FIBER: 500,
    AxisType.ROTATION_CHIP: 500
}
cfg.position_limits = {
    AxisType.X: (-30000,30000),
    AxisType.Y: (-30000,30000),
    AxisType.Z: (-16000,16000),
    AxisType.ROTATION_FIBER: (5000,5000),
    AxisType.ROTATION_CHIP: (5000, 5000)
}
cfg.visa_addr = 'ASRL7::INSTR'

print(cfg.get_axis_attributes())

# Manager instance
sm = StageManager(cfg,create_shm=False)
# all_ax = [AxisType.X, AxisType.Y, AxisType.Z, AxisType.ROTATION_CHIP, AxisType.ROTATION_FIBER]
# asyncio.run(sm.initialize_all(all_ax))
asyncio.run(sm.initialize_axis(AxisType.X))
asyncio.run(sm.initialize_axis(AxisType.Y))
asyncio.run(sm.initialize_axis(AxisType.Z))
# print(asyncio.run(sm.get_all_positions()))

all = [AxisType.X, AxisType.Y]
for ax in all:
    for i in range(2):
        asyncio.run(sm.move_axis(ax,(1000*(-1)**(i%2)),True))
# asyncio.run(sm.motors[AxisType.X].move_relative(3000))
sm.motors[AxisType.X]._write('0.000000 -1000.000000 0.000000 r')
print(asyncio.run(sm.get_all_positions()))
asyncio.run(sm.disconnect_all())