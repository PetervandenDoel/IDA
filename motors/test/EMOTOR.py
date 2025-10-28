from motors.elec.BSC203_controller import BSC203Motor
from motors.hal.motors_hal import AxisType
import asyncio
import time
import pyvisa as visa

rm = visa.ResourceManager()
print(rm.list_resources())

device = BSC203Motor(ser_port='7', axes=[AxisType.X,AxisType.Y,AxisType.Z])

ok = device.connect()

async def helper_func(coro, args=None):
    if args is None:
        ans = await coro()
    else:
        ans = await coro(*args)
    print(ans)
    return ans

if ok:
    print(ok)
    asyncio.run(helper_func(device.get_config))
    bok = device.home(AxisType.X)
    if bok:
        print("Device homed\n")
    # asyncio.run(helper_func(device.move_relative, (AxisType.Y,10,None)))
    print(device.get_position(axis=AxisType.X))
    aok = device.move_relative(AxisType.X, 100)
    asyncio.run(helper_func(device.get_config))
    if aok:
        time.sleep(1)
        print(device.get_position(axis=AxisType.X))
    else:
        raise
else:
    raise

bok = device.disconnect()
