import threading
from global_var import DEFAULT_JOIN_TIMEOUT


class ParserBase:
    """Small base class to reduce boilerplate for start/stop of parser threads.

    Subclasses should provide a `_run` method (the thread target) and a
    `name` attribute for logging. The base class exposes `_start_thread()` and
    `_stop_thread()` helpers that manage `self.running`, `self.thread` and
    timed join behavior while logging warnings on failure.
    """
    def __init__(self, log_queue, name='Parser'):
        self.log_queue = log_queue
        self.running = False
        self.thread = None
        self.name = name

    def _start_thread(self, target):
        self.running = True
        self.thread = threading.Thread(target=target, daemon=False, name=self.name)
        self.thread.start()

    def _stop_thread(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=DEFAULT_JOIN_TIMEOUT)
            if self.thread.is_alive():
                try:
                    self.log_queue.put(f"{self.name} thread did not stop within timeout.")
                except Exception:
                    pass
