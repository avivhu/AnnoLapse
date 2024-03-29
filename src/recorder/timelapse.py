#!/usr/bin/python3
import subprocess
from datetime import datetime
from pathlib import Path
import time
from typing import Optional
from dotenv import load_dotenv
import argparse
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from picamera.camera import PiCamera
from common.storage import upload_to_remote_storage
from common.utils import capture_still, DEFAULT_FRAME_WH
import json
import src.common.config as config


def get_image_out_path(dst_dir, series_datetime: datetime, shutter_speed_percent: int):
    # Return image file and directory.
    # Group images by date and by exposure series:
    #   2022-05-07 / 2022-05-07T11-49-40 / 2022-05-07T11-49-40--shutter_100.jpg
    datetime_str = series_datetime.isoformat()

    # Format time string with punctuation that can be in a file name
    datetime_str = datetime_str.replace(":", "-")
    date_str = datetime_str.split("T")[0]
    out_file = (
        dst_dir
        / date_str
        / datetime_str
        / f"{datetime_str}--shutter_{shutter_speed_percent:03d}.jpg"
    )
    return out_file, datetime_str


def capture_picamera_method(dst_dir: Path):

    # Get time, which we'll use to name the output images series
    series_datetime = datetime.utcnow().replace(microsecond=0)

    with PiCamera(resolution=DEFAULT_FRAME_WH, framerate=2) as camera:
        # Set ISO
        camera.iso = config.CAMERA_ISO

        # Wait for the automatic gain control to settle
        time.sleep(5)

        # Now fix the values
        base_speed = camera.exposure_speed
        camera.shutter_speed = camera.exposure_speed
        camera.exposure_mode = "off"
        awb_gains = camera.awb_gains
        camera.awb_mode = "off"
        camera.awb_gains = awb_gains

        # Finally, take several photos with the fixed settings
        for i, shutter_speed_percent in enumerate(config.SHUTTER_SPEED_PERCENTS):
            desired_speed = round(shutter_speed_percent / 100.0 * base_speed)
            camera.shutter_speed = desired_speed

            # Need to wait for the command to take effect
            time.sleep(1)
            out_fname, image_series_name = get_image_out_path(
                dst_dir, series_datetime, shutter_speed_percent
            )
            out_fname.parent.mkdir(parents=True, exist_ok=True)

            camera.capture(str(out_fname))

            props = {
                "series_name": image_series_name,
                "index": i,
                "filename": str(out_fname),
                "shutter_speed_percent": shutter_speed_percent,
                "camera.framerate": repr(camera.framerate),
                "desired_speed": desired_speed / 1000,
                "camera.exposure_speed": camera.exposure_speed / 1000,
            }

            logging.info(f"Capture: {str(props)}", extra={"custom_dimensions": props})

    return image_series_name


def upload_files_and_delete(timelapse_name, local_dir):
    upload_to_remote_storage(
        container_name=config.CONTAINER_NAME,
        source=str(local_dir),
        dest=f"{timelapse_name}/images",
        delete=True,
    )


def main():
    print("Starting recorder")
    load_dotenv()

    # Set up logging to Azure Application Insights
    # See: https://docs.microsoft.com/en-us/azure/azure-monitor/app/opencensus-python
    # Instantiate the exporter directly from the environment variable
    # `APPLICATIONINSIGHTS_CONNECTION_STRING`
    logging.basicConfig(
        level=logging.INFO,
        # format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            AzureLogHandler(),
        ],
    )
    logging.info("Recorder logging enabled")

    # Silence this spammy logger.
    # See: https://stackoverflow.com/questions/52051501/azure-blob-storage-sdk-switch-off-logging
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
        logging.WARNING
    )

    local_images_dir = Path(
        f"{config.LOCAL_IMAGES_BASE_PATH}/{config.TIMELAPSE_NAME}/images"
    )
    local_images_dir.mkdir(parents=True, exist_ok=True)

    prev_time: Optional[datetime] = None
    while True:
        if prev_time is not None:

            # Wait for the remainder of the interval
            elapsed = (datetime.now() - prev_time).total_seconds()
            remainder = config.INTERVAL_SEC - elapsed
            if remainder > 0:
                logging.info(f"Waiting for next series: {remainder:.1f} seconds")
                time.sleep(remainder)

        prev_time = datetime.now()

        try:
            # Capture image HDR sequence (aka bracket)
            image_series_name = capture_picamera_method(local_images_dir)

            # Upload latest and delete. If we can't upload, we store and try again later
            upload_files_and_delete(config.TIMELAPSE_NAME, local_images_dir)

            logging.info(
                f"Captured and uploaded image series {image_series_name}",
                extra={"custom_dimensions": {"series_name": image_series_name}},
            )

        except Exception as ex:
            logging.error("Error in timelapse capture", ex)


def run_viewfinder(port: int):
    cmd = f'mjpg_streamer -i "input_raspicam.so -x 512 -y 384 -fps 2 -rot 180 -ex auto" -o "output_http.so -p {port}"'
    r = subprocess.run(cmd, shell=True)
    r.wait()


def _get_hostname():
    return subprocess.check_output("hostname", text=True).strip()


def _get_viewfinder_url(port: int):
    return "http://{}:{}/?action=stream".format(_get_hostname(), port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--view",
        help="Start live video (viewfinder). It may be accessed over http",
        action="store_true",
    )
    parser.add_argument(
        "--port",
        default=config.DEFAULT_VIEWFINDER_PORT,
        help="Port for viewfinder service",
    )
    args = parser.parse_args()

    if args.view:
        print("Running viewfinder in " + _get_viewfinder_url(args.port))
        run_viewfinder(args.port)
    else:
        main()
