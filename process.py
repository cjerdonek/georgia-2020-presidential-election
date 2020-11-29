"""
Usage:

Run:

    $ python process.py

"""

# Copyright (c) 2020 Chris Jerdonek

import csv
import json
import logging
from pathlib import Path
import time
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import requests


CACHE_DIR = Path('cache')
DOWNLOADS_DIR = Path('downloads')

VOTE_TOTAL_KEYS = [
    # The total of Trump, Biden, and Jorgenson vote totals.
    'TBJ',
    # "Ballots cast," or all types of votes.
    'BC',
    'Und',
    'Ovr',
]

RLA_KEYS = VOTE_TOTAL_KEYS + ['InvW', 'ValW']

BC_DELTA_INDEX = -3


_log = logging.getLogger()


def get_input_path(name):
    return Path('input-data') / name


def read_json(path):
    with open(path) as f:
        data = json.load(f)

    return data


def write_json(path, data):
    _log.info(f'writing json: {path}')
    with open(path, mode='w') as f:
        json.dump(data, f, sort_keys=True, indent='    ')


def make_zero_vote_totals(keys):
    return {key: 0 for key in keys}


def unzip_file(zip_path, file_name):
    suffix = Path(file_name).suffix

    dir_path = zip_path.parent
    new_path = zip_path.with_suffix(suffix)

    with ZipFile(zip_path) as zipfile:
        created_path = Path(zipfile.extract(file_name, path=dir_path))
        _log.info(f'renaming to: {new_path}')
        created_path.rename(new_path)

    _log.info(f'removing: {zip_path}')
    zip_path.unlink()


def parse_county(line):
    # An example line:
    # Appling|105371|271560|11/16/2020 3:48:35 PM EST|16
    parts = line.split('|')
    name, id1, id2 = parts[:3]
    name = name.replace('_', ' ')

    return name, id1, id2


def iter_counties():
    # The data in this file was obtained from this URL:
    # https://results.enr.clarityelections.com//GA/105369/271927/json/en/electionsettings.json
    # and then accessing the following item in the JSON data:
    # data['settings']['electiondetails']['participatingcounties']
    path = get_input_path('counties.json')

    data = read_json(path)

    counties_data = data['participatingcounties']

    for i, line in enumerate(counties_data):
        name, id1, id2 = parse_county(line)

        yield (i, name, id1, id2)


def get_county_names():
    """
    Return a dict mapping normalized county name to name.
    """
    normalized_to_name = {}

    for i, name, *_ in iter_counties():
        normalized = name.upper()
        normalized_to_name[normalized] = name

    return normalized_to_name


def get_index_to_county_name():
    """
    Return a dict mapping 0-based index to county name.
    """
    index_to_name = {}

    for i, name, *_ in iter_counties():
        index_to_name[i] = name

    return index_to_name


def download(url, path, target_path=None):
    if target_path is None:
        target_path = path

    if target_path.exists():
        _log.info(f'already downloaded: {target_path}')
        return False

    _log.info(f'downloading: {url}')
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(f'got status code: {r.status_code}')

    with open(path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=128):
            f.write(chunk)

    _log.info(f'wrote to: {path}')

    return True


def download_county_results(url_format, subdir, zip_name=None):
    output_dir = DOWNLOADS_DIR / subdir

    if not output_dir.exists():
        output_dir.mkdir()

    for i, name, id1, id2 in iter_counties():
        name = name.replace(' ', '_')
        url = url_format.format(name=name, id1=id1, id2=id2)
        ext = url.split('.')[-1]

        filename = f'{i:03}-{name}.{ext}'

        path = output_dir / filename

        if zip_name is not None:
            suffix = Path(zip_name).suffix
            target_path = path.with_suffix('.xml')

        downloaded = download(url, path=path, target_path=target_path)

        if not downloaded:
            continue

        if zip_name is not None:
            unzip_file(path, file_name=zip_name)

        _log.info('sleeping for 5 seconds before next download...')
        time.sleep(5)


def check_cache_path(base_name):
    cache_path = CACHE_DIR / f'{base_name}.json'
    if cache_path.exists():
        _log.info(f'using cached data: {cache_path}')
        data = read_json(cache_path)
    else:
        data = None

    return (cache_path, data)


