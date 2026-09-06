import RPi.GPIO as GPIO

ACT_IN1 = 19
ACT_IN2 = 26
MOTOR_IN1 = 20
MOTOR_IN2 = 21


# Configure the motor-controller GPIO pins.
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ACT_IN1, GPIO.OUT)
    GPIO.setup(ACT_IN2, GPIO.OUT)
    GPIO.setup(MOTOR_IN1, GPIO.OUT)
    GPIO.setup(MOTOR_IN2, GPIO.OUT)


# Drive the actuator outward.
def actuator_extend():
    GPIO.output(ACT_IN1, GPIO.HIGH)
    GPIO.output(ACT_IN2, GPIO.LOW)


# Drive the actuator inward.
def actuator_retract():
    GPIO.output(ACT_IN1, GPIO.LOW)
    GPIO.output(ACT_IN2, GPIO.HIGH)


# Stop actuator movement.
def actuator_stop():
    GPIO.output(ACT_IN1, GPIO.LOW)
    GPIO.output(ACT_IN2, GPIO.LOW)


# Start the ball motor.
def motor_run():
    GPIO.output(MOTOR_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_IN2, GPIO.LOW)


# Stop the ball motor.
def motor_stop():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.LOW)


# Release all GPIO resources.
def gpio_cleanup():
    GPIO.cleanup()
