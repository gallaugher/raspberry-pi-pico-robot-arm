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
from adafruit_debouncer import Button

# Setup Servos - you can tinker with min & max, but these are good ranges and "perfect" 0 to 180° swings aren't as critical in the launcher.
pwm_base = pwmio.PWMOut(board.GP13, frequency=50)  # X axis (pan)
servo_base = servo.Servo(pwm_base, min_pulse=650, max_pulse=2350)
pwm_elbow = pwmio.PWMOut(board.GP12, frequency=50)  # Y axis (tilt)
servo_elbow = servo.Servo(pwm_elbow, min_pulse=650, max_pulse=2350)
pwm_claw = pwmio.PWMOut(board.GP11, frequency=50)  # Launch
servo_claw = servo.Servo(pwm_claw, min_pulse=650, max_pulse=2350)

# Set initial angles at 90°
servo_base.angle = 90
servo_elbow.angle = 90
servo_claw.angle = 90
claw_open = False

# Disable servos after positioning to prevent startup jitter
servo_base.angle = None
servo_elbow.angle = None
servo_claw.angle = None

# Setup Joysticks on Pico Analog Pins (remember a joystick is just two potentiometers)
x_axis = analogio.AnalogIn(board.A0)  # GP27
y_axis = analogio.AnalogIn(board.A1)  # GP26

# Setup Launch Button
button_input = digitalio.DigitalInOut(board.GP6)
button_input.switch_to_input(digitalio.Pull.UP)
button = Button(button_input)

# Calculation Constants
MAX_SERVO = 180 # Moves 180° max
MAX_JOYSTICK = 65535 # Servo maximum value
CENTER_JOYSTICK = int(65535 / 2)
CENTER_SERVO = int(MAX_SERVO / 2)
deadband_pct = 0.08 # The % where a reading shift won't trigger a movement. Prevents some jitter.
deadband = MAX_JOYSTICK * deadband_pct # at 8% this should be 4% on either side. You can change & experiment

# Safety limits to avoid servo endpoints. Not critical, but may take some "whine" out & avoid tinkering w/min-max pulse values.
MIN_ANGLE = 5
MAX_ANGLE = 175

# Joystick filtering used in formula (there's one for both x & y values in while True:
#     x_filt = (1 - JOY_FILTER_ALPHA) * x_filt + JOY_FILTER_ALPHA * xr
#     y_filt = (1 - Y_FILTER_ALPHA) * y_filt + Y_FILTER_ALPHA * yr  # Heavier Y filter
# Higher alpha (closer to 1.0) = more responsive, less filtering (new readings have more weight)
# Lower alpha (closer to 0.0) = more filtering, smoother but less responsive (old values persist more)
JOY_FILTER_ALPHA = 0.25  # X-axis filter - 25% new reading + 75% old filtered value (moderate filtering)
Y_FILTER_ALPHA = 0.15  # Y-axis heavier filtering (smoother) - 15% new reading + 85% old filtered value (heavier filtering)

# X-axis servo control variables
current_x_angle = 90
last_x_angle_sent = 90
last_x_reading = CENTER_JOYSTICK
current_x_side = None
last_x_movement_time = time.monotonic()
x_servo_enabled = True

# Y-axis servo control variables
current_y_angle = 90 # Start straight up
last_y_angle_sent = 90 # Saving this prevents redundant updates
last_y_reading = CENTER_JOYSTICK # This will detect direction changes - start in center for self-centering joystick
current_y_side = None # 3 readings for joystick push: 'up', 'down', or None (centered - None is a null value, not a String)
last_y_movement_time = time.monotonic() # Timestamp of last servo movement (for auto-disable timeout)
y_servo_enabled = True # Will set to False to prevent jitter

# Speed control - how quickly servo turns off after a move. Stops any jitter.
servo_timeout = 0.015 # increase for smoothness, reduce if you have excessive jitter

# X-axis speeds - base seems to be able to move faster
x_min_speed = 0.05
x_max_speed = 0.25

# Y-axis speeds - cheap servos have a hard time with weight of platform. Slower speed helps a bit
y_min_speed = 0.05
y_max_speed = 0.25
y_speed_decay = 0.7  # When joystick centered, speed gradually reduces to zero (multiply by this each loop). Higher = slower coast to stop

# Servo only gets updated when the angle has changed by at least 0.3 degrees (output filter)
# This is vs. the deadband, which is for the joystick reading (input filter)
servo_update_threshold = 0.3  # Minimum degree change before updating servo. Increase = less jitter but less responsive

# Acceleration limiting for Y-axis - prevents sudden jumps
max_y_accel = 1.5  # Max change in speed per loop iteration
last_y_speed = 0

# Filtered joystick values
x_filt = x_axis.value
y_filt = y_axis.value

