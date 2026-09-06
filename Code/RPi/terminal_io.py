import time


# Sleep in short intervals so a running cycle can stop promptly.
def sleep_interruptible(duration, stop_event=None):
    deadline = time.time() + duration
    while time.time() < deadline:
        if stop_event is not None and stop_event.is_set():
            return True
        time.sleep(min(0.05, deadline - time.time()))
    return False
