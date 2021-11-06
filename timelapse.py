#!/usr/bin/python3
import subprocess
from datetime import datetime
from pathlib import Path
import time

width = 3280//2
height = 2464//2
exposures = [-10, -5, 0, 5]

time_str = datetime.now().replace(microsecond=0).isoformat()
time_str = time_str.replace(':', '-')

dst_dir = Path('~/images')

period_sec = 60*1 # Every minute

while True:
    for ev in exposures:
        out_file = dst_dir / f'{time_str}--ev_{ev:+03d}.jpg'
        cmd = f'raspistill -o {str(out_file)} -w {width} -h {height} -rot 180 --raw -ev {ev}'
        print(cmd)
        subprocess.check_output(cmd, shell=True)
    time.sleep(period_sec)
