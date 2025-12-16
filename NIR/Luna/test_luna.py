from NIR.Luna.Luna_instr import Luna
import pyvisa as visa

rm = visa.ResourceManager()
# print(rm.list_resources())

lna = Luna()

iplst = ['137.82.94.91']
port='1'

lna.connect(iplst[0], port)

