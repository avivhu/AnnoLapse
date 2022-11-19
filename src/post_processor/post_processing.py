#!/usr/bin/python3
import logging
from typing import List, Optional
from tqdm import tqdm
from common.storage import sync_files
from pathlib import Path
import pandas as pd
import cv2
import common.settings as settings
import re
import numpy as np
import tempfile
from dataclasses import dataclass
from common.utils import run_command
import datetime
from dateutil import tz
import dask.distributed as dd
import common.config as config
import argparse


@dataclass
class ImageFile:
    src_path: Path
    shutter: int


@dataclass
class ImageSet:
    """A set of same-time images with different exposures."""

    name: str
    files: List[ImageFile]


# Image set transformers functions take an image set and return a transformed image
class ImageSetTransformer:
    def __init__(self, name: str):
        self.name = name

    def transform(self, image_set: ImageSet) -> np.ndarray:
        raise Exception("Not implemented")


class HdrTransformer(ImageSetTransformer):
    def __init__(self, hdr_method: str):
        self.hdr_method = hdr_method
        super().__init__(f"hdr_{self.hdr_method}")

    def transform(self, image_set: ImageSet):
        paths = [x.src_path for x in image_set.files]
        with tempfile.NamedTemporaryFile(prefix="hdr", suffix=".bmp") as tmpf:
            create_hdr(paths, Path(tmpf.name), method=self.hdr_method)
            img = cv2.imread(tmpf.name)
            assert img is not None
            return img


class TakeCenterBracketImage(ImageSetTransformer):
    def __init__(self):
        super().__init__("center_bracket")

    def transform(self, image_set: ImageSet):
        ind = len(image_set.files) // 2
        img = cv2.imread(str(image_set.files[ind].src_path))
        assert img is not None
        return img


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
    writer = cv2.VideoWriter(
        str(out_file), cv2.VideoWriter_fourcc(*"mp4v"), 30, frame_size
    )
    for file in tqdm(files):
        frame = cv2.imread(str(file))
        writer.write(frame)
    writer.release()


def create_hdr(src_files: List[Path], out_file: Path, method: str = "drago"):
    src_files_str = " ".join([str(x) for x in src_files])
    cmd = f"luminance-hdr-cli --tmo {method} -o {out_file} {src_files_str}"
    run_command(cmd, print_output=False)
    assert out_file.is_file()


def compute_local_time(utc: datetime.datetime):
    # Get local time
    # See https://stackoverflow.com/questions/4770297/convert-utc-datetime-string-to-local-datetime
    from_zone = tz.gettz("UTC")
    to_zone = tz.gettz("Asia/Jerusalem")

    # Tell the datetime object that it's in UTC time zone since
    # datetime objects are 'naive' by default
    utc = utc.replace(tzinfo=from_zone)

    # Convert time zone
    local_time = utc.astimezone(to_zone)
    return local_time


def print_overlay_text(img, image_set):
    # Parse datetime from iso format
    utc = datetime.datetime.strptime(image_set.name, "%Y-%m-%dT%H-%M-%S")
    local_time = compute_local_time(utc)

    # Print file path on image
    text = f"{image_set.name}     {local_time}"
    cv2.putText(img, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
    cv2.putText(img, text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def get_processed_file_path(
    image_set: ImageSet, transformer: ImageSetTransformer, processed_dir: Path
):
    return processed_dir / image_set.name / transformer.name / "img.bmp"


def process_single_set(
    image_set: ImageSet,
    tranformer: ImageSetTransformer,
    processed_dir: Path,
    overwrite: bool = False,
):

    logging.info(f"Processing {image_set.name} with transformer {transformer.name}")

    out_file_path = get_processed_file_path(image_set, transformer, processed_dir)
    if not overwrite and out_file_path.exists():
        print(f"{image_set.name} already processed. skipping it")
        return

    img = tranformer.transform(image_set)
    print_overlay_text(img, image_set)

    out_file_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_file_path), img)
    logging.info(f"Created: {str(out_file_path)}")
    return None


