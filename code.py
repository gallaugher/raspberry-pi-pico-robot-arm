# nudge_robot_arm.py
# Cheap servos will jitter on their own, so this code will stop servos when they shouldn't be moving
# This is accomplished by cutting PWM signal by sending a None, effectively turning off a servo between movements.
# Uses concepts of EMA - Exponential Moving Average - instead of responding to instant joystick reading.
# This prevents jitter by reducing abrupt movements from a single reading. Average of readings is smoother than one reading.
# Designed to work with a self-centering joystick, so a nudge in one direction moves servos in that direction
# as opposed to moving servos where joystick is positioned & requiring the user to "hold" the position
# against any tension to push joystick back to center. A good UX choice for platform positioning where
# one might want to "nudge" the movement slightly in one direction or another.
# Also increases acceleration based on how far the joystick is from center. Further = faster movement.
# By: Prof. John Gallaugher
# Find Build Video (and much more) at YouTube.com/@BuildWithProfG
# github.com/gallaugher - @gallaugher.bsky.social - @gallaugher@mastodon.world

import time, board, analogio, pwmio, digitalio
from adafruit_motor import servo

# Setup Servos
pwm_x = pwmio.PWMOut(board.GP14, frequency=50)       # X axis (shoulder)
servo_x = servo.Servo(pwm_x, min_pulse=650, max_pulse=2350)

pwm_y = pwmio.PWMOut(board.GP15, frequency=50)       # Y axis (elbow)
servo_y = servo.Servo(pwm_y, min_pulse=650, max_pulse=2350)

pwm_claw = pwmio.PWMOut(board.GP13, frequency=50)    # Claw
servo_claw = servo.Servo(pwm_claw, min_pulse=650, max_pulse=2350)

pwm_base = pwmio.PWMOut(board.GP12, frequency=50)    # Base rotation
servo_base = servo.Servo(pwm_base, min_pulse=500, max_pulse=2500)

# Set initial angles
servo_x.angle = 90
servo_y.angle = 90
servo_claw.angle = 90
servo_base.angle = 0

# Disable joystick-controlled servos after positioning to prevent startup jitter
servo_x.angle = None
servo_y.angle = None

# Setup Joystick Analog Inputs
x_axis = analogio.AnalogIn(board.A0)  # GP26
y_axis = analogio.AnalogIn(board.A1)  # GP27

# Setup Claw Buttons
claw_open_btn = digitalio.DigitalInOut(board.GP16)
claw_open_btn.switch_to_input(pull=digitalio.Pull.UP)

claw_closed_btn = digitalio.DigitalInOut(board.GP17)
claw_closed_btn.switch_to_input(pull=digitalio.Pull.UP)

# Setup Base Rotation Buttons
base_right_btn = digitalio.DigitalInOut(board.GP18)
base_right_btn.switch_to_input(pull=digitalio.Pull.UP)

base_left_btn = digitalio.DigitalInOut(board.GP19)
base_left_btn.switch_to_input(pull=digitalio.Pull.UP)

# Calculation Constants
MAX_SERVO = 180
MAX_JOYSTICK = 65535
CENTER_JOYSTICK = int(65535 / 2)
CENTER_SERVO = int(MAX_SERVO / 2)
deadband_pct = 0.08
deadband = MAX_JOYSTICK * deadband_pct

# Safety limits to avoid servo endpoints
MIN_ANGLE = 5
MAX_ANGLE = 175

# Joystick EMA filter alphas
JOY_FILTER_ALPHA = 0.25
Y_FILTER_ALPHA = 0.15

# X-axis servo control variables
current_x_angle = 90
last_x_angle_sent = 90
last_x_reading = CENTER_JOYSTICK
current_x_side = None
last_x_movement_time = time.monotonic()
x_servo_enabled = True

# Y-axis servo control variables
current_y_angle = 90
last_y_angle_sent = 90
last_y_reading = CENTER_JOYSTICK
current_y_side = None
last_y_movement_time = time.monotonic()
y_servo_enabled = True

# Speed control
servo_timeout = 0.015

# X-axis speeds
x_min_speed = 0.02
x_max_speed = 0.10

# Y-axis speeds
y_min_speed = 0.02
y_max_speed = 0.10
y_speed_decay = 0.7

# Servo update threshold
servo_update_threshold = 0.3

# Acceleration limiting for Y-axis
max_y_accel = 1.5
last_y_speed = 0

# Base and claw step size for button control
ANGLE_STEP = 3

# Filtered joystick values
x_filt = x_axis.value
y_filt = y_axis.value

