import os


# Store results on the operator's desktop.
DESKTOP_RESULTS_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "Results")

# Hardware timings and GUI runtime defaults.
FULL_EXTENSION_TIME = 5.0
FULL_RETRACTION_TIME = 6.0
BALL_STEP_TIME = 25.0 / 47.0
BALL_STEP_PAUSE = 0.2
NUM_STEPS = 5
MOTOR_RUN_TIME = 7.5
MOTOR_JOG_TIME = 1.5
DEFAULT_RUNTIME_MINUTES = 15
RUNTIME_STEP_MINUTES = 15
