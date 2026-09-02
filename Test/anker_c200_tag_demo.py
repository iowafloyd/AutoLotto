#!/usr/bin/env python3
"""
Simple AprilTag detection demo for the Anker PowerConf C200 webcam.

Run on the Raspberry Pi with the webcam connected. The script captures frames
from the camera, runs an AprilTag detector, and prints detected tag ids and
positions to the terminal. Optionally displays a preview window when a
desktop/session is available.

Dependencies:
 - OpenCV (system package `python3-opencv` recommended on Raspbian)
 - apriltag or pupil_apriltags (one of them)

Example:
  python3 Test/anker_c200_tag_demo.py --camera 0

Press Ctrl-C to exit.
"""

import argparse
import sys
import time
from datetime import datetime

import cv2


def make_detector():
    try:
        import apriltag as at

        det = at.Detector()

        def detect(gray):
            return det.detect(gray)

        detector_name = 'apriltag'
        return detect, detector_name
    except Exception:
        try:
            from pupil_apriltags import Detector as PADetector

            det = PADetector()

            def detect(gray):
                return det.detect(gray)

            detector_name = 'pupil_apriltags'
            return detect, detector_name
        except Exception:
            print('ERROR: No apriltag detector found. Install `apriltag` or `pupil_apriltags`.', file=sys.stderr)
            raise


def fmt_detection(d):
    # Support both apriltag and pupil_apriltags result objects/dicts
    tag_id = getattr(d, 'tag_id', None) or getattr(d, 'id', None)
    center = getattr(d, 'center', None)
    corners = getattr(d, 'corners', None)
    decision = getattr(d, 'decision_margin', None)
    if decision is None:
        decision = getattr(d, 'hamming', None)

    return tag_id, center, corners, decision


def main():
    parser = argparse.ArgumentParser(description='AprilTag demo for Anker C200 webcam')
    parser.add_argument('--camera', '-c', type=int, default=0, help='Camera index (default: 0)')
    parser.add_argument('--display', '-d', action='store_true', help='Show preview window (optional)')
    parser.add_argument('--fps', type=float, default=10.0, help='Maximum prints per second')
    args = parser.parse_args()

    detect_func, detector_name = make_detector()
    print(f'Using detector: {detector_name}')

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f'ERROR: Cannot open camera index {args.camera}', file=sys.stderr)
        sys.exit(2)

    last_print = 0.0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print('Warning: empty frame, retrying...', file=sys.stderr)
                time.sleep(0.1)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            detections = detect_func(gray)

            now = time.time()
            if now - last_print >= 1.0 / max(0.001, args.fps):
                last_print = now
                ts = datetime.utcnow().isoformat() + 'Z'
                print(f'[{ts}] Detections: {len(detections)}')
                for i, d in enumerate(detections):
                    tag_id, center, corners, decision = fmt_detection(d)
                    print(f' - #{i}: id={tag_id} center={center} corners={corners} margin={decision}')

            if args.display:
                # draw overlays
                for d in detections:
                    _, center, corners, _ = fmt_detection(d)
                    if corners is not None:
                        pts = corners.astype(int)
                        for j in range(4):
                            p1 = tuple(pts[j])
                            p2 = tuple(pts[(j + 1) % 4])
                            cv2.line(frame, p1, p2, (0, 255, 0), 2)
                    if center is not None:
                        c = tuple(map(int, center))
                        cv2.circle(frame, c, 4, (0, 0, 255), -1)

                cv2.imshow('Anker C200 AprilTag', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print('\nInterrupted by user, exiting...')
    finally:
        cap.release()
        if args.display:
            cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