print("Code Running!")
while True:
    # Read & filter joystick
    xr = x_axis.value
    yr = y_axis.value

    x_filt = (1 - JOY_FILTER_ALPHA) * x_filt + JOY_FILTER_ALPHA * xr
    y_filt = (1 - Y_FILTER_ALPHA) * y_filt + Y_FILTER_ALPHA * yr

    x_reading = int(x_filt)
    y_reading = int(y_filt)

    # X-Axis Control
    if x_reading < CENTER_JOYSTICK - deadband:
        current_x_side = 'left'
    elif x_reading > CENTER_JOYSTICK + deadband:
        current_x_side = 'right'
    else:
        current_x_side = None

    x_degrees_per_step = x_min_speed
    if current_x_side is not None:
        distance_from_center = abs(x_reading - CENTER_JOYSTICK)
        max_distance = CENTER_JOYSTICK - deadband
        speed_factor = distance_from_center / max_distance
        x_degrees_per_step = x_min_speed + (speed_factor * (x_max_speed - x_min_speed))

    if current_x_side == 'left' and x_reading < last_x_reading:
        current_x_angle = min(MAX_ANGLE, current_x_angle + x_degrees_per_step)
    elif current_x_side == 'right' and x_reading > last_x_reading:
        current_x_angle = max(MIN_ANGLE, current_x_angle - x_degrees_per_step)

    if abs(current_x_angle - last_x_angle_sent) >= servo_update_threshold:
        servo_x.angle = round(current_x_angle)
        last_x_angle_sent = current_x_angle
        last_x_movement_time = time.monotonic()
        if not x_servo_enabled:
            x_servo_enabled = True
        print(f"X: {x_reading}, Side: {current_x_side}, Angle: {current_x_angle:.1f}, Speed: {x_degrees_per_step:.1f}")

    if x_servo_enabled and (time.monotonic() - last_x_movement_time) > servo_timeout:
        servo_x.angle = None
        x_servo_enabled = False

    last_x_reading = x_reading

    # Y-Axis Control
    if y_reading < CENTER_JOYSTICK - deadband:
        current_y_side = 'up'
    elif y_reading > CENTER_JOYSTICK + deadband:
        current_y_side = 'down'
    else:
        current_y_side = None

    y_degrees_per_step = y_min_speed
    if current_y_side is not None:
        distance_from_center = abs(y_reading - CENTER_JOYSTICK)
        max_distance = CENTER_JOYSTICK - deadband
        speed_factor = distance_from_center / max_distance
        desired_y_speed = y_min_speed + (speed_factor * (y_max_speed - y_min_speed))

        speed_change = desired_y_speed - last_y_speed
        if abs(speed_change) > max_y_accel:
            speed_change = max_y_accel if speed_change > 0 else -max_y_accel

        y_degrees_per_step = last_y_speed + speed_change
        last_y_speed = y_degrees_per_step
    else:
        last_y_speed = last_y_speed * y_speed_decay

    if current_y_side == 'up' and y_reading < last_y_reading:
        current_y_angle = min(MAX_ANGLE, current_y_angle + y_degrees_per_step)
    elif current_y_side == 'down' and y_reading > last_y_reading:
        current_y_angle = max(MIN_ANGLE, current_y_angle - y_degrees_per_step)

    if abs(current_y_angle - last_y_angle_sent) >= servo_update_threshold:
        servo_y.angle = round(current_y_angle)
        last_y_angle_sent = current_y_angle
        last_y_movement_time = time.monotonic()
        if not y_servo_enabled:
            y_servo_enabled = True
        print(f"Y: {y_reading}, Side: {current_y_side}, Angle: {current_y_angle:.1f}, Speed: {y_degrees_per_step:.1f}")

    if y_servo_enabled and (time.monotonic() - last_y_movement_time) > servo_timeout:
        servo_y.angle = None
        y_servo_enabled = False

    last_y_reading = y_reading

    # Base Rotation - button controlled
    if not base_right_btn.value:
        servo_base.angle = int(max(0, servo_base.angle - ANGLE_STEP))
        print(f"Base right: {servo_base.angle}")
    elif not base_left_btn.value:
        servo_base.angle = int(min(180, servo_base.angle + ANGLE_STEP))
        print(f"Base left: {servo_base.angle}")
    else:
        servo_base.angle = None  # Kill PWM when not moving to reduce jitter

    # Claw - two separate buttons, open and close
    if not claw_open_btn.value:
        servo_claw.angle = int(min(100, servo_claw.angle + ANGLE_STEP)) if servo_claw.angle is not None else 90
        print(f"Claw open: {servo_claw.angle}")
    elif not claw_closed_btn.value:
        servo_claw.angle = int(max(0, servo_claw.angle - ANGLE_STEP)) if servo_claw.angle is not None else 90
        print(f"Claw closed: {servo_claw.angle}")
    else:
        servo_claw.angle = None  # Kill PWM when not moving to reduce jitter
