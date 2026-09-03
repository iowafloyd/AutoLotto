# Change Log

## Version 2.1

- Added result filtering during shutdown. The latest Results file is analyzed line by line, duplicate values are removed while preserving their first-seen order, and the filtered data is saved to a new file.

## Version 2.0

Migrated camera-based tag detection from the OpenMV H7 camera to the Anker PowerConf C200 webcam.

- Replaced the H7 serial connection, handshake, tag messages, and image-save commands with direct webcam capture through OpenCV.
- AprilTags are detected from captured webcam frames during each ball-collection step.
- Added timestamped C200 camera logs containing detector output and camera warnings for troubleshooting.
- Removed H7 firmware, H7 serial helpers, H7 demos, and H7 protocol tests.
- Preserved the existing actuator, motor, timing, keyboard, shutdown, and CSV output workflow.

## Version 1.0

Original process flow using the OpenMV H7 camera:

- The Raspberry Pi connected to the H7 over a serial USB link.
- The Pi sent a handshake and waited for the H7 to report that it was ready.
- The cycle fully retracted and extended the actuator, then randomized the balls with the motor.
- For each of five ball-extraction steps, the Pi moved the actuator, requested an image save from the H7, and allowed the ball to drop.
- The H7 detected AprilTags and sent tag values back to the Pi over serial.
- The Pi collected the tag values, recorded the cycle results in a timestamped CSV file, and completed the shutdown sequence when stopped or when the runtime limit was reached.
