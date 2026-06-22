import logging
import time
from contextlib import contextmanager


class ProgressTracker:
    """Prints a compact one-line-per-step summary to the terminal.

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
        elapsed = time.time() - self.start
        print(
            f"[{elapsed:>7.1f}s] Step {self.current}/{self.total}: {description} ...",
            end=" ",
            flush=True,
        )
        t0 = time.time()
        ok = True
        try:
            yield
        except BaseException:
            ok = False
            raise
        finally:
            dt = time.time() - t0
            status = "OK" if ok else "FAIL"
            print(f"{status} ({dt:.1f}s)")
            self._step_times.append((description, dt, status))

    def finish(self) -> float:
        elapsed = time.time() - self.start
        print(f"\n{'=' * 50}")
        print(f"{self.name} finished in {elapsed:.1f}s")
        failed = [(d, t) for d, t, s in self._step_times if s == "FAIL"]
        if failed:
            for desc, dt in failed:
                print(f"  FAIL  {desc} ({dt:.1f}s)")
        return elapsed
