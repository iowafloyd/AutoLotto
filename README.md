# AutoLotto Design & Purpose
The AutoLotto hardware and software package is an inexpensive automated portable, modular, open-source platform for the generation/recording of lottery drawing values. The purpose of AutoLotto is to generate a large dataset of physically randomized values for ingestion into a machine learning model and subsequent next-drawing prediction.

The physical system has been designed to utilize, to the extent possible with the given consumer-grade hardware, the system dynamics of numerous multi-state lottery systems. The system is fully automated once the program is started and the desired total runtime is input.

# Hardware
The below list of materials is required to build AutoLotto. Some modification is required, as shown in detail in the “Build” folder
 - Portable Aluminum step-stool (brand: Loyoda)
 - Aluminum baseplate, pattern plates & U-channel extrusions, bearing assemblies, shafts, cap screws & nuts, and drive wheels (brand: GoBilda)
 - Clear acrylic tube (brand: uxcell)
 - Clear acrylic dome (brand: HiCaptain)
 - 25mm plastic “ping pong” balls (brand: Chengu)
 - AprilTags printed on 0.75” circular sticker-paper (brand: Premium Label Supply)
 - Clear semi-glass paint for lottery balls (brand: Krylon)
 - Raspberry Pi 4B (8GB RAM version used)
 - USB external SSD (brand: SSK, 128GB version used)
 - L298N motor controller with dual H-bridge (brand: BOJACK used)
 - Linear actuator, 12V, 6” stroke, with integral limit switches (brand: Firgelli)
 - Motor, 12V, 1620RPM (brand: GoBilda Yellowjacket)
 - Webcam, USB, with autofocus, 2K resolution, adjustable field of view (brand: Anker PowerConf C200)
 - USB-C LED (brand: ICBEAMER) and USB-C to 2-wire connector (brand: QIANRENON)
 - 120VAC-to-12VDC, 5A power adapter (brand: ALITOVE)
 - 12VDC-to-5VDC buck converter (brand: PlusRoc)
 - Touch screen, 7” IPS LCD, with DSI input for Raspberry Pi, 800x480 resolution (brand: Hosyond)
 - Custom touch screen holder, motor controller enclosure, and lottery ball platform 3D printed
 - SAE pressure rivet nut tool kit (brand: AskWay)
 - Thumb screws (1/4”-20 preferred, brand: Zyghjort)
 - Tools for assembly/modifications
     - M4 Allen wrench and crescent wrench, or socket
     - 3/8” drill bit
     - 3” hole saw
     - wire cutters/strippers
     - 2.5mm thick zip ties
     - 1/8” heat shrink tubing
     - Set of DuPont cables (F-F and M-F) for Raspberry Pi
     - To make life easier:
        - Multimeter for troubleshooting
        - Pigtail barrel plug connector cables, 12VDC 5A (
        - Clear plastic wire clips with adhesive backing (brand: Blulu)
        - Helping Hands soldering station (brand: KOTTO)
        - Wire loom tubing, 3/8” diameter (brand: Alex Tech)
        - Silicone bumps, adhesive-backed (brand: QUEENTI)
        - Lever wire connectors (2-in/4-out and 2-in/6-out, brand: XALXMAW)
        - Digital soldering station (brand: YIHUA)
        - Lots of time and patience to strip wires, twist, tin, solder, and don’t-forget-to-heat-shrink-after!


# Main Sequence

The GUI is designed for minimalistic, distraction-free viewing of the AutoLotto process with large, easily-touched controls. The user can enable the webcam output to the screen or leave it off. The user can also set the total runtime desired in Settings. Lastly, the user can enable recording of AprilTag detection diagnostics, but this should only be required when first assembling and troubleshooting the system.

Upon program start, the actuator is retracted fully. This is to establish “full bottom”, as the hardware used does not have feedback for the Pi to determine its current location. The actuator is then extended fully, which brings the ball platform above the bottom level of the dome. The motor is activated to spin the dome for a given amount of time, ensuring lottery ball randomization. The actuator is retracted a given amount of time to ensure the ball platform is now level with the bottom of the dome. The actuator is retracted one ball-diameter and the dome is jogged to allow a ball to drop into the tube. The webcam reads any AprilTags in its view and records them. The first value seen that is not unique to this loop is recorded. The motor is activated to spin the dome again for randomization, and the actuator is retracted another ball-diameter. This repeats for a total of 5 balls. Once five unique values have been recorded, the loop is complete.

Due to the unpredictable nature of, well… nature… sometimes balls don’t drop immediately down into the tube. Or sometimes the webcam doesn’t immediately see the new AprilTag. These and other similar bugs have been found and fixed in the main sequence code.

For a graphical overview of the GUI lifecycle and the motion-control/camera
sequence, see [PROCESS_FLOWS.md](PROCESS_FLOWS.md).

## Desktop launcher

The Raspberry Pi GUI can be launched from a desktop icon and started automatically with the graphical desktop session.

From the project directory, run:

```sh
./install_autolotto.sh
```

This installs `AutoLotto.desktop` on the desktop and in the user's autostart directory. The launcher uses the project's `.venv` Python interpreter and starts `Code/RPi/main.py` without opening a terminal window.

Run CSV files and their filtered versions are saved in the project's `Results/` folder.
The `Results/` folder is tracked in Git. After the selected runtime completes
without an application or cleanup error, AutoLotto stages and commits changes
to that folder and pushes the current branch using the repository's configured
Git remote. Configure GitHub authentication and an upstream branch on the
device before running; credentials should remain in Git's credential manager
or SSH configuration, never in the repository or application code. A Git
commit or push failure is shown as an application error.

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
   - Duration: 25/47 seconds (approximately 0.5319 seconds)
   - Action: retract the actuator for one ball-extraction step

5. Actuator rest after each ball retraction
   - Duration: three times the retraction duration (approximately 1.5957 seconds)
   - Action: keep the actuator stopped to maintain its 25% duty cycle

6. Motor jog after first ball retraction
   - Duration: 0.5 seconds
   - Action: briefly spin the motor after the first ball retraction

7. Tag data collection
   - Timeout: 5.0 seconds
   - Action: collect tag values from the serial interface after each retraction step

8. Motor run to move balls down the tube
   - Duration: 1.0 second
   - Action: run the motor briefly between extraction steps; this same action is repeated twice in the code before the pause

9. Ball step pause
   - Duration: 0.1 seconds
   - Action: short pause between extraction steps

## Notes

- The sequence repeats for 5 ball-extraction steps per cycle.
- The overall runtime limit is 2 minutes per session.
- These values are useful when diagnosing timing-related issues or comparing expected behavior against observed behavior.
