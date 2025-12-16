from NIR.Luna.luna_controller import LunaController
import pyvisa as visa


luna = LunaController()

iplst = ['137.82.94.91']
port='1'

lna.connect(iplst[0], port)

