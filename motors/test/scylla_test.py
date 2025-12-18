from motors.optical.scylla_controller import ScyllaController
from motors.hal.motors_hal import AxisType
import asyncio
import time

sc = ScyllaController(axis=AxisType.ROTATION_FIBER)
# sc = ScyllaController(axis=AxisType.X)
aok = asyncio.run(sc.connect())
if aok:
    print('Hello')
else:
    print('Goodbye')
asyncio.run(sc.get_position())
asyncio.run(sc.move_relative(10))
time.sleep(2)
asyncio.run(sc.get_position())
bok = asyncio.run(sc.disconnect())
if bok:
    print('Goodbye')
else:
    print('Hello')


# trial = 1
# # Connection
# sc = ScyllaController(axis=AxisType.X)
# aok = asyncio.run(sc.connect())
# if aok:
#     print('Hello')
# else:
#     print('Goodbye')
# print(f'{trial}\n')
# trial += 1
# asyncio.run(sc.get_position())
# c = 1
# for i in range(100, 1000, 100):
#     asyncio.run(sc.move_relative(c*i))
#     c*=-1
# print(f'{trial}\n')
# trial += 1
# asyncio.run(sc.get_position())
# bok = asyncio.run(sc.disconnect())
# if bok:
#     print('Goodbye')
# else:
#     print('Hello')

# # Connection
# sc = ScyllaController(axis=AxisType.Y)
# aok = asyncio.run(sc.connect())
# if aok:
#     print('Hello 2')
# else:
#     print('Goodbye 2')
# print(f'{trial}\n')
# trial += 1
# asyncio.run(sc.get_position())
# asyncio.run(sc.move_relative(100))
# print(f'{trial}\n')
# trial += 1
# asyncio.run(sc.get_position())
# c = 1
# for i in range(100, 1000, 100):
#     asyncio.run(sc.move_relative(c*i))
#     c*=-1
# print(f'{trial}\n')
# trial += 1
# asyncio.run(sc.get_position())
# bok = asyncio.run(sc.disconnect())
# if bok:
#     print('Goodbye 2')
# else:
#     print('Hello 2')

# print(f'{trial}\n')
# trial += 1
# asyncio.run(sc.get_position())