def read_rla_totals():
    base_name = 'rla-totals'
    cache_path, totals = check_cache_path(base_name)
    if totals is not None:
        return totals

    normalized_to_name = get_county_names()

    totals = {}

    for name in normalized_to_name.values():
        totals[name] = make_zero_vote_totals(RLA_KEYS)

    # This CSV was downloaded from here:
    # https://sos.ga.gov/index.php/elections/historic_first_statewide_audit_of_paper_ballots_upholds_result_of_presidential_race
    # and the batch results lines were put into a separate file.
    path = get_input_path('audit-report-batch-results-lines.csv')
    with open(path) as f:
        reader = csv.reader(f)
        # Skip the header row.
        next(reader)
        for i, row in enumerate(reader, start=1):
            if len(row) != 10:
                raise RuntimeError(f'error at line: {i}')

            name = row[0]
            name = normalized_to_name[name]
            county_totals = totals[name]

            batch_type = row[2]

            row_totals = [int(part) for part in row[3:]]

            county_totals['TBJ'] += sum(row_totals[:3])
            county_totals['BC'] += sum(row_totals)
            county_totals['InvW'] += row_totals[3]
            county_totals['ValW'] += row_totals[4]
            county_totals['Und'] += row_totals[5]
            county_totals['Ovr'] += row_totals[6]

    write_json(cache_path, data=totals)

    return totals


def iter_download_dir(subdir_name):
    """
    Yield pairs: (path, county_name).
    """
    index_to_name = get_index_to_county_name()

    dir_path = DOWNLOADS_DIR / subdir_name

    for path in sorted(dir_path.iterdir()):
        # Skip files like ".DS_Store".
        if not path.suffix:
            continue

        filename = path.name
        index = int(filename.split('-')[0])
        name = index_to_name[index]

        yield path, name


# This function is no longer needed.
def read_official_json_totals():
    index_to_name = get_index_to_county_name()

    totals = {}

    for path in sorted(DOWNLOADS_DIR.iterdir()):
        # Skip .gitkeep.
        if not path.suffix:
            continue

        assert path.suffix == '.json'
        filename = path.name

        index = int(filename.split('-')[0])
        name = index_to_name[index]

        with open(path) as f:
            data = json.load(f)

        contests_data = data['Contests']
        data = contests_data[0]
        # Double-check that we are looking at the right contest.
        if not data['C'].startswith('President of the United States'):
            raise RuntimeError(index, data)

        ballots_cast = data['BC']

        totals[name] = ballots_cast

    return totals


def get_ballots_cast(root):
    vt_element = root.find('VoterTurnout')
    total = vt_element.attrib['ballotsCast']

    return int(total)


def get_votes_by_vote_type(element):
    totals = {}

    mapping = {
        'Overvotes': 'Ovr',
        'Undervotes': 'Und',
    }
    for vote_type in element.findall('VoteType'):
        attrib = vote_type.attrib
        name = attrib['name']
        name = mapping[name]

        total = attrib['votes']
        totals[name] = int(total)

    return totals


def get_candidate_total(contest):
    total = 0
    for choice_element in contest.findall('Choice'):
        attrib = choice_element.attrib
        name = attrib['text']
        assert 'Trump' in name or 'Biden' in name or 'Jorgensen' in name

        choice_total = attrib['totalVotes']
        total += int(choice_total)

    return total


def read_detailxml_file(path):
    tree = ET.parse(path)
    root = tree.getroot()

    totals = {}
    totals['BC'] = get_ballots_cast(root)

    contest = root.find('Contest')
    contest_name = contest.attrib['text']

    # Make sure we have the right contest.
    if not contest_name.startswith('President of the United States'):
        raise RuntimeError(f'got contest name: {contest_name!r}')

    new_totals = get_votes_by_vote_type(contest)
    totals.update(new_totals)

    totals['TBJ'] = get_candidate_total(contest)

    return totals


