import subprocess
import logging


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
def run_command(cmd):
    logging.debug(f"Running command: {cmd}")
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    while True:
        line = process.stdout.readline()
        if line:
            print(line.decode("utf-8").rstrip())
        if process.poll() is not None:
            break
    process.wait()
    if process.returncode != 0:
        raise Exception(f"Command failed: {cmd}")
