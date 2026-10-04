import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2

try:
    from .tag_diagnostics import TagDiagnostics
except ImportError:
    from tag_diagnostics import TagDiagnostics


def make_detector():
    # Select the first available AprilTag detector implementation.
    try:
        import apriltag as at

        detector = at.Detector()
        return detector.detect, "apriltag"
    except Exception:
        try:
            from pupil_apriltags import Detector as PADetector

            detector = PADetector()
            return detector.detect, "pupil_apriltags"
        except Exception:
            print(
                "ERROR: No apriltag detector found. Install `apriltag` or `pupil_apriltags`.",
                file=sys.stderr,
            )
            raise


def format_detection(detection):
    # Normalize detector-specific fields into one common tuple.
    tag_id = getattr(detection, "tag_id", None)
    if tag_id is None:
        tag_id = getattr(detection, "id", None)
    center = getattr(detection, "center", None)
    corners = getattr(detection, "corners", None)
    margin = getattr(detection, "decision_margin", None)
    if margin is None:
        margin = getattr(detection, "hamming", None)
    return tag_id, center, corners, margin


class C200Camera:
    # Coordinate camera capture, detection, logging, and tag collection.
    def __init__(
        self,
        camera_index=0,
        log_dir=None,
        max_log_fps=10.0,
        detector=None,
        capture=None,
    ):
        if detector is None:
            self.detect, self.detector_name = make_detector()
        else:
            self.detect, self.detector_name = detector, "injected"
        self.capture = capture if capture is not None else cv2.VideoCapture(camera_index)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError(f"Cannot open camera index {camera_index}")
        self.capture_lock = threading.Lock()

        if log_dir is None:
            log_dir = Path(__file__).resolve().parents[2] / "Test" / "camera_logs"
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.log_path = log_dir / f"c200_camera_{timestamp}.log"
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.max_log_fps = max(0.001, max_log_fps)
        self.last_log = 0.0
        self.diagnostics = TagDiagnostics(log_dir)
        self.log(f"Camera log: {self.log_path}")
        self.log(f"Using detector: {self.detector_name}")

    # Enable or disable structured AprilTag diagnostics for the current run.
    def set_tag_diagnostics_enabled(self, enabled):
        log_path = self.diagnostics.set_enabled(enabled)
        if enabled and log_path is not None:
            self.log(f"Tag diagnostics: {log_path}")

    # Attach collection context to subsequent diagnostic records.
    def set_diagnostic_context(self, **context):
        self.diagnostics.set_context(**context)

    # Write camera messages to both the console and the session log.
    def log(self, message, error=False):
        stream = sys.stderr if error else sys.stdout
        print(message, file=stream, flush=True)
        print(message, file=self.log_file, flush=True)

    # Capture a frame, detect tags, and periodically log observations.
    def read_detections(self):
        with self.capture_lock:
            ret, frame = self.capture.read()
        if not ret:
            self.log("Warning: empty frame, retrying...", error=True)
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = self.detect(gray)
        self.diagnostics.record(
            "detections",
            detections=[
                {
                    "tag_id": format_detection(detection)[0],
                    "center": format_detection(detection)[1],
                    "corners": format_detection(detection)[2],
                    "margin": format_detection(detection)[3],
                }
                for detection in detections
            ],
        )
        now = time.monotonic()
        if now - self.last_log >= 1.0 / self.max_log_fps:
            self.last_log = now
            timestamp = datetime.utcnow().isoformat() + "Z"
            self.log(f"[{timestamp}] Detections: {len(detections)}")
            for index, detection in enumerate(detections):
                tag_id, center, corners, margin = format_detection(detection)
                self.log(
                    f" - #{index}: id={tag_id} center={center} "
                    f"corners={corners} margin={margin}"
                )
        return detections

    # Return the latest raw camera frame for the live preview.
    def read_frame(self):
        with self.capture_lock:
            ret, frame = self.capture.read()
        return frame if ret else None

    # Return the currently visible tag identifiers.
    def read_tag_ids(self):
        detections = self.read_detections()
        if detections is None:
            return None
        return {
            str(format_detection(detection)[0])
            for detection in detections
            if format_detection(detection)[0] is not None
        }

    # Wait for one previously unseen tag or an interruption/timeout.
    def wait_for_new_tag(
        self,
        previous_visible_tags,
        confirmed_tags,
        stop_event=None,
        timeout=10.0,
        stable_frames=3,
        poll_interval=0.05,
    ):
        deadline = time.monotonic() + timeout
        candidate = None
        candidate_frames = 0
        last_visible_tags = set(previous_visible_tags)
        self.diagnostics.record(
            "wait_started",
            previous_visible_tags=sorted(previous_visible_tags),
            confirmed_tags=sorted(confirmed_tags),
            timeout=timeout,
        )
        while time.monotonic() < deadline:
            if stop_event is not None and stop_event.is_set():
                self.diagnostics.record(
                    "tag_decision",
                    outcome="stopped",
                    visible_tags=sorted(last_visible_tags),
                )
                return None, last_visible_tags
            detections = self.read_detections()
            if detections is None:
                time.sleep(poll_interval)
                continue
            ordered_visible_tags = [
                str(tag_id)
                for detection in detections
                if (tag_id := format_detection(detection)[0]) is not None
            ]
            visible_tags = set(ordered_visible_tags)
            last_visible_tags = visible_tags
            new_tags = visible_tags - set(previous_visible_tags) - set(confirmed_tags)
            if new_tags:
                new_candidate = next(
                    tag_id for tag_id in ordered_visible_tags if tag_id in new_tags
                )
                self.diagnostics.record(
                    "tag_decision",
                    outcome="accepted",
                    tag_id=new_candidate,
                    visible_tags=sorted(visible_tags),
                    new_tags=sorted(new_tags),
                )
                return new_candidate, visible_tags
            else:
                candidate = None
                candidate_frames = 0
            time.sleep(poll_interval)
        self.diagnostics.record(
            "tag_decision",
            outcome="timeout",
            visible_tags=sorted(last_visible_tags),
            new_tags=sorted(
                last_visible_tags - set(previous_visible_tags) - set(confirmed_tags)
            ),
        )
        return None, last_visible_tags

    # Collect a fixed number of detected tag values within a time limit.
    def collect_tag_values(self, timeout=5.0, minimum_values=5):
        collected = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and len(collected) < minimum_values:
            detections = self.read_detections()
            if detections is None:
                time.sleep(0.1)
                continue
            collected.extend(
                str(format_detection(detection)[0]) for detection in detections
            )
        return collected[:minimum_values]

    # Release camera resources and close the camera log.
    def close(self):
        self.capture.release()
        self.diagnostics.close()
        self.log_file.close()