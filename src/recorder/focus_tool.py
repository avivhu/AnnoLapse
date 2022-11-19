# A utility to help focus a mnaul-focus lens.
# The program measures the focus and and prints the measure.
# Manually twist the lens until the focus measure is maximized.
from picamera.array import PiRGBArray
from picamera import PiCamera
import recorder.focus_measure as focus_measure
import cv2
import numpy as np
import time
import common.utils as utils

# Define the region of the image on which we calculate the focus.
# It is a fraction of the total image width,height.
# For example, ROI=0.5 defines a centered rectangle with area
# (.5)x(.5) of the image area.
ROI = 0.2
INTERVAL_SEC = 1

with PiCamera() as camera:
    camera.resolution = (utils.DEFAULT_WIDTH, utils.DEFAULT_HEIGHT)
    camera.start_preview()
    time.sleep(1)
    with PiRGBArray(camera) as stream:
        while True:
            camera.capture(stream, format="bgr")

            # At this point the image is available as stream.array
            image = np.copy(stream.array)
            stream.truncate(0)

            # Crop center
            size_hw = np.array(image.shape[:2])
            tl = (size_hw * (1 / 2.0 - ROI / 2.0)).astype(int)
            br = (tl + ROI * size_hw).astype(int)
            cropped = image[tl[0] : br[0], tl[1] : br[1], :]

            # Use the center channel (green) as it's the best among RGB to measure intensity.
            cropped = np.copy(cropped[:, :, 1])

            focus_measure = focus_measure.LAPV(cropped)
            print(focus_measure)

            cv2.rectangle(image, tl[::-1], br[::-1], [255, 255, 255], thickness=3)
            cv2.imwrite("/tmp/im.bmp", image)
            cv2.imwrite("/tmp/crop.bmp", cropped)
            time.sleep(INTERVAL_SEC)
