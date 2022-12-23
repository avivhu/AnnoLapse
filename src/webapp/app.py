from datetime import datetime
from azure.storage.blob import BlobServiceClient
from markupsafe import escape
import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
)


def _get_container_client(container_name="thecontainer"):
    connect_str = _get_connection_string()
    service_client = BlobServiceClient.from_connection_string(connect_str)
    client = service_client.get_container_client(container_name)
    return client

def _get_recorded_days():
    client = _get_container_client()
    prefix = "annolapse1/images/"
    blobs = client.walk_blobs(name_starts_with=prefix)
    days = list([b.name.split('/')[-2] for b in blobs])
    days.sort()
    return days


def _get_recorded_series_in_day(day):
    client = _get_container_client()
    prefix = f"annolapse1/images/{day}/"
    blobs = client.walk_blobs(name_starts_with=prefix)
    series = list([b.name.split('/')[-2] for b in blobs])
    series.sort()
    return series


def _get_images_in_series(day, series):
    client = _get_container_client()
    prefix = f"annolapse1/images/{day}/{series}/"
    blobs = client.walk_blobs(name_starts_with=prefix)
    images = list([b.name for b in blobs])
    images.sort()
    return images


app = Flask(__name__)

@app.route("/namer/<name>")
def hello(name):
    return f"Hello, {escape(name)}!"

@app.route("/days")
def show_days():
    days = _get_recorded_days()
    days.sort(reverse=True)
    aaa = '<br>\n'.join(days)
    return f"Days:\n{aaa}"


@app.route("/day/<day>")
def show_day(day):
    series = _get_recorded_series_in_day(day)
    aaa = '<br>\n'.join(series)
    return f"Series in day:\n{aaa}"


@app.route("/apath/<path:subpath>")
def showpath(subpath):
    return f"Path, {escape(subpath)}!"

@app.route("/")
def index():
    print("Request for index page received")
    return render_template("index.html")


@app.route("/test")
def test():
    print("testing")
    days = _get_recorded_days()
    series = _get_recorded_series_in_day(days[-1])
    _get_images_in_series(days[-1], series[-1])
    return " ".join(days)
    # return render_template("hello.html", name=most_recent_blob.name)


if __name__ == "__main__":
   app.run()
