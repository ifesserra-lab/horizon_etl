import logging
import time
from contextlib import contextmanager


class ProgressTracker:
    """Prints a compact one-line-per-step header during execution,
    then a sequential summary of all stage numbers and durations at the end.

    Suppresses Prefect's verbose console logger so the output stays clean.
    All timing and entity details still go to the ETL report JSON/MD files.
    """

    def __init__(self, total: int, name: str = "Pipeline"):
        self.total = total
        self.name = name
        self.current = 0
        self.start = time.time()
        self._step_times: list[tuple[str, float, str]] = []
        logging.getLogger("prefect").setLevel(logging.WARNING)

    @contextmanager
    def step(self, description: str):
        self.current += 1
        print(f"  Step {self.current}/{self.total}: {description} ...", flush=True)
        t0 = time.time()
        ok = True
        try:
            yield
        except BaseException:
            ok = False
            raise
        finally:
            dt = time.time() - t0
            self._step_times.append((description, dt, "OK" if ok else "FAIL"))

    def finish(self) -> float:
        elapsed = time.time() - self.start
        print(f"\n{'=' * 52}")
        print(f"  {self.name} — Summary")
        print(f"{'=' * 52}")
        for i, (desc, dt, status) in enumerate(self._step_times, 1):
            flag = "✓" if status == "OK" else "✗"
            print(f"  Step {i:>2}  {flag}  {desc:.<50s} {dt:>6.1f}s")
        print(f"{'─' * 52}")
        print(f"  Total{' ' * 44} {elapsed:>6.1f}s")
        failed = [(d, t) for d, t, s in self._step_times if s == "FAIL"]
        if failed:
            print()
            for desc, dt in failed:
                print(f"  FAIL  {desc} ({dt:.1f}s)")
        return elapsed
