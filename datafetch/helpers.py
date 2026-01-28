import csv
from io import StringIO
import json
from os.path import join, exists
from os import makedirs
import re
import time

from django.conf import settings

import requests


def fetch_text(url, filename, method="get", path=None, refresh=False, encoding=None, **kwargs):
    """
    very basic caching sort of thing
    """
    datadir = join(settings.BASE_DIR, 'data')
    if path:
        datadir = join(datadir, path)
    filepath = join(datadir, filename)
    if not exists(filepath) or refresh:
        r = requests.request(method, url, **kwargs)
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


def fetch_json(url, filename, path=None, refresh=False, encoding=None, headers=None):
    text = fetch_text(
        url=url,
        filename=filename,
        path=path,
        refresh=refresh,
        encoding=encoding
    )
    return json.loads(text)


def fetch_file(url, filename, path=None, refresh=False, **kwargs):
    """
    similar to fetch_json, but for images
    """
    datadir = join(settings.BASE_DIR, 'data')
    if path:
        datadir = join(datadir, path)
    filepath = join(datadir, filename)
    if not exists(filepath) or refresh:
        r = requests.get(url)
        time.sleep(0.5)
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
    return filepath  # Return filepath for caller to use


def create_data_folder(path):
    """
    create a folder (relative to the data directory)
    """
    datadir = join(settings.BASE_DIR, 'data')
    path = join(datadir, path)
    if not exists(path):
        makedirs(path)


def count_breakdown(things, key):
    """
    Just a helper I use quite often for exploring the data.
    Pass it a list of dicts and a key for a breakdown by the numbers
    """
    counts = {}
    for thing in things:
        if thing.get(key) not in counts:
            counts[thing.get(key)] = 0
        counts[thing.get(key)] += 1
    return counts


def parse_name(name):
    """
    Some very dodgy code for extracting honorifics and gender from names
    """
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

def parse_company_name(name):
    return re.sub(u"^(.*?), The$", r"The \1", name.strip())


def parse_ch_officer_name(name):
    """
    Parse Companies House officer name format into structured components.

    CH uses "SURNAME, Forenames" format for individuals.
    Corporate directors use "COMPANY NAME" (no comma).

    Examples:
    - "SMITH, John Andrew" -> {name: "John Andrew Smith", family_name: "Smith", given_name: "John"}
    - "VAN DER BERG, Jan" -> {name: "Jan Van Der Berg", family_name: "Van Der Berg", given_name: "Jan"}
    - "O'BRIEN, Patrick" -> {name: "Patrick O'Brien", family_name: "O'Brien", given_name: "Patrick"}
    - "ACME LIMITED" -> {name: "Acme Limited", family_name: "", given_name: "", is_corporate: True}

    Args:
        name: Name string from Companies House API

    Returns:
        Dict with keys: name, family_name, given_name, is_corporate
    """
    if not name:
        return {
            'name': '',
            'family_name': '',
            'given_name': '',
            'is_corporate': False,
        }

    name = name.strip()

    # Check if it's a corporate name (no comma, or comma inside parentheses)
    # Corporate names often have patterns like "LTD", "LIMITED", "PLC", etc.
    if ',' not in name:
        # No comma - likely corporate
        # Title case it for readability
        return {
            'name': name.title(),
            'family_name': '',
            'given_name': '',
            'is_corporate': True,
        }

    # Split on first comma only
    parts = name.split(',', 1)
    if len(parts) != 2:
        # Unexpected format, return as-is
        return {
            'name': name.title(),
            'family_name': '',
            'given_name': '',
            'is_corporate': True,
        }

    surname_part = parts[0].strip()
    forenames_part = parts[1].strip()

    # Convert UPPERCASE surname to title case, handling special cases
    # like "VAN DER BERG" -> "Van Der Berg", "O'BRIEN" -> "O'Brien"
    def title_case_surname(s):
        """Title case surname, handling prefixes and apostrophes."""
        # Split on spaces and apostrophes while preserving them
        words = re.split(r"(\s+|')", s)
        result = []
        for word in words:
            if word.isspace() or word == "'":
                result.append(word)
            elif word.upper() in ('VAN', 'VON', 'DE', 'DER', 'DEN', 'LA', 'LE', 'DI', 'DA'):
                # Keep common prefixes lowercase (optional - depends on preference)
                # For UK, title case is more common
                result.append(word.title())
            else:
                result.append(word.title())
        return ''.join(result)

    family_name = title_case_surname(surname_part)
    given_name = forenames_part.title()

    # Extract just the first given name for the given_name field
    given_name_parts = given_name.split()
    first_given_name = given_name_parts[0] if given_name_parts else ''

    # Build full name: "Forenames Surname"
    full_name = f"{given_name} {family_name}".strip()

    return {
        'name': full_name,
        'family_name': family_name,
        'given_name': first_given_name,
        'is_corporate': False,
    }

def snake_case(camel_case_text):
    return re.sub(r'([a-z])([A-Z])', r'\1_\2', camel_case_text).lower()

def fetch_ec_csv(url, filename, path=None, refresh=False):
    datadir = join(settings.BASE_DIR, 'data')
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
