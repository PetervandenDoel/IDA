from SMU.keithley2600_controller import Keithley2600BController
import pyvisa as visa
import time
from time import sleep


ctl = Keithley2600BController(visa_address='GPIB0::26::INSTR')
ok = ctl.connect()
if ok:
    print(f's:{ok}')
else:
    print(f'N:{ok}')
id = ctl.idn()
print(id)

# --- SETTERS ---
channels = ["A", "B"]

for ch in channels:
    ctl.set_source_mode("I", ch)
    ctl.set_current(0.001, ch)
    ctl.set_current_limit(0.01, ch)
    ctl.set_voltage(1.0, ch)
    ctl.set_voltage_limit(1.5, ch)
    ctl.set_power_limit(0.5, ch)
    ctl.output_on(ch)

# --- GETTERS ---
print("Current:", ctl.get_current())
print("Current Limits:", ctl.get_current_limits())
print("Voltage:", ctl.get_voltage())
print("Voltage Limits:", ctl.get_voltage_limits())
print("Resistance:", ctl.get_resistance())
print("Power Limits:", ctl.get_power_limits())
print("State:", ctl.get_state())

# Turn off outputs after test
for ch in channels:
    ctl.output_off(ch)


# Test iv sweep
start = 0
stop = 0.5
step = 0.1
ch = ["A"]
sweep_t = "voltage"

# result = ctl.iv_sweep(start=start,stop=stop,step=step,channel=ch,type=sweep_t)

# print("Sweep res: ")
# for v,i in zip(result["V"], result["I"]):
#     print(f"V = {v:.3f} | I = {i:.3f}")

# import matplotlib.pyplot as plt
# plt.plot(result["V"], result["I"])
# plt.xlabel("Voltage (V)")
# plt.ylabel("Current (A)")
# plt.title("IV Sweep")
# plt.grid(True)
# plt.show()
# ctl.disconnect()
# res = ctl.get_and_clear_errors()
# for r in res:
#     print(r)
# print("here")
# cmd = (
#     "local t={}; "
#     "for name in script.factory.catalog() do t[#t+1]=name end; "
#     'print(table.concat(t, ","))'
# )
# ctl.inst.write(cmd)
# sleep(0.5)
# # count = int(ctl.inst.read().strip())
# print([ctl.inst.read().strip() for _ in range(500)])
# resp = ctl.inst.read_raw()
# print([resp])
# ctl.inst.flush()
print('################ Chill #################')

# # Run a iv sweep
w = ctl.inst.write
# w(f'smua.source.func = smua.OUTPUT_DCVOLTS')
# w(f'smua.source.limiti = 0.01') # 10mA
# w(f'smua.nvbuffer1.clear()')
# pts = int(round((stop-start) / step))+1
# print(f"Start: {start} | Stop: {stop} | pts: {pts} | ss: {step}")
# print(f"Commencing Voltage sweep (o.1)")
# w(f'smua.nvbuffer1.capacity = {pts}')
# w(f'smua.nvbuffer1.appendmode = 1')
# w(f'smua.nvbuffer1.collectsourcevalues = 0')
# w(f'smua.measure.count = 1')
# nlpc = 0.1 # std
# w(f'smua.measure.nlpc = {nlpc}')
# w(f'smua.source.output = smua.OUTPUT_ON')
# w(f'SweepILinMeasureV(smua, {start}, {stop}, 0.1, {pts})')
# sleep(2)
# print("Working?")
# data = w(f'printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)')
# print([ctl.inst.read().strip() for _ in range(100)])
# print("test test test")
# src = ctl.inst.query("script.factory.scripts.KISweep.list()")
# print([a for a in src.strip().split(", ")])

# start = 0.0
# stop = 0.5
# step = 0.1
# pts = int(round((stop - start) / step)) + 1

# print('################ Chill #################')
# print(f"Start: {start} | Stop: {stop} | pts: {pts} | ss: {step}")
# print(f"Commencing Voltage sweep")

# w = ctl.inst.write
# q = ctl.inst.query
# ctl.inst.write("abort")
# ctl.inst.write("reset()")
# ctl.inst.write("display.clear()")
# ctl.inst.write("smua.reset()")
# ctl.inst.write("smua.source.output = smua.OUTPUT_OFF")
# ctl.get_and_clear_errors()
# # Setup
# w('smua.reset()')
# w('smua.source.func = smua.OUTPUT_DCVOLTS')
# w('smua.source.limiti = 0.01')  # 10 mA current limit
# w('smua.measure.count = 1')
# w('smua.measure.nplc = 0.1')
# w('smua.nvbuffer1.clear()')
# w('smua.nvbuffer1.appendmode = 1')
# w('smua.nvbuffer1.collectsourcevalues = 0')
# w('smua.source.output = smua.OUTPUT_ON')

# # Sweep using inline for-loop
# tsp = [
#     f'for x = {start}, {stop}, {step} do',
#     '  smua.source.levelv = x',
#     '  delay(0)',
#     '  smua.measure.i(smua.nvbuffer1)',
#     'end'
# ]
# for line in tsp:
#     w(line)
# count = q("print(smua.nvbuffer1.n)").strip()
# print(f"Yikes: {count}")
# # Data fetch
# w("format.data = format.REAL64")
# w("format.byteorder = format.LITTLEENDIAN")
# currents = ctl.inst.query_binary_values("printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)", datatype='d', container=list)

# voltages = [start + i*step for i in range(pts)]
# for v, i in zip(voltages, currents):
    # print(f"V = {v:.3f} V, I = {i:.6f} A")

# # w('smua.source.output = smua.OUTPUT_OFF')
# w('smua.nvbuffer1.clear()')
# w('smua.nvbuffer1.appendmode=1')
# w('smua.nvbuffer1.collectsourcevalues=1')
# w('smua.nvbuffer1.collecttimestamps=1')

# w('SweepVLinMeasureI(smua, 0.001, 1, 0.01, 51)')
# w('waitcomplete()')
# q = ctl.inst.query
# n = int(float(q('print(smua.nvbuffer1.n)')))
# i_csv = q('printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.readings)')
# v_csv = q('printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.sourcevalues)')
# t_csv = q('printbuffer(1, smua.nvbuffer1.n, smua.nvbuffer1.timestamps)')

# I = [float(x) for x in i_csv.strip().split(',') if x]
# V = [float(x) for x in v_csv.strip().split(',') if x]
# t = [float(x) for x in t_csv.strip().split(',') if x]

# for i in range(n):
#     print(f'{i}th row: I:{I[i]} | V:{V[i]} | t:{t[i]}')

res = ctl.iv_sweep(0.0,1.0,0.1,["A", "B"], 'Voltage', "LOG")
print(res)
res_n = ctl.iv_sweep_list([0.001, 0.01, 0.1, 0.5, 1], ["A"], 'Voltage')
print(res_n)
ctl.disconnect()