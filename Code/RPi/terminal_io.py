import select
import sys
import termios
import time
import tty

old_settings = None


def enable_raw_mode():
    global old_settings
    if sys.stdin.isatty():
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())


def restore_terminal():
    global old_settings
    if old_settings is not None:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def check_for_keypress():
    if select.select([sys.stdin], [], [], 0)[0]:
        sys.stdin.read(1)
        return True
    return False


def sleep_interruptible(duration, stop_event=None):
    deadline = time.time() + duration
    while time.time() < deadline:
        interrupted = (
            stop_event.is_set() if stop_event is not None else check_for_keypress()
        )
        if interrupted:
            return True
        time.sleep(min(0.05, deadline - time.time()))
    return False