print("Code Running!")
while True:
    # Read & filter joystick
    xr = x_axis.value
    yr = y_axis.value

    # Exponential moving average filter
    x_filt = (1 - JOY_FILTER_ALPHA) * x_filt + JOY_FILTER_ALPHA * xr
    y_filt = (1 - Y_FILTER_ALPHA) * y_filt + Y_FILTER_ALPHA * yr  # Smoother but less responsive

    # Use the filtered readings (smoothed above via EMA - Exponential Moving Average) for servo control
    x_reading = int(x_filt)
    y_reading = int(y_filt)

    # X-Axis Control - record if stick is being moved to left or right (within deadband)
    if x_reading < CENTER_JOYSTICK - deadband:
        current_x_side = 'left'
    elif x_reading > CENTER_JOYSTICK + deadband:
        current_x_side = 'right'
    else:
        current_x_side = None

    # Increases speed of x-movement the further the joystick from center.
    x_degrees_per_step = x_min_speed
    if current_x_side is not None:
        distance_from_center = abs(x_reading - CENTER_JOYSTICK)
        max_distance = CENTER_JOYSTICK - deadband
        speed_factor = distance_from_center / max_distance
        x_degrees_per_step = x_min_speed + (speed_factor * (x_max_speed - x_min_speed))

    # Update servo angle only if joystick *continues moving* in same direction (prevents reversals)
    if current_x_side == 'left' and x_reading < last_x_reading:
        current_x_angle = min(MAX_ANGLE, current_x_angle + x_degrees_per_step) # Move left, constrain at max limit
    elif current_x_side == 'right' and x_reading > last_x_reading:
        current_x_angle = max(MIN_ANGLE, current_x_angle - x_degrees_per_step) # Move right, constrain at min limit

    # If angle change exceeds threshold, send new angle to servo and re-enable if needed
    if abs(current_x_angle - last_x_angle_sent) >= servo_update_threshold:
        servo_base.angle = round(current_x_angle) # Send angle command to servo
        last_x_angle_sent = current_x_angle # Track what we sent
        last_x_movement_time = time.monotonic() # Reset timeout timer
        if not x_servo_enabled:
            x_servo_enabled = True
            print("X-Servo re-enabled")
        print(f"X: {x_reading}, Side: {current_x_side}, Angle: {current_x_angle:.1f}, Speed: {x_degrees_per_step:.1f}")

    # If the servo is enabled, but we've exceeded the servo_timeout period, then cut PWM signal by sending a None
    # This effectively "turns off" the servo so it won't jitter on its own
    if x_servo_enabled and (time.monotonic() - last_x_movement_time) > servo_timeout:
        servo_base.angle = None  # Disables the PWM signal, effectively shutting off the servo
        x_servo_enabled = False  # Record that the servo is "off" so we can turn it on again when next valid movement detected
        print("X-Servo disabled (holding position)")  # For debugging so you can see when this happens

    last_x_reading = x_reading # update last reading to the current reading

    # Y-Axis control - record if joystick is being moved 'up' or 'down' or not (None).
    if y_reading < CENTER_JOYSTICK - deadband:
        current_y_side = 'up'
    elif y_reading > CENTER_JOYSTICK + deadband:
        current_y_side = 'down'
    else:
        current_y_side = None

    # Calculate speed with Y-specific limits
    y_degrees_per_step = y_min_speed
    if current_y_side is not None:
        distance_from_center = abs(y_reading - CENTER_JOYSTICK)
        max_distance = CENTER_JOYSTICK - deadband
        speed_factor = distance_from_center / max_distance
        desired_y_speed = y_min_speed + (speed_factor * (y_max_speed - y_min_speed))

        # Apply acceleration limiting to prevent sudden jumps (Y-axis & cheap servos seem to need this likely due to platform weight causing jitter)
        speed_change = desired_y_speed - last_y_speed
        if abs(speed_change) > max_y_accel:
            speed_change = max_y_accel if speed_change > 0 else -max_y_accel

        y_degrees_per_step = last_y_speed + speed_change
        last_y_speed = y_degrees_per_step
    else:
        # When centered, gradually reduce speed to zero
        last_y_speed = last_y_speed * y_speed_decay

    # Update servo angle only if joystick *continues moving* in same direction (prevents reversals)
    if current_y_side == 'up' and y_reading < last_y_reading:
        current_y_angle = min(MAX_ANGLE, current_y_angle + y_degrees_per_step) # Move up, enforce max limit
    elif current_y_side == 'down' and y_reading > last_y_reading:
        current_y_angle = max(MIN_ANGLE, current_y_angle - y_degrees_per_step) # Move down, enforce min limit

    # If angle change exceeds threshold, send new angle to servo and re-enable if needed
    if abs(current_y_angle - last_y_angle_sent) >= servo_update_threshold:
        servo_elbow.angle = round(current_y_angle)  # Send angle command to servo
        last_y_angle_sent = current_y_angle  # Track what we sent
        last_y_movement_time = time.monotonic()  # Reset timeout timer
        if not y_servo_enabled:
            y_servo_enabled = True
            print("Y-Servo re-enabled")
        print(f"Y: {y_reading}, Side: {current_y_side}, Angle: {current_y_angle:.1f}, Speed: {y_degrees_per_step:.1f}")

    last_y_reading = y_reading  # Update last reading to the current reading

    button.update()  # Launch button is debounced. Updating is essential to get latest state
    if button.pressed:  # If pressed, launch by immediately moving to 0°
        claw_open = not claw_open
        print(f"Button pressed & claw is {"open" if claw_open else "closed"}")
        if claw_open:
            servo_claw.angle = 0
        else:
            servo_claw.angle = 90
        time.sleep(0.25)
        servo_claw.angle = None  # Disable launch servo to prevent jitter