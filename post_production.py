#!/usr/bin/python3
from typing import List
from tqdm import tqdm
from storage import sync_files, get_latest_files
from pathlib import Path
from tqdm import tqdm
import cv2
import settings
import re
import numpy as np
import pandas as pd
import collections
from dataclasses import dataclass
from utils import run_command
import datetime
from dateutil import tz
import dask.distributed as dd
import config
import argparse


def create_video_from_images(files: List[Path], out_file: Path):
    # with tempfile.TemporaryDirectory() as tmp_dir:
    #     list_file = Path(tmp_dir) / 'files.txt'
    #     with open(list_file, 'wt') as list_file_handle:
    #         for file in files:
    #             list_file_handle.write(f"file '{file}'\n")

    #     cmd = f"ffmpeg -y -f concat -safe 0 -i {str(list_file)} -c:v libx264 -r 30 -pix_fmt yuv420p {out_file}"
    #     run_command(cmd)
    #     assert out_file.is_file()

    frame_size = cv2.imread(str(files[0])).shape
    frame_size = frame_size[1], frame_size[0]
    writer = cv2.VideoWriter(str(out_file), cv2.VideoWriter_fourcc(*'mp4v'), 30, frame_size)
    for file in tqdm(files):
        frame = cv2.imread(str(file))
        writer.write(frame)
    writer.release()


def create_hdr(src_files: List[Path], out_file: Path, method: str = "drago"):
    src_files_str = " ".join([str(x) for x in src_files])
    cmd = f"luminance-hdr-cli --tmo {method} -o {out_file} {src_files_str}"
    run_command(cmd)
    assert out_file.is_file()

@dataclass
class ImageFile:
    src_path: Path
    shutter: int


@dataclass
class ImageSet:
    """A set same-time images with different exposures.
    """
    name: str
    files: List[ImageFile]


def process_single_exposure_set(image_set: ImageSet, processed_dir: Path):
    print(f"Processing {image_set.name}")
    set_out_dir = processed_dir / image_set.name
    if set_out_dir.exists():
        print(f"{image_set.name} already processed. skipping it")
        return
    for img_file in image_set.files:
        if img_file.shutter == 100:
            set_out_dir.mkdir(parents=True, exist_ok=True)

            img = cv2.imread(str(img_file.src_path))

            # Parse datetime from iso format
            utc = datetime.datetime.strptime(image_set.name, "%Y-%m-%dT%H-%M-%S")

            # Get local time
            # See https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime
            from_zone = tz.gettz('UTC')
            to_zone = tz.gettz('Asia/Jerusalem')

            # Tell the datetime object that it's in UTC time zone since 
            # datetime objects are 'naive' by default
            utc = utc.replace(tzinfo=from_zone)

            # Convert time zone
            local_time = utc.astimezone(to_zone)

            # Print file path on image
            text = f"{image_set.name}     {local_time}"
            cv2.putText(img, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
            cv2.putText(img, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.imwrite(str(set_out_dir / "img.bmp"), img)
            print(str(set_out_dir / "img.bmp"))


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument("--download", default=True, help="Download new images from storage")
    args.add_argument("--local_path", default=True, help="Download new images from storage")

    args = args.parse_args()

    processing_path = Path(config.POST_PROCESSING_PATH)
    if args.download:
        sync_files(
            settings.CONTAINER_NAME,
            date_prefix="",
            dst_dir=processing_path,
            overwrite=False,
        )

    # List files, group by series
    base_dir = processing_path / f"{settings.TIMELAPSE_NAME}/images"
    processed_dir = processing_path / f"{settings.TIMELAPSE_NAME}/processed"
    processed_dir.mkdir(exist_ok=True)

    # Create regex to extract shutter number
    # Example: '2022-03-26T07-14-29--shutter_050.jpg' --> '2022-03-26T07-14-29, '050'
    pat_re = re.compile(r"(?P<time>.+?)--shutter_(?P<shutter>\d+?).jpg")

    # Process the pipeline for each series
    client = dd.Client(processes=False)

    # The directory format is images / day / series / im*.jpg
    # Walk all the directories at depth 2 (day / series_name )
    image_sets = []
    data = collections.defaultdict(list)
    for series_dir in tqdm(list(base_dir.glob('*/*'))):
        series = series_dir.name
        day = series.split('T')[0]
        series_dir = base_dir / day / series
        out_dir = processed_dir / day / series
        out_dir.mkdir(parents=True, exist_ok=True)
        image_files = []
        for img in list(series_dir.iterdir()):
            if img.suffix != '.jpg':
                continue
            m = pat_re.match(img.name)
            assert m is not None
            shutter = int(m.group("shutter"))
            image_file = ImageFile(src_path=img, shutter=shutter)
            image_files.append(image_file)
        image_series = ImageSet(name=series, files=image_files)
        image_sets.append(image_series)

    image_sets.sort(key=lambda x: x.name)

    full_sets = [len(ser.files) == len(config.SHUTTER_SPEED_PERCENTS) for ser in image_sets]
    print(f"{sum(full_sets)}/{len(image_sets)} sets are full")

    futures = client.map(lambda ser: process_single_exposure_set(ser, processed_dir), image_sets)
    results = client.gather(futures)

    # Aggregate - Create the final video

    # Recursively list jpg files in the processed dir
    files_for_video = sorted(list(processed_dir.rglob('*.bmp')), key=lambda x: x.name)

    # Create video from list of files using ffmpeg
    create_video_from_images(files_for_video, processed_dir / "video.mp4")

    # post_production_dir = Path("../PostProduction")
    # post_production_dir.mkdir(parents=True, exist_ok=True)

    # # For each group, create an HDR image
    # for name, grp in df.groupby("series"):
    #     src_files = list(grp.path.values)
    #     hdr_methods = ["drago", "fattal"]
    #     for hdr_method in hdr_methods:
    #         out_file = Path(f"{post_production_dir}/{hdr_method}/{name}.jpg")
    #         out_file.parent.mkdir(exist_ok=True, parents=True)
    #         create_hdr(src_files, out_file, hdr_method)
