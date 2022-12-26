import sys
from pathlib import Path
from typing import List
from datetime import datetime
from dataclasses import dataclass
import pytz
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
)
from markupsafe import escape

from common.utils import compute_local_time

# Work around PYTHONPATH issues in a simple way that works in the webapp
p = (Path(__file__).parent.parent / "common").absolute()
assert p.exists()
sys.path.append(str(p))

from storage import get_container_client, get_container_url, get_images_dir
import config


@dataclass
class Image:
    filename: str
    url: str


@dataclass
class Day:
    id: str
    display_name: str


@dataclass
class ImageSet:
    id: str
    day: str
    local_time: str
    images: List[Image]


def _get_recorded_days():
    client = get_container_client()
    blobs = client.walk_blobs(name_starts_with=get_images_dir() + "/")
    days = list([b.name.split("/")[-2] for b in blobs])
    days.sort(reverse=True)
    result = []
    for day in days:
        result.append(
            Day(day, datetime.strptime(day, "%Y-%m-%d").strftime("%A, %B %d, %Y"))
        )
    return result


def _get_recorded_image_sets_in_day(day_id: str):
    client = get_container_client()
    prefix = f"{get_images_dir()}/{day_id}/"
    blobs = client.walk_blobs(name_starts_with=prefix)
    series = list([b.name.split("/")[-2] for b in blobs])
    series.sort()
    return series


def _get_image_set(image_set_id):
    client = get_container_client()
    # The day is the first part of the image set id
    day = image_set_id.split("T")[0]
    prefix = f"{get_images_dir()}/{day}/{image_set_id}/"
    blobs = client.walk_blobs(name_starts_with=prefix)
    images = []
    for b in blobs:
        url = get_container_url() + b.name
        images.append(_get_image(b.name))
    return _create_image_set(image_set_id, day, images)


def _get_image(image_blob_name):
    url = get_container_url() + image_blob_name
    return Image(image_blob_name, url)


def _create_day(day_id: str):
    return Day(day_id, datetime.strptime(day_id, "%Y-%m-%d").strftime("%A, %B %d, %Y"))


def _create_image_set(id, day, images=None):
    return ImageSet(id, day, _image_set_id_to_local_time(id), images)


def _image_set_id_to_local_time(image_set_id: str):
    # Parse string such as 2022-12-23T10-21-18
    # into a datetime object
    utc_time = datetime.strptime(image_set_id, "%Y-%m-%dT%H-%M-%S")
    local_time = compute_local_time(utc_time, config.TIMEZONE)

    # Print in military time
    return local_time.strftime("%A, %B %d, %Y at %H:%M:%S")


app = Flask(__name__)


@app.route("/namer/<name>")
def hello(name):
    return f"Hello, {escape(name)}!"


@app.route("/")
def show_days():
    days = _get_recorded_days()
    print("Request for days page received")
    return render_template("days.html", days=days)


@app.route("/day/<day_id>")
def show_day(day_id: str):
    day = _create_day(day_id)
    image_set_ids = _get_recorded_image_sets_in_day(day.id)
    image_set_ids = sorted(image_set_ids, reverse=True)
    image_sets = [_create_image_set(id, day) for id in image_set_ids]
    return render_template("day.html", day=day, image_sets=image_sets)


@app.route("/image_set/<image_set_id>")
def show_image_set(image_set_id: str):
    print("Request for image set page received")
    image_set = _get_image_set(image_set_id)
    return render_template("image_set.html", image_set=image_set)


if __name__ == "__main__":
    app.run()
