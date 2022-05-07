#!/usr/bin/python3
from typing import List
from storage import _get_sas_key, download_files, get_latest_files
from pathlib import Path
import settings
import subprocess
import re
import collections
import pandas as pd
from utils import run_command


def post_production():
    get_latest_files(settings.CONTAINER_NAME, day="2022-03-10")


def create_hdr(src_files: List[Path], out_file: Path, method: str = "drago"):
    src_files_str = " ".join([str(x) for x in src_files])
    cmd = f"luminance-hdr-cli --tmo {method} -o {out_file} {src_files_str}"
    run_command(cmd)
    assert out_file.is_file()


if __name__ == "__main__":
    local_path = Path("../Mirror")
    download_files(
        settings.CONTAINER_NAME,
        date_prefix="2022-03-26",
        dst_dir=local_path,
        overwrite=False,
    )

    # List files, group by series
    base_dir = local_path / f"{settings.TIMELAPSE_NAME}/images"

    # Create regex to extract shutter number
    # Example: '2022-03-26T07-14-29--shutter_050.jpg' --> '2022-03-26T07-14-29, '050'
    pat_re = re.compile(r"(?P<time>.+?)--shutter_(?P<shutter>\d+?).jpg")
    data = collections.defaultdict(list)
    for f in list(base_dir.glob("*.jpg")):
        mm = pat_re.match(f.name)
        assert mm is not None
        data["shutter"].append(mm["shutter"])
        data["series"].append(mm["time"])
        data["path"].append(f.absolute())

    df = pd.DataFrame(data)
    NUM_IN_GROUP = 5  # Number of images in a group, one for each shutter value

    # Keep only full groups
    non_full = []
    for name, grp in df.groupby("series"):
        if len(grp) < NUM_IN_GROUP:
            print("Group is not full:", grp.series)
            non_full.append(name)

    df = df[~df.series.isin(non_full)]

    post_production_dir = Path("../PostProduction")
    post_production_dir.mkdir(parents=True, exist_ok=True)

    # For each group, create an HDR image
    for name, grp in df.groupby("series"):
        src_files = list(grp.path.values)
        hdr_methods = ["drago", "fattal"]
        for hdr_method in hdr_methods:
            out_file = Path(f"{post_production_dir}/{hdr_method}/{name}.jpg")
            out_file.parent.mkdir(exist_ok=True, parents=True)
            create_hdr(src_files, out_file, hdr_method)
