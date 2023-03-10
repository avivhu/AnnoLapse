#!/usr/bin/python3

# Storage settings
CONTAINER_NAME = "thecontainer"
TIMELAPSE_NAME = "annolapse1"

# Use save files to ramdisk to avoid wearing out the SD card.
# They are uploaded and then deleted anyway so we only need temporary storage.
# To set up ramdisk:
#   sudo mkdir -p /media/ramdisk
#   sudo mount -t tmpfs -o size=100M tmpfs /media/ramdisk
#   sudo chmod 1777 /media/ramdisk
#   grep /media/ramdisk /etc/mtab | sudo tee -a /etc/fstab
# See also: https://askubuntu.com/questions/152868/how-do-i-make-a-ram-disk
LOCAL_IMAGES_BASE_PATH = "/media/ramdisk/timelapse_data"

# Capture settings
CAMERA_ISO = 200
INTERVAL_SEC = 600
SHUTTER_SPEED_PERCENTS = [20, 50, 100, 200, 500]

# Viewfinder settings
DEFAULT_VIEWFINDER_PORT = 80
