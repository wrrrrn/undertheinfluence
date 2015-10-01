import json
from os.path import join, exists
from os import makedirs
import time

from django.conf import settings

import requests


# very basic caching sort of thing
def fetch_json(url, filename, path=None, refresh=False):
    fullpath = join(settings.BASE_DIR, 'datafetch', 'data')
    if path:
        fullpath = join(fullpath, path)
    filepath = join(fullpath, filename)
    if not exists(filepath) or refresh:
        r = requests.get(url)
        time.sleep(0.5)
        with open(filepath, "w") as f:
            f.write(r.text)
        j = r.json()
    else:
        with open(filepath) as f:
            j = json.load(f)
    return j

def fetch_file(url, filename, path=None, refresh=False):
    fullpath = join(settings.BASE_DIR, 'datafetch', 'data')
    if path:
        fullpath = join(fullpath, path)
    filepath = join(fullpath, filename)
    if not exists(filepath) or refresh:
        r = requests.get(url)
        time.sleep(0.5)
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

def create_folder(path):
    if not exists(path):
        makedirs(path)
