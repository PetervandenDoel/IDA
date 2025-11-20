from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration
import pyvisa as visa
import time
# from NIR.lambda_sweep import LambdaScanProtocol
from NIR.nir_controller import NIR8164
import logging
logging.getLogger("matplotlib").setLevel(logging.ERROR)

def main():
    import numpy as np
    laser = NIR8164()
    laser.connect()
    laser.write('SENSE1:CHAN1:POW:RANGE:AUTO 1')
    # laser.write('SENSE1:CHAN2:POW:RANGE:AUTO 1')
    # for _ in range(10):
    #     print(laser.get_power_range())
    # time.sleep(0.3)
    time.sleep(0.1)
    # SWEEP
    wl, ch1, ch2 = laser.optical_sweep(
        1490, 1600, 0.01, 1.0, mode="grr"
    )

    import matplotlib.pyplot as plt
    plt.plot(wl, ch1)
    plt.plot(wl, ch2)
    plt.show()
    laser.disconnect()

if __name__ == '__main__':
    main()