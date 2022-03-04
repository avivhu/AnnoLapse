#!/usr/bin/python3
from storage import get_latest_files
import settings

def post_production():
    get_latest_files(settings.CONTAINER_NAME, day='2022-03-04')


if __name__ == '__main__':
    post_production()

