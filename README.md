# AutoLotto Timing Summary

This project uses a timed sequence of actuator and motor actions during each cycle. The following summary documents the current timing behavior for troubleshooting.

## Cycle timing sequence

1. Full actuator retraction
   - Duration: 6.0 seconds
   - Action: retract actuator fully before the cycle begins

2. Full actuator extension
   - Duration: 4.25 seconds
   - Action: extend actuator until the platform reaches the bottom of the dome

3. Motor randomization run
   - Duration: 7.5 seconds
   - Action: run the motor to randomize the balls

4. First ball retraction
   - Duration: 35/47 seconds (approximately 0.7447 seconds)
   - Action: retract the actuator for one ball-extraction step

5. Motor jog after first ball retraction
   - Duration: 0.5 seconds
   - Action: briefly spin the motor after the first ball retraction

6. Tag data collection
   - Timeout: 5.0 seconds
   - Action: collect tag values from the serial interface after each retraction step

7. Motor run to move balls down the tube
   - Duration: 1.0 second
   - Action: run the motor briefly between extraction steps; this same action is repeated twice in the code before the pause

8. Ball step pause
   - Duration: 0.1 seconds
   - Action: short pause between extraction steps

## Notes

- The sequence repeats for 5 ball-extraction steps per cycle.
- The overall runtime limit is 2 minutes per session.
- These values are useful when diagnosing timing-related issues or comparing expected behavior against observed behavior.
