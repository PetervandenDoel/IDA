from tqdm import tqdm
import time

class FileProgressTqdm(tqdm):
    """
    Silent tqdm that exports:
      - percentage
      - ETA (seconds)
      - iteration counters
    """
    def __init__(self, *args, progress_cb=None, **kwargs):
        super().__init__(*args, **kwargs, disable=True)
        self._cb = progress_cb
        self._t_last = time.time()
        self._ema_step = None  # exponential moving avg step time

    def update(self, n=1):
        t_now = time.time()
        dt = t_now - self._t_last
        self._t_last = t_now

        # Update EMA step duration
        if n > 0:
            step_time = dt / n
            if self._ema_step is None:
                self._ema_step = step_time
            else:
                # similar smoothing to tqdm's internal algorithm
                self._ema_step = (self._ema_step * 0.9) + (step_time * 0.1)

        super().update(n)

        if self._cb is not None and self.total:
            pct = (self.n / self.total) * 100.0

            # Remaining iterations
            remaining = max(self.total - self.n, 0)

            # ETA in seconds
            eta_sec = remaining * (self._ema_step or 0.0)

            try:
                self._cb(
                    percent=pct,
                    n=self.n,
                    total=self.total,
                    eta_seconds=eta_sec,
                )
            except Exception:
                pass


from pathlib import Path
import threading
import os
import json

_global_progress_lock = threading.Lock()


def write_progress_file(activity: str,
                        percent: float,
                        eta_seconds: float = None,
                        n: int = None,
                        total: int = None,
                        lock: threading.Lock = None):
    """
    Atomic writer for GUI progress dialog.
    Now includes ETA + counters if provided.
    """

    try:
        from GUI.lib_gui import PROGRESS_PATH
    except Exception:
        PROGRESS_PATH = Path(__file__).resolve().parent / "database" / "progress.json"

    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "activity": str(activity),
        "progress_percent": float(percent),
        "timestamp": time.time(),
    }
    print('AHHHHHHHHHHHHHHHHHHHHHHHHH')
    print(data)

    if eta_seconds is not None:
        data["eta_seconds"] = float(eta_seconds)

    if n is not None:
        data["n"] = int(n)

    if total is not None:
        data["total"] = int(total)

    tmp = PROGRESS_PATH.with_suffix(PROGRESS_PATH.suffix + ".tmp")

    if lock is None:
        lock = _global_progress_lock

    with lock:
        for attempt in range(5):
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, PROGRESS_PATH)
                break

            except PermissionError:
                if attempt == 4:
                    print("[Progress] Failed to update progress file after retries")
                else:
                    time.sleep(0.05)

            except Exception as e:
                print(f"[Progress] Unexpected error: {e}")
                break
