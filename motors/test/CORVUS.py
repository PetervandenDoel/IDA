from motors.optical.ida_controller import CorvusController
from motors.hal.motors_hal import AxisType
import pyvisa as visa
import asyncio
import time

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
        position_limits=(-16000,16000))

xok = asyncio.run(cx.connect())

if xok:
    print(f'Succesfully connected to cx: {cx.axis} | {xok}')
else:
    print(f'Tsk tsk tsk')

stri = (
    # '|||||||||||||||||||||||'
    f'X: {vars(cx)}\n'
    # '|||||||||||||||||||||||'
    f'Y: {vars(cy)}\n'
    # '|||||||||||||||||||||||'
    f'Y: {vars(cz)}\n'
    # '|||||||||||||||||||||||'
    )
# print(stri)
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

axs = [cx,cy,cz]

for ax in axs:
    print(asyncio.run(ax.get_position()))

# Z - (-15,000, 15,000)
# Z safe under [-15,000, 5,000] cannot hit stage here
# asyncio.run(cz.move_absolute(-10000))
asyncio.run(cx.move_relative(-1000))

time.sleep(2)
asyncio.run(cx.disconnect())
asyncio.run(cy.disconnect())
asyncio.run(cz.disconnect())
rm.close()