#!/usr/bin/python3
import subprocess
from datetime import datetime
from pathlib import Path
import time
from dotenv import load_dotenv
import argparse


from picamera.camera import PiCamera
from storage import upload_to_remote_storage
from utils import capture_still, DEFAULT_FRAME_WH
import settings

def get_image_fname(dst_dir, time_str, shutter_speed_percent):
    out_file = dst_dir / f'{time_str}--shutter_{shutter_speed_percent:03d}.jpg'
    return out_file


def capture_picamera_method(dst_dir: Path, time_str: str):
    with PiCamera(resolution=DEFAULT_FRAME_WH, framerate=2) as camera:
        # Set ISO to the desired value
        camera.iso = settings.CAMERA_ISO

        # Wait for the automatic gain control to settle
        time.sleep(5)

        # Now fix the values
        base_speed = camera.exposure_speed
        camera.shutter_speed = camera.exposure_speed
        camera.exposure_mode = 'off'
        awb_gains = camera.awb_gains
        camera.awb_mode = 'off'
        camera.awb_gains = awb_gains

        shutter_speed_percents = [20, 50, 100, 200, 500]

        # Finally, take several photos with the fixed settings
        for i, shutter_speed_percent in enumerate(shutter_speed_percents):
            desired_speed = round(shutter_speed_percent / 100.0 * base_speed)
            camera.shutter_speed = desired_speed

            # Need to wait for the command to take effect
            time.sleep(1)
            out_fname = get_image_fname(dst_dir, time_str, shutter_speed_percent)
            camera.capture(str(out_fname))
            print(i, str(out_fname), shutter_speed_percent, camera.framerate, desired_speed/1000, camera.exposure_speed/1000)


def upload_files_and_delete(timelapse_name, local_dir):
    upload_to_remote_storage(container_name=settings.CONTAINER_NAME, source=str(local_dir), dest=f'{timelapse_name}/images', delete=True)


def main():
    print('Capturing timelapse')
    load_dotenv()

    local_images_dir = Path(f'{settings.LOCAL_IMAGES_BASE_PATH}/{settings.TIMELAPSE_NAME}/images')
    local_images_dir.mkdir(parents=True, exist_ok=True)
    period_sec = 60  # Every minute

    while True:
        # Format time string with punctuation that can be in a file name
        time_str = datetime.now().replace(microsecond=0).isoformat()
        time_str = time_str.replace(':', '-')

        # Capture image HDR sequence (aka bracket)
        capture_picamera_method(local_images_dir, time_str)

        try:
            # Upload latest and delete. If we can't upload, we store and try again later
            upload_files_and_delete(settings.TIMELAPSE_NAME, local_images_dir)
        except Exception as ex:
            print('Error uploading files: ', ex)

        # Wait for next sequence
        time.sleep(period_sec)

        
def run_viewfinder(port: int):
     cmd = f'mjpg_streamer -i "input_raspicam.so -x 512 -y 384 -fps 2 -rot 180 -ex night" -o "output_http.so -p {port}"'
     r = subprocess.run(cmd, shell=True)
     r.wait()

     
def _get_hostname():
    return subprocess.check_output('hostname', text=True).strip()


def _get_viewfinder_url(port: int):
    return 'http://{}:{}/?action=stream'.format(_get_hostname(), port)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--view', help='Start live video (viewfinder). It may be accessed over http', action="store_true")
    parser.add_argument('--port', default=80, help='Port for viewfinder service')
    args = parser.parse_args()

    if args.view:
        print('Running viewfinder in ' + _get_viewfinder_url(args.port))
        run_viewfinder(args.port)
    else:
        main()
        
