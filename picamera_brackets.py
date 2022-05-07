from time import sleep
from picamera import PiCamera
import numpy as np

camera = PiCamera(resolution=(1280, 720), framerate=2)

# Set ISO to the desired value
camera.iso = 200

# Wait for the automatic gain control to settle
sleep(5)

# Now fix the values
base_speed = camera.exposure_speed
camera.shutter_speed = camera.exposure_speed
camera.exposure_mode = "off"
awb_gains = camera.awb_gains
camera.awb_mode = "off"
camera.awb_gains = awb_gains

shutter_speed_factors = [0.2, 0.5, 1, 2, 5]

# Finally, take several photos with the fixed settings
for i, speed_factor in enumerate(shutter_speed_factors):
    desired_speed = round(speed_factor * base_speed)
    camera.shutter_speed = desired_speed

    # Need to wait for the command to take effect
    sleep(1)
    camera.capture("/home/pi/images2/image%02d.jpg" % i)
    print(
        i,
        speed_factor,
        camera.framerate,
        desired_speed / 1000,
        camera.exposure_speed / 1000,
    )
