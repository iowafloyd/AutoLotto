import os as _stdlib_os

for _name in dir(_stdlib_os):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_stdlib_os, _name)
