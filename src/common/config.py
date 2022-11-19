#!/usr/bin/python3

# Storage settings
CONTAINER_NAME = "thecontainer"
TIMELAPSE_NAME = "annolapse1"
LOCAL_IMAGES_BASE_PATH = "/home/pi/timelapse_data"

# Capture settings
CAMERA_ISO = 200
INTERVAL_SEC = 60
SHUTTER_SPEED_PERCENTS = [20, 50, 100, 200, 500]

# Viewfinder settings
DEFAULT_VIEWFINDER_PORT = 80

# Options for post processor
POST_PROCESSING_PATH = r"/mnt/r/Mirror"
