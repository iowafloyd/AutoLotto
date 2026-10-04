# AutoLotto Process Flows

This is a rough map of the current GUI and hardware-control behavior. Timings
and hardware details are configured in `Code/RPi/config.py` and may change.

## GUI and run lifecycle

```text
Application starts
    |
    +-- Initialize camera, GPIO, CSV output, controller, and GUI
    |       |
    |       +-- Initialization fails -> show error and wait for CLOSE
    |       |
    |       `-- Initialization succeeds -> enter Tk event loop
    |
    +-- While idle
    |       +-- Every ~100 ms: render the latest preview frame
    |       |       `-- Request frame on a background reader if one is not active
    |       +-- Every ~1 second: update elapsed-time display
    |       `-- START -> create stop event and launch run worker
    |
    `-- Run worker
            +-- While not stopped and runtime remains:
            |       +-- Run one motion-control / camera cycle
            |       +-- Cycle stopped -> finish with stop-button reason
            |       +-- Tag confirmation timeout -> finish with timeout reason
            |       `-- Cycle succeeds -> update GUI, append results, repeat
            |
            +-- Runtime expires -> finish with runtime-reached reason
            +-- Exception -> record error for GUI status
            `-- Always try to:
                    1. Stop/retract hardware and log completion
                    2. Filter results
                    3. Release GPIO and camera resources
                    4. Notify Tk that the worker finished

STOP button
    `-- Set stop event -> worker exits at its next interruptible checkpoint

END button or window close during a run
    +-- Set close request and stop event
    +-- Wait up to 10 seconds for worker shutdown
    +-- If worker finishes -> close window after cleanup
    `-- If worker is still stuck -> emergency-stop motor/actuator outputs,
        then close window

Window close while idle
    `-- Emergency-stop outputs -> release resources on a background thread
        -> close window without waiting for camera cleanup
```

## Motion control and camera cycle

```text
Begin cycle
    |
    +-- Fully retract actuator
    +-- Fully extend actuator
    +-- Run motor to randomize balls
    +-- Retract actuator briefly to align platform
    +-- Read current visible tag IDs as the initial baseline
    |
    `-- Repeat for each configured ball step
            +-- Retract actuator for one extraction step
            +-- Run motor briefly
            +-- Jog motor before confirmation
            +-- Wait for unseen tag ID(s)
            |       +-- One or more new IDs -> accept the first in detector order
            |       |   and remember all IDs visible in that frame
            |       +-- Stop requested -> return stopped
            |       `-- No new ID before timeout
            |               +-- Jog motor once more
            |               +-- Wait for unseen tag ID(s) again
            |               +-- New ID -> accept it and continue
            |               +-- Stop requested -> return stopped
            |               `-- Still none -> return timeout
            +-- Record confirmed value and update GUI
            `-- Pause briefly before the next ball step
    |
    `-- Return collected values as the completed cycle result

After cycle (in the run worker)
    +-- Successful cycle -> save values and begin another cycle if runtime remains
    +-- Timeout or stop -> leave the run loop
    `-- Finish -> stop/retract hardware, filter result file, clean up resources
```

## Camera details

- The live preview reads frames on a background thread so camera capture does
  not block Tk's event loop. Tk renders only the latest published frame.
- Tag confirmation uses camera detections, not the preview image. The detector's
  order determines which unseen tag is selected when a frame contains multiple
  new IDs.
- A detected tag is considered new only if it was not in the previous visible
  tag set and has not already been confirmed in the current cycle.
- Camera detection logs are rate-limited. Optional structured diagnostics can
  record per-frame observations and tag decisions.
- A forced window close stops the motor and actuator outputs, but a blocked
  camera or hardware operation may prevent background resource cleanup from
  completing before the process exits.