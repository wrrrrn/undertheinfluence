import csv
from io import StringIO
import json
from os.path import join, exists
from os import makedirs
import re
import time

from django.conf import settings

import requests


"""
very basic caching sort of thing
"""
def fetch_text(url, filename, path=None, refresh=False, headers=None, encoding=None):
    kwargs = {}
    if headers:
        kwargs["headers"] = headers
    datadir = join(settings.BASE_DIR, 'datafetch', 'data')
    if path:
        datadir = join(datadir, path)
    filepath = join(datadir, filename)
    if not exists(filepath) or refresh:
        r = requests.get(url, **kwargs)
        time.sleep(0.5)
        if encoding:
            r.encoding = encoding
        with open(filepath, "w") as f:
            f.write(r.text)
        t = r.text
    else:
        with open(filepath) as f:
            t = f.read()
    return t

def fetch_json(url, filename, path=None, refresh=False, headers=None, encoding=None):
    text = fetch_text(url, filename, path, refresh, headers, encoding)
    return json.loads(text)

"""
similar to fetch_json, but for images
"""
def fetch_file(url, filename, path=None, refresh=False):
    datadir = join(settings.BASE_DIR, 'datafetch', 'data')
    if path:
        datadir = join(datadir, path)
    filepath = join(datadir, filename)
    if not exists(filepath) or refresh:
        r = requests.get(url)
        time.sleep(0.5)
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)

"""
create a folder (relative to the data directory)
"""
def create_data_folder(path):
    datadir = join(settings.BASE_DIR, 'datafetch', 'data')
    path = join(datadir, path)
    if not exists(path):
        makedirs(path)

"""
Just a helper I use quite often for exploring the data.
Pass it a list of dicts and a key for a breakdown by
the numbers
"""
def count_breakdown(things, key):
    counts = {}
    for thing in things:
        if thing.get(key) not in counts:
            counts[thing.get(key)] = 0
        counts[thing.get(key)] += 1
    return counts

"""
Some very dodgy code for extracting
honorifics and gender from names
"""
def parse_name(name):
    data = {'name': name}
    stripped_name = name.replace('.', '').strip()
    # TODO: honorary suffixes
    stripped_name = re.sub(r'(\s+[A-Z]{2,})+$', '', stripped_name)
    prefixes = {
        'female': ('Queen', r'Lady(?: na)?', 'Duchess of', 'Baroness', r'Countess(?: of)?', 'Viscountess', 'Dame', 'Mrs', 'Ms', 'Miss',),

        'male': ('Colonel', 'Major', 'Baron', r'Marquess(?: of)?', 'Duke', 'Viscount', 'Count', r'Lord(?: na)?', r'Earl(?: of)?', 'Sir', 'Mr', r'Lieut(?:enant|-General|-Commander|-Colonel)', 'Admiral', r'Air (?:Commodore|Vice-Marshall)', r'Brigadier(?:-General)?', 'Captain', 'Colonel', 'Commander', 'Commodore', 'Field Marshal', 'Flight Lieut', 'General', 'Group Captain', 'Vice-Admiral', r'Major(?:-General)?', 'Master of', 'Rear-Admiral', 'Squadron Leader', 'Sub-Lieutenant', 'Wing Commander',),

        'unknown': (r'(?:The )?(?:Rt )?Hon(?:ourable)?', 'Bishop', r'(?:Very )?Reverend', 'Archbishop', 'Cllr', 'Dr', r'Prof(?:essor)?',),
    }
    all_prefixes = "|".join([b for a in prefixes.values() for b in a])
    r = re.match(r"((?:{}) )+(.*)$".format(all_prefixes), stripped_name)
    if r:
        # derive gender from honorific prefix
        if re.match(r"(({}) )+".format("|".join(prefixes['female'])), stripped_name):
            data['gender'] = "female"
        elif re.match(r"(({}) )+".format("|".join(prefixes['male'])), stripped_name):
            data['gender'] = "male"
        data['honorific_prefix'] = r.group(1).strip()
        stripped_name = r.group(2)
    return stripped_name, data

def snake_case(camel_case_text):
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', camel_case_text).lower()

def fetch_ec_csv(url, filename, path=None, refresh=False):
    datadir = join(settings.BASE_DIR, 'datafetch', 'data')
    if path:
        datadir = join(datadir, path)
    filepath = join(datadir, filename)
    if exists(filepath) and not refresh:
        with open(filepath) as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [snake_case(fieldname) for fieldname in reader.fieldnames]
            return list(reader)
    else:
        r = requests.get(url)
        r.encoding = "utf8"
        raw_text = r.text[1:]
        with open(filepath, "w") as f:
            f.write(raw_text)
        reader = csv.DictReader(StringIO(raw_text))
        reader.fieldnames = [snake_case(fieldname) for fieldname in reader.fieldnames]
        return list(reader)
