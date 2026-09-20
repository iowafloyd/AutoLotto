import json
import threading
from datetime import datetime, timezone
from pathlib import Path


def make_json_safe(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return make_json_safe(value.tolist())
    return str(value)


class TagDiagnostics:
    """Write optional structured AprilTag observations and decisions."""

    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.enabled = False
        self.log_path = None
        self.log_file = None
        self.context = {}
        self.lock = threading.Lock()

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        with self.lock:
            if enabled == self.enabled:
                return self.log_path
            if enabled:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                self.log_path = self.log_dir / f"tag_diagnostics_{timestamp}.jsonl"
                self.log_file = self.log_path.open("w", encoding="utf-8")
                self.enabled = True
                self._write("diagnostics_started", log_path=str(self.log_path))
            else:
                self._write("diagnostics_stopped")
                self.enabled = False
                if self.log_file is not None:
                    self.log_file.close()
                self.log_file = None
        return self.log_path

    def set_context(self, **context):
        with self.lock:
            self.context = dict(context)

    def record(self, event, **data):
        with self.lock:
            if self.enabled:
                self._write(event, **data)

    def _write(self, event, **data):
        entry = make_json_safe({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "context": self.context,
            **data,
        })
        json.dump(entry, self.log_file)
        self.log_file.write("\n")
        self.log_file.flush()

    def close(self):
        self.set_enabled(False)