def read_image_sets_catalog(src_dir: Path, max_sets: Optional[int] = None):

    # Create regex to extract shutter number
    # Example: '2022-03-26T07-14-29--shutter_050.jpg' --> '2022-03-26T07-14-29, '050'
    pat_re = re.compile(r"(?P<time>.+?)--shutter_(?P<shutter>\d+?).jpg")

    # The directory format is images / day / image_set_name / im*.jpg
    # Walk all the directories at depth 2 (day / image_set_name )
    the_dirs = list(src_dir.glob("*/*"))

    def _read(img_set_dir: Path):
        series = img_set_dir.name
        day = series.split("T")[0]
        img_set_dir = src_dir / day / series
        image_files = []
        for img in list(img_set_dir.iterdir()):
            if img.suffix != ".jpg":
                continue
            m = pat_re.match(img.name)
            assert m is not None
            shutter = int(m.group("shutter"))
            image_file = ImageFile(src_path=img, shutter=shutter)
            image_files.append(image_file)
        image_series = ImageSet(name=series, files=image_files)
        return image_series

    client = dd.Client(processes=False)
    image_sets = list(client.gather(client.map(_read, the_dirs)))
    image_sets.sort(key=lambda x: x.name)
    return image_sets


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument(
        "--download", default=True, help="Download new images from storage"
    )
    args = args.parse_args()

    # Log to console
    logging.basicConfig(level=logging.DEBUG)

    post_processing_path = Path(config.POST_PROCESSING_PATH)
    if args.download:
        sync_files(
            settings.CONTAINER_NAME,
            date_prefix="",
            dst_dir=post_processing_path,
            overwrite=False,
        )

    # Process the pipeline for each image set
    src_dir = post_processing_path / f"{settings.TIMELAPSE_NAME}/images"
    processed_dir = post_processing_path / f"{settings.TIMELAPSE_NAME}/processed"

    image_sets0 = read_image_sets_catalog(src_dir, max_sets=None)

    # Remove non-full image sets
    image_sets1 = [
        aset
        for aset in image_sets0
        if len(aset.files) == len(config.SHUTTER_SPEED_PERCENTS)
    ]

    # For each day, first image set after midday
    times = []
    for image_set in image_sets1:
        utc = datetime.datetime.strptime(image_set.name, "%Y-%m-%dT%H-%M-%S")
        local_time = compute_local_time(utc)
        times.append(pd.to_datetime(local_time))

    df = pd.DataFrame({"time": times, "image_set": image_sets1})
    df.loc[:, "t_since_midday"] = [
        (
            t.replace(tzinfo=None) - datetime.datetime(t.year, t.month, t.day, 12, 0)
        ).total_seconds()
        / 60
        / 60
        for t in times
    ]
    df.loc[:, "date"] = [t.date() for t in times]

    image_sets = []
    for d, grp in df.groupby("date"):
        a = grp[grp.t_since_midday >= 0]
        if len(a) == 0:
            continue
        a = a.sort_values("t_since_midday")
        image_sets.append(a.iloc[0].image_set)
    image_sets.sort(key=lambda x: x.name)

    transformers = [
        HdrTransformer("drago"),
        HdrTransformer("fattal"),
        TakeCenterBracketImage(),
    ]

    # List files, group by series
    processed_dir.mkdir(exist_ok=True)

    client = dd.Client()  # (processes=False)
    for transformer in transformers:
        if False:
            futures = client.map(
                lambda image_set: process_single_set(
                    image_set, transformer, processed_dir, overwrite=True
                ),
                image_sets,
            )
            results = client.gather(futures)
        else:
            for image_set in image_sets:
                process_single_set(
                    image_set, transformer, processed_dir, overwrite=False
                )
        for image_set in image_sets:
            afile = get_processed_file_path(image_set, transformer, processed_dir)
            assert afile.exists()

    # Create a video per each transformer
    for transformer in transformers:
        files_for_video = []
        for image_set in image_sets:
            afile = get_processed_file_path(image_set, transformer, processed_dir)
            assert afile.exists()
            files_for_video.append(afile)

        # Create video from list of files using ffmpeg
        video_path = processed_dir / f"{transformer.name}.mp4"
        create_video_from_images(files_for_video, video_path)

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
