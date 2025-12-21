# from motors.optical.scylla_controller import ScyllaController
from motors.stage_manager import StageManager
from motors.config.stage_config import StageConfiguration
from motors.hal.motors_hal import AxisType
import asyncio
import time

cfg = StageConfiguration(
    driver_types= {
        AxisType.X: "scylla_controller",
        AxisType.Y: "scylla_controller",
        AxisType.Z: "scylla_controller",
        AxisType.ROTATION_CHIP: "scylla_controller",
        AxisType.ROTATION_FIBER: "scylla_controller",
    }
)
axes = list(cfg.driver_types.keys())
mng = StageManager(config=cfg)
ok = asyncio.run(mng.initialize_all([AxisType.ROTATION_CHIP]))
print(ok)
asyncio.run(mng.disconnect_all())

