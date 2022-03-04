#!/usr/bin/python3
import os
from pathlib import Path
import shutil
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import settings
import time

# From: https://stackoverflow.com/questions/63413832/upload-local-folder-to-azure-blob-storage-using-blobserviceclient-with-python-v1
def _upload_file(client, source, dest):
    print(f'Uploading {source} to {dest}')
    with open(source, 'rb') as data:
        client.upload_blob(name=dest, data=data, overwrite=True)


def _upload_dir(client, source, dest, delete):
    prefix = '' if dest == '' else dest + '/'
    for root, dirs, files in list(os.walk(source)):
        for name in files:
            dir_part = os.path.relpath(root, source)
            dir_part = '' if dir_part == '.' else dir_part + '/'
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
    print('Removing', str(path))
    if path.is_file():
        path.unlink()  # remove file
    else:
        shutil.rmtree(path)  # remove dir

def _get_connection_string():
    connect_str = os.getenv('TIMELAPSE_AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        raise Exception('Environment variable TIMELAPSE_AZURE_STORAGE_CONNECTION_STRING is not set. Get it from Azure Portal')
    return connect_str


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
        start_with = f'{settings.TIMELAPSE_NAME}/images/{day}'
    while True:
        blobs = client.list_blobs(name_starts_with=start_with)
        blobs = list(blobs)
        blobs.sort(key=lambda b: b.name)

        print(blobs[-1].name)

        download_file_path = '/tmp/dl.jpg'
        with open(download_file_path, "wb") as download_file:
            dl = client.download_blob(blobs[-1]).readall()
            download_file.write(dl)
        time.sleep(1)


    
    
