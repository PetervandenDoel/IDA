import time
from NIR.nir_controller import NIR8164
import numpy as np
import matplotlib.pyplot as plt
import logging
logging.getLogger("matplotlib").setLevel(logging.ERROR)

def main():
    dev = NIR8164(com_port=4, gpib_addr=20)
    # print("Laser power/wavelength...")
    # dev.set_power(-10)
    # print("P =", dev.get_power())
    dev.set_wavelength(1550.0)
    # print("WL =", dev.get_wavelength())

    # print("Detector live read...")
    # try:
    #     p1, p2 = dev.read_power()
    #     print("Pch1, Pch2 =", p1, p2)
    # except Exception as e:
    #     print("Live read skipped:", e)


    # print("Lambda scan...")
    # wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -10, -30))
    # print("Points:", len(wl), "WL[0..-1] =", wl[0], wl[-1])
    # print(ch1,ch2)
    def plot_trials_side_by_side(trials):
        """
        trials: list of dicts like:
            {
                "label": "Trial 1: No settings",
                "wl": wl_array,
                "channels": [ch1_array, ch2_array, ...]
            }
        """
        n = len(trials)
        if n == 0:
            return

        fig, axes = plt.subplots(1, n, figsize=(5 * n, 4), sharex=True, sharey=True)
        if n == 1:
            axes = [axes]  # make iterable

        for ax, trial in zip(axes, trials):
            wl = trial["wl"]
            channels = trial["channels"]
            y = np.vstack(channels)  # shape: (num_detectors, num_points)

            for i in range(y.shape[0]):
                ax.plot(wl, y[i, :], label=f"Detector {i+1}")

            ax.set_title(trial["label"])
            ax.set_xlabel("Wavelength [nm]")
            ax.grid(True)

        # Only first subplot gets y-label
        axes[0].set_ylabel("Power [dBm]")

        # One shared legend for all subplots
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, title="Detector", loc="upper right")

        fig.tight_layout()
        plt.show()
    
    def p(wl, ch1, ch2, title="Lambda Scan"):
        x = wl
        y = np.vstack([ch1, ch2])

        plt.figure()
        for i in range(y.shape[0]):
            plt.plot(x, y[i, :], label=f"Detector {i+1}")

        plt.xlabel("Wavelength [nm]")
        plt.ylabel("Power [dBm]")
        plt.title(title)
        plt.legend(title="Detector")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    # print("Trial 1: No settings")
    # wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0)
    # p(wl, ch1, ch2, "Trial 1")
    # print("Trial 2: (-10, Auto)")
    # wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -10, None))
    # p(wl, ch1, ch2, "Trial 2")
    # print("Trial 3: (-10, -30 dBm)")
    # wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -10, -30))
    # p(wl, ch1, ch2, "Trial 3")
    # print("Trial 4: (-30, -30 dBm)")
    # wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -30, -30))
    # p(wl, ch1, ch2, "Trial 4")

    print("Running sweeps...")
    trials = []

    print("Trial 1: No settings")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0)
    trials.append({
        "label": "Trial 1: No settings",
        "wl": wl,
        "channels": [ch1, ch2],
    })

    print("Trial 2: (-10, Auto)")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -30, -10))
    trials.append({
        "label": "Trial 2: (-10, Auto)",
        "wl": wl,
        "channels": [ch1, ch2],
    })

    print("Trial 3: (-10, -30 dBm)")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -30, -20))
    trials.append({
        "label": "Trial 3: (-10, -30 dBm)",
        "wl": wl,
        "channels": [ch1, ch2],
    })

    print("Trial 4: (-30, -30 dBm)")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -30, -30))
    trials.append({
        "label": "Trial 4: (-30, -30 dBm)",
        "wl": wl,
        "channels": [ch1, ch2],
    })
    print("Trial 5: (-50, -30 dBm)")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -30, -40))
    trials.append({
        "label": "Trial 5: (-50, -30 dBm)",
        "wl": wl,
        "channels": [ch1, ch2],
    })
    print("Trial 6: (-60, -30 dBm)")
    wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -30, -50))
    trials.append({
        "label": "Trial 6: (-60, -30 dBm)",
        "wl": wl,
        "channels": [ch1, ch2],
    })
    # Now show all trials side by side
    plot_trials_side_by_side(trials)
    # wl, ch1, ch2 = dev.optical_sweep(1500.0, 1600.0, 0.1, 1.0, 0, (1, -10, -20))
    # p(wl, ch1, ch2)

    dev.cleanup_scan()
    dev.configure_units()
    dev.disconnect()
    print("Done.")

if __name__ == "__main__":
    main()
