#!/usr/bin/python3
import os
from pathlib import Path
import shutil
from azure.storage.blob import BlobServiceClient
import config
import time
import logging

from utils import run_command

# From: https://stackoverflow.com/questions/63413832/upload-local-folder-to-azure-blob-storage-using-blobserviceclient-with-python-v1
def _upload_file(client, source, dest):
    with open(source, "rb") as data:
        client.upload_blob(name=dest, data=data, overwrite=True)
    logging.info(f"Uploaded: source={source} dest={dest}")


def _upload_dir(client, source, dest, delete):
    prefix = "" if dest == "" else dest + "/"
    for root, dirs, files in list(os.walk(source)):
        for name in files:
            dir_part = os.path.relpath(root, source)
            dir_part = "" if dir_part == "." else dir_part + "/"
            file_path = os.path.join(root, name)
            blob_path = prefix + dir_part + name
            _upload_file(client, file_path, blob_path)
            if delete:
                _remove(file_path)
    # if delete:
    #    _remove(source)


# https://stackoverflow.com/a/41789397
def _remove(path):
    path = Path(path)
    if path.is_file():
        path.unlink()  # remove file
    else:
        shutil.rmtree(path)  # remove dir
    logging.debug(f"Removed file={str(path)}")


def _get_connection_string():
    connect_str = os.getenv("TIMELAPSE_AZURE_STORAGE_CONNECTION_STRING")
    if not connect_str:
        raise Exception(
            "Environment variable TIMELAPSE_AZURE_STORAGE_CONNECTION_STRING is not set. Get it from Azure Portal"
        )
    return connect_str


def _get_sas_key():
    key = os.getenv("TIMELAPSE_AZURE_STORAGE_SAS_KEY")
    if not key:
        raise Exception(
            "Environment variable TIMELAPSE_AZURE_STORAGE_SAS_KEY is not set. Get it from Azure Portal"
        )
    return key


def upload_to_remote_storage(container_name, source, dest, delete):
    connect_str = _get_connection_string()
    service_client = BlobServiceClient.from_connection_string(connect_str)
    client = service_client.get_container_client(container_name)
    _upload_dir(client, source=source, dest=dest, delete=delete)


def get_latest_files(container_name, day):
    connect_str = _get_connection_string()
    service_client = BlobServiceClient.from_connection_string(connect_str)
    client = service_client.get_container_client(container_name)
    if day is not None:
        start_with = f"{config.TIMELAPSE_NAME}/images/{day}"
    last_dl = None
    while True:
        blobs = client.list_blobs(name_starts_with=start_with)
        blobs = list(blobs)
        blobs.sort(key=lambda b: b.name)

        print(blobs[-1].name)
        if last_dl != blobs[-1].name:
            download_file_path = "/tmp/dl.jpg"
            with open(download_file_path, "wb") as download_file:
                dl = client.download_blob(blobs[-1]).readall()
                download_file.write(dl)
                last_dl = blobs[-1].name
        time.sleep(1)


def sync_files(
    container_name: str, date_prefix: str, dst_dir: Path, overwrite: bool
):
    # Download files from source to destination. Delete files in the distination that that are not present in the source.
    sas_key = _get_sas_key()
    in_dir = f"{config.TIMELAPSE_NAME}/images"
    dst_dir2 = dst_dir / in_dir
    Path(dst_dir2).mkdir(parents=True, exist_ok=True)
    url = f"https://annolapse.blob.core.windows.net/{container_name}/{in_dir}/"
    overwrite_str = "true" if overwrite else "false"
    cmd = rf'azcopy sync "{url}?{sas_key}" "{str(dst_dir2)}"  --include-pattern "{date_prefix}*"  --delete-destination true'
    run_command(cmd)
