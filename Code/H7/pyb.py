class USB_VCP:
    def __init__(self):
        self._connected = False

    def isconnected(self):
        return self._connected

    def any(self):
        return False

    def read(self, size=1):
        return b""

    def write(self, data):
        if isinstance(data, str):
            data = data.encode("ascii", "ignore")
        return len(data)