def read_official_totals():
    base_name = 'detailxml'
    cache_path, totals = check_cache_path(base_name)
    if totals is not None:
        return totals

    totals = {}
    for path, name in iter_download_dir('detailxml'):
        try:
            county_totals = read_detailxml_file(path)
        except Exception:
            raise RuntimeError(f'error reading: {path}')

        totals[name] = county_totals

    write_json(cache_path, data=totals)

    return totals


def compute_all_counties(totals):
    name = next(iter(totals))
    keys = totals[name]
    all_totals = make_zero_vote_totals(keys)

    for county_totals in totals.values():
        for key, total in county_totals.items():
            all_totals[key] += total

    return all_totals


def add_all_totals(totals):
    all_totals = compute_all_counties(totals)
    totals['ALL'] = all_totals


def write_row(f, values):
    text = ','.join(str(value) for value in values)
    f.write(f'{text}\n')


def write_output(official_totals, rla_totals):
    add_all_totals(official_totals)
    add_all_totals(rla_totals)

    rows = []
    key_count = len(VOTE_TOTAL_KEYS)
    for name in sorted(official_totals):
        rla_county_totals = rla_totals[name]
        official_county_totals = official_totals[name]

        pairs = [
            (official_county_totals, VOTE_TOTAL_KEYS),
            (rla_county_totals, RLA_KEYS),
        ]

        row = [name]
        for totals, keys in pairs:
            for key in keys:
                row.append(totals[key])

        for i in range(1, key_count + 1):
            delta = row[i + key_count] - row[i]
            row.append(delta)

        rows.append(row)

    def sort_key(row):
        # Make the ALL row first, then sort by the magnitude of the
        # ballots cast delta, then alphabetically by name.
        return (row[0] != 'ALL', -1 * abs(row[BC_DELTA_INDEX]), name)

    rows = sorted(rows, key=sort_key)

    headers = ['County']
    pairs = [
        ('Ofc', VOTE_TOTAL_KEYS),
        ('RLA', RLA_KEYS),
        ('\u0394', VOTE_TOTAL_KEYS),
    ]
    for prefix, keys in pairs:
        for key in keys:
            header = f'{prefix}-{key}'
            headers.append(header)

    path = Path('output.csv')
    with open(path, mode='w') as f:
        write_row(f, headers)
        for row in rows:
            write_row(f, row)

    _log.info(f'wrote: {path}')


def main():
    logging.basicConfig(level='INFO')

    # Some example urls:
    # https://results.enr.clarityelections.com//GA/Appling/105371/271560/json/sum.json
    # https://results.enr.clarityelections.com//GA/Fulton/105430/271723/reports/detailxml.zip
    # url_format = 'https://results.enr.clarityelections.com//GA/{name}/{id1}/{id2}/json/sum.json'
    # subdir = 'sumjson'
    url_format = 'https://results.enr.clarityelections.com//GA/{name}/{id1}/{id2}/reports/detailxml.zip'
    subdir = 'detailxml'

    download_county_results(url_format, subdir=subdir, zip_name='detail.xml')

    official_totals = read_official_totals()

    rla_totals = read_rla_totals()

    # **Note!** Here we subtract the number of Absentee by Mail cards
    # for "Card #2" in the official results reported by Gwinnett County:
    # https://www.gwinnettcounty.com/web/gwinnett/Departments/Elections/ElectionResults
    # This number can be found e.g. in the "Absentee by" column of
    # the Gwinnett Transit Referendum results, found on the last page
    # of their results PDF.  We included this PDF in the "pdfs" directory
    # of this repo for convenience.
    #   Doing this subtraction eliminates a major, known discrepancy in
    # the official vs. RLA totals.  Namely, the undervote total in the
    # RLA results for Gwinnett County included the "second sheet" of a
    # multi-card ballot, even though those ballots didn't have the
    # Presidential contest. This subtraction is only an approximate
    # correction though, as we don't know the true number of second sheet
    # ballot cards found during the RLA.  (We are using the number from
    # the official / pre-RLA totals as a proxy.)
    gwinnett_totals = rla_totals['Gwinnett']
    for key in ('BC', 'Und'):
        gwinnett_totals[key] -= 119461

    assert len(rla_totals) == 159
    assert set(rla_totals) == set(official_totals)

    write_output(official_totals, rla_totals=rla_totals)


if __name__ == '__main__':
    main()
