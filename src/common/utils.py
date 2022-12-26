from datetime import datetime
import subprocess
import logging
from dateutil import tz

FULL_WIDTH = 3280
FULL_HEIGHT = 2464

DEFAULT_FRAME_WH = (3280 // 2, 2464 // 2)


def capture_still(
    out_file, width=DEFAULT_FRAME_WH[0], height=DEFAULT_FRAME_WH[1], ev=0
):
    cmd = f"raspistill -o {str(out_file)} -w {width} -h {height} --raw -ev {ev}"
    print(cmd)
    subprocess.check_output(cmd, shell=True)


def capture_raspistill_method(dst_dir, time_str):
    exposures = [-10, -5, 0, 5]
    for ev in exposures:
        out_file = dst_dir / f"{time_str}--ev_{ev:+03d}.jpg"
        capture_still(out_file, ev=ev)


# Run command and show its stdout in real time
# Throw if error
def run_command(cmd, print_output: bool = True):
    logging.info(f"Running command: {cmd}")
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
    )
    while True:
        line = process.stdout.readline()
        if line and print_output:
            print(line.decode("utf-8").rstrip())
        if process.poll() is not None:
            break
    process.wait()
    if process.returncode != 0:
        raise Exception(f"Command failed: {cmd}")


def compute_local_time(utc: datetime, local_tz: str):
    # Get local time
    # See https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime
    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz(local_tz)

    # Tell the datetime object that it's in UTC time zone since
    # datetime objects are 'naive' by default
    utc = utc.replace(tzinfo=from_zone)

    # Convert time zone
    local_time = utc.astimezone(to_zone)
    return local_time


def image_set_id_to_time(image_set_id: str):
    # Parse string such as 2022-12-23T10-21-18
    # into a datetime object
    utc_time = datetime.strptime(image_set_id, "%Y-%m-%dT%H-%M-%S")
    return utc_time


def _test():
    atime = image_set_id_to_time("2022-12-23T10-21-18")
    res = compute_local_time(atime, "Asia/Jerusalem")
    assert res.hour == 12


if __name__ == "__main__":
    _test()
