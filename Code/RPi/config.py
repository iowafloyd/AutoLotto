from pathlib import Path


# Store results in the project folder.
RESULTS_DIR = Path(__file__).resolve().parents[2] / "Results"

# Hardware timings and GUI runtime defaults.
FULL_EXTENSION_TIME = 5.0
FULL_RETRACTION_TIME = 6.0
BALL_STEP_TIME = 25.0 / 47.0
BALL_STEP_REST_TIME = 4 * BALL_STEP_TIME # Actuator duty cycle is 25% (4:1 rest:active). 4X rest time gives extra margin of error
BALL_STEP_PAUSE = BALL_STEP_TIME * 3.0 # Actuator cool-down time
NUM_STEPS = 5
MOTOR_RUN_TIME = 10 # Approx. 2X actuator duty time, to allow for actuator cool-down
MOTOR_JOG_TIME = 1.5
DEFAULT_RUNTIME_MINUTES = 15
RUNTIME_STEP_MINUTES = 15
