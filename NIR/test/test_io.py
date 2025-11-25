import time
from NIR.nir_controller import NIR8164
# from NIR.sweep import HP816xLambdaScan
import numpy as np
import matplotlib.pyplot as plt
import logging
logging.getLogger("matplotlib").setLevel(logging.ERROR)
from utils.timing_helper import timed_function

def main():
    dev = NIR8164()
    dev.connect()

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

    @timed_function
    def optical_function(range):
        return dev.optical_sweep(1500.0, 1600.0, 0.01, 1.0, args=(1, -30, range))
    
    trials = []

    for x in [-i for i in range(10,40, 10)]:
        wl, ch1, ch2 = optical_function(x)
        trials.append(
            {
                "label": f"{x} dBm Range",
                "wl": wl,
                "channels": [ch1, ch2]
            }
        )
    wl, ch1, ch2 = optical_function(None)
    trials.append({
        "label": "Auto dBm Range",
        "wl": wl,
        "channels": [ch1, ch2],
    })

    # Now show all trials side by side
    plot_trials_side_by_side(trials)

    dev.cleanup_scan()
    dev.configure_units()
    dev.disconnect()
    print("Done.")

if __name__ == "__main__":
    main()
