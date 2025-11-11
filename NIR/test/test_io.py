import time
from NIR.nir_controller import NIR8164

def main():
    dev = NIR8164(com_port=4, gpib_addr=20)
    print("Laser power/wavelength...")
    dev.set_power(-10)
    print("P =", dev.get_power())
    dev.set_wavelength(1550.0)
    print("WL =", dev.get_wavelength())

    print("Detector live read...")
    try:
        p1, p2 = dev.read_power()
        print("Pch1, Pch2 =", p1, p2)
    except Exception as e:
        print("Live read skipped:", e)


    print("Lambda scan (short)...")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.001, 5.0, 0, (1, -80, None))
    print("Points:", len(wl), "WL[0..-1] =", wl[0], wl[-1])
    print(ch1,ch2)


    dev.cleanup_scan()
    dev.configure_units()
    dev.disconnect()
    print("Done.")

if __name__ == "__main__":
    main()
