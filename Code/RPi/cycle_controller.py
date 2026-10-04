import time

from c200_camera import C200Camera
from logging_utils import log_completion
from motion_control import (
    actuator_extend,
    actuator_retract,
    actuator_stop,
    gpio_cleanup,
    motor_run,
    motor_stop,
)
from terminal_io import sleep_interruptible
from config import (
    BALL_STEP_PAUSE,
    BALL_STEP_TIME,
    FULL_EXTENSION_TIME,
    FULL_RETRACTION_TIME,
    MOTOR_JOG_TIME,
    MOTOR_RUN_TIME,
    NUM_STEPS,
)


class CycleController:
    # Coordinate one complete ball-randomization and collection cycle.
    def __init__(self, camera):
        self.camera = camera

    # Run the actuator, motor, camera, and result-recording workflow.
    def run_cycle(self, stop_event, status_callback, drawn_values_callback=None):
        status_callback("Retracting actuator")
        print("Full retraction", flush=True)
        actuator_retract()
        if sleep_interruptible(FULL_RETRACTION_TIME, stop_event):
            return "stopped", None, None
        actuator_stop()

        status_callback("Extending actuator")
        print("Full extension", flush=True)
        actuator_extend()
        if sleep_interruptible(FULL_EXTENSION_TIME, stop_event):
            return "stopped", None, None
        actuator_stop()

        status_callback("Randomizing balls")
        print("Starting randomization", flush=True)
        motor_run()
        if sleep_interruptible(MOTOR_RUN_TIME, stop_event):
            return "stopped", None, None
        motor_stop()

        # Reset the platform and randomize the balls before collection.
        actuator_retract() # Initial actuator retraction so platform aligns with bottom of dome. Aids in first-ball alignment with camera
        if sleep_interruptible(BALL_STEP_TIME / 2, stop_event):
            return "stopped", None, None
        actuator_stop()

        print("Randomization complete. Starting data collection")
        print("Beginning ball extraction")
        cycle_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cycle_values = []
        self.camera.set_diagnostic_context(phase="initial_visibility")
        previous_visible_tags = self.camera.read_tag_ids() or set()

        # Extract and confirm each ball, stopping on interruption or timeout.
        for step in range(NUM_STEPS):
            self.camera.set_diagnostic_context(
                phase="ball_confirmation", step=step + 1
            )
            status_callback(f"Collecting ball {step + 1} of {NUM_STEPS}")
            actuator_retract()

            if sleep_interruptible(BALL_STEP_TIME, stop_event):
                return "stopped", None, None
            actuator_stop()
            motor_run()
            if sleep_interruptible(1.0, stop_event):
                return "stopped", None, None
            motor_stop()

            print("Motor jog before ball confirmation...")
            motor_run()
            if sleep_interruptible(MOTOR_JOG_TIME, stop_event):
                return "stopped", None, None
            motor_stop()

            status_callback("Waiting for ball confirmation")
            confirmed_tag, visible_tags = self.camera.wait_for_new_tag(
                previous_visible_tags,
                cycle_values,
                stop_event=stop_event,
            )
            if confirmed_tag is None:
                if stop_event.is_set():
                    return "stopped", None, None
                status_callback("No new ball detected; jogging motor again")
                motor_run()
                if sleep_interruptible(MOTOR_JOG_TIME, stop_event):
                    return "stopped", None, None
                motor_stop()
                confirmed_tag, visible_tags = self.camera.wait_for_new_tag(
                    previous_visible_tags,
                    cycle_values,
                    stop_event=stop_event,
                )
                if confirmed_tag is None:
                    if stop_event.is_set():
                        return "stopped", None, None
                    status_callback("Ball confirmation timed out")
                    return "timeout", None, None

            cycle_values.append(confirmed_tag)
            previous_visible_tags = visible_tags
            print(f"Step {step + 1} confirmed value: {confirmed_tag}")
            if drawn_values_callback is not None:
                drawn_values_callback(",".join(cycle_values))

            if sleep_interruptible(BALL_STEP_PAUSE, stop_event):
                return "stopped", None, None

        print("Examining data collection", flush=True)
        count = len(cycle_values)
        if cycle_values:
            csv_row = f"{cycle_timestamp}\t{','.join(cycle_values)}"
        else:
            csv_row = cycle_timestamp
        return "ok", count, csv_row

    # Return the machine to a safe state and record the completion reason.
    def shutdown(self, reason, stop_event=None):
        print(f"Stopping all systems ({reason})")
        motor_stop()
        print("Full actuator retraction before shutdown")
        actuator_retract()
        time.sleep(FULL_RETRACTION_TIME)
        actuator_stop()
        log_completion(reason)

    # Release all hardware resources after the run has ended.
    def cleanup(self):
        actuator_stop()
        motor_stop()
        gpio_cleanup()
        self.camera.close()
        print("Clean shutdown")

    # Stop actuator and motor outputs if normal worker shutdown is stuck.
    def emergency_stop(self):
        actuator_stop()
        motor_stop()
