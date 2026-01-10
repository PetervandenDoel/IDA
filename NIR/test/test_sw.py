from NIR.sweep import HP816xLambdaScan

laser = HP816xLambdaScan(
    laser_gpib='GPIB0::4::INSTR',
    detectors_gpib=['GPIB0::20::INSTR']
)

c_ok = laser.connect_mf()

if c_ok:
    print('Connection successful')
else:
    print('failed to connect')

mapping = laser.enumarate_slots()

args_list = [(slot, mf,-30.0, -20.0) for _, mf, slot, _ in mapping]

info = laser.lambda_scan(
    start_nm=1200,
    stop_nm=1400,
    step_pm=10,
    power_dbm=1,
    num_scans=0,
    args=args_list
)
print(info)
laser.disconnect()
