from pathlib import Path


# Store results in the project folder.
RESULTS_DIR = Path(__file__).resolve().parents[2] / "Results"

# Hardware timings and GUI runtime defaults.
FULL_EXTENSION_TIME = 5.0
FULL_RETRACTION_TIME = 6.0
BALL_STEP_TIME = 25.0 / 47.0
BALL_STEP_REST_TIME = 3 * BALL_STEP_TIME
BALL_STEP_PAUSE = 0.2
NUM_STEPS = 5
MOTOR_RUN_TIME = 7.5
MOTOR_JOG_TIME = 1.5
DEFAULT_RUNTIME_MINUTES = 15
RUNTIME_STEP_MINUTES = 15
