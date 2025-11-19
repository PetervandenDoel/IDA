import pyvisa
import time

rm = pyvisa.ResourceManager()
inst = rm.open_resource("GPIB0::20::INSTR")

inst.write_termination = "\n"
inst.read_termination  = "\n"
inst.timeout = 30000

print("=== Connected ===")

# ---------------------------------------------------------
# 1. Basic IDN
# ---------------------------------------------------------
try:
    print("*IDN? ->", inst.query("*IDN?"))
except Exception as e:
    print("IDN FAILED:", e)

# ---------------------------------------------------------
# # 2. CLS
# # ---------------------------------------------------------
# print("\n-- *CLS --")
# try:
#     inst.write("*CLS")
#     print("CLS OK")
# except Exception as e:
#     print("CLS FAILED:", e)

# try:
#     print("SYST:ERR? ->", inst.query("SYST:ERR?"))
# except Exception as e:
#     print("SYST:ERR? FAILED:", e)

# ---------------------------------------------------------
# 3. POWER
# ---------------------------------------------------------
print("\n-- SOUR0:POW -1 --")
try:
    inst.write("SOUR0:POW 1")
    print("POW OK")
except Exception as e:
    print("POW FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("SYST:ERR? FAILED:", e)

# ---------------------------------------------------------
# 4. POWER ON
# ---------------------------------------------------------
print("\n-- SOUR0:POW:STAT ON --")
try:
    inst.write("SOUR0:POW:STAT ON")
    print("STAT OK")
except Exception as e:
    print("STAT FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("SYST:ERR? FAILED:", e)

# ---------------------------------------------------------
# 5. Set wavelength
# ---------------------------------------------------------
print("\n-- SOUR0:WAV 1545e-9 --")
try:
    inst.write("SOUR0:WAV 1545e-9")
    print("WAV OK")
except Exception as e:
    print("WAV FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("ERR FAILED:", e)

# ---------------------------------------------------------
# 6. Sweep mode
# ---------------------------------------------------------
print("\n-- SOUR0:WAV:SWE:MODE CONT --")
try:
    inst.write("SOUR0:WAV:SWE:MODE CONT")
    print("MODE OK")
except Exception as e:
    print("MODE FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("ERR FAILED:", e)

# ---------------------------------------------------------
# 7. Sweep start
# ---------------------------------------------------------
print("\n-- SOUR0:WAV:SWE:STAR 1.545e-6 --")
try:
    inst.write("SOUR0:WAV:SWE:STAR 1.545e-6")
    print("STAR OK")
except Exception as e:
    print("STAR FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("ERR FAILED:", e)

# ---------------------------------------------------------
# 8. Sweep stop
# ---------------------------------------------------------
print("\n-- SOUR0:WAV:SWE:STOP 1.565e-6 --")
try:
    inst.write("SOUR0:WAV:SWE:STOP 1.565e-6")
    print("STOP OK")
except Exception as e:
    print("STOP FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("ERR FAILED:", e)

# ---------------------------------------------------------
# 9. Sweep step
# ---------------------------------------------------------
print("\n-- SOUR0:WAV:SWE:STEP 0.01NM --")
try:
    inst.write("SOUR0:WAV:SWE:STEP 0.01NM")
    print("STEP OK")
except Exception as e:
    print("STEP FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("ERR FAILED:", e)

# ---------------------------------------------------------
# 10. Sweep start command
# ---------------------------------------------------------
print("\n-- SOUR0:WAV:SWE:STAT START --")
try:
    inst.write("SOUR0:WAV:SWE:STAT START")
    print("START OK")
except Exception as e:
    print("START FAILED:", e)

try:
    print("SYST:ERR? ->", inst.query("SYST:ERR?"))
except Exception as e:
    print("ERR FAILED:", e)

print("\n==== DONE ====")

inst.close()
rm.close()
