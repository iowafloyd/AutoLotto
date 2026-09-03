import sys
import time
from datetime import datetime
from pathlib import Path

import cv2


def make_detector():
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

        if log_dir is None:
            log_dir = Path(__file__).resolve().parents[2] / "Test" / "camera_logs"
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.log_path = log_dir / f"c200_camera_{timestamp}.log"
        self.log_file = self.log_path.open("w", encoding="utf-8")
        self.max_log_fps = max(0.001, max_log_fps)
        self.last_log = 0.0
        self.log(f"Camera log: {self.log_path}")
        self.log(f"Using detector: {self.detector_name}")

    def log(self, message, error=False):
        stream = sys.stderr if error else sys.stdout
        print(message, file=stream, flush=True)
        print(message, file=self.log_file, flush=True)

    def read_detections(self):
        ret, frame = self.capture.read()
        if not ret:
            self.log("Warning: empty frame, retrying...", error=True)
            return None

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = self.detect(gray)
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

    def close(self):
        self.capture.release()
        self.log_file.close()