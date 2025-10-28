from motors.optical.ida_controller import CorvusController
from motors.hal.motors_hal import AxisType
import pyvisa as visa
import asyncio

rm = visa.ResourceManager()
print(rm.list_resources())

cx = CorvusController(
        axis=AxisType.X,
        enabled_axes=[AxisType.X, AxisType.Y, AxisType.Z],
        visa_address='ASRL7::INSTR')
cy = CorvusController(
        axis=AxisType.Y,
        enabled_axes=[AxisType.X, AxisType.Y, AxisType.Z],
        visa_address='ASRL7::INSTR')
cz = CorvusController(
        axis=AxisType.Z,
        enabled_axes=[AxisType.X, AxisType.Y, AxisType.Z],
        visa_address='ASRL7::INSTR',
        position_limits_um=(-16000,16000))

xok = asyncio.run(cx.connect())

if xok:
    print(f'Succesfully connected to cx: {cx.axis} | {xok}')
else:
    print(f'Tsk tsk tsk')


yok = asyncio.run(cy.connect())

if yok:
    print(f'Succesfully connected to: {cy.axis} | {yok}')
else:
    print(f'Tsk tsk tsk')

zok = asyncio.run(cz.connect())

if zok:
    print(f'Succesfully connected to: {cz.axis} | {zok}')
else:
    print(f'Tsk tsk tsk')

# print('Lets try moving the x-axis now...')
# print('Corvus does not support homing...')
# xmove = asyncio.run(cx.move_relative(distance=-5000))
# if xmove:
#     print(f'Successfully logged a movement: {xmove}')
# else:
#     print('Move rel failure for x axis')
# print('Lets try moving the y-axis now...')
# ymove = asyncio.run(cy.move_relative(distance=-5000))
# if ymove:
#     print(f'Successfully logged a movement: {ymove}')
# else:
#     print('Move rel failure for y axis')

# print('Lets try moving the z-axis now...')
# zmove = asyncio.run(cz.move_relative(distance=-500))
# if zmove:
#     print(f'Successfully logged a movement: {zmove}')
# else:
#     print('Move rel failure for x axis')
axs = [cx,cy,cz]

for ax in axs:
    print(asyncio.run(ax.get_position()))

# Z - (-15,000, 15,000)
# Z safe under [-15,000, 5,000] cannot hit stage here
asyncio.run(cz.move_absolute(-10000))

asyncio.run(cx.disconnect())
asyncio.run(cy.disconnect())
asyncio.run(cz.disconnect())
rm.close()