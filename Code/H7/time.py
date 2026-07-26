import time as _stdlib_time


def localtime():
    return _stdlib_time.localtime()


def sleep_ms(milliseconds):
    _stdlib_time.sleep(milliseconds / 1000.0)


def sleep(seconds):
    _stdlib_time.sleep(seconds)
