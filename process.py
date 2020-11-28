"""
Usage:

Run:

    $ python process.py

Comment out the download_county_results() line after downloading the
first time.
"""

# Copyright (c) 2020 Chris Jerdonek

import csv
import json
import logging
from pathlib import Path
import time

import requests


_log = logging.getLogger()


def get_input_path(name):
    return Path('input-data') / name


def parse_county(line):
    # An example line:
    # Appling|105371|271560|11/16/2020 3:48:35 PM EST|16
    parts = line.split('|')
    name, id1, id2 = parts[:3]

    # An example url:
    # https://results.enr.clarityelections.com//GA/Appling/105371/271560/json/sum.json
    url = f'https://results.enr.clarityelections.com//GA/{name}/{id1}/{id2}/json/sum.json'

    return name, url


def iter_counties():
    # The data in this file was obtained from this URL:
    # https://results.enr.clarityelections.com//GA/105369/271927/json/en/electionsettings.json
    # and then accessing the following item in the JSON data:
    # data['settings']['electiondetails']['participatingcounties']
    path = get_input_path('counties.json')

    with open(path) as f:
        data = json.load(f)
        counties_data = data['participatingcounties']

        for line in counties_data:
            name, url = parse_county(line)
            name = name.replace('_', ' ')

            yield (name, url)


def get_county_names():
    """
    Return a dict mapping normalized county name to name.
    """
    normalized_to_name = {}

    for name, _ in iter_counties():
        normalized = name.upper()
        normalized_to_name[normalized] = name

    return normalized_to_name


def get_index_to_county_name():
    """
    Return a dict mapping 0-based index to county name.
    """
    index_to_name = {}

    for i, (name, _) in enumerate(iter_counties()):
        index_to_name[i] = name

    return index_to_name


def download(url, filename):
    path = Path('downloads') / filename

    _log.info(f'downloading: {url}')
    r = requests.get(url)
    path.write_text(r.text)
    _log.info(f'wrote to: {path}')


def download_county_results():
    for i, (name, url) in enumerate(iter_counties()):
        name = name.replace(' ', '_')
        filename = f'{i:03}-{name}.json'

        download(url, filename)
        _log.info('sleeping for 10 seconds before next download...')
        time.sleep(10)


def read_rla_totals():
    normalized_to_name = get_county_names()

    totals = {name: 0 for name in normalized_to_name.values()}

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

            numbers = [int(part) for part in row[3:]]
            total = sum(numbers)
            totals[name] += total

    return totals


def read_official_totals():
    index_to_name = get_index_to_county_name()

    totals = {}

    json_dir = Path('downloads')
    for path in sorted(json_dir.iterdir()):
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


def write_row(f, name, official, rla, last):
    f.write(f'{name},{official},{rla},{last}\n')


def write_output(official_totals, rla_totals):
    rla_total = 0
    official_total = 0

    rows = []
    for name in sorted(official_totals):
        rla = rla_totals[name]
        official = official_totals[name]
        row = (name, official, rla, rla - official)
        rows.append(row)

        rla_total += rla
        official_total += official

    # Sort by the magnitude of the difference, in descending order,
    # then next alphabetically.
    rows = sorted(rows, key=lambda row: (-1 * abs(row[-1]), name))

    path = Path('output.csv')
    with open(path, mode='w') as f:
        write_row(f, 'County', 'Initial', 'RLA', 'Difference')
        for row in rows:
            write_row(f, *row)

        write_row(f, 'ALL', official_total, rla_total, rla_total - official_total)

    _log.info(f'wrote: {path}')


def main():
    logging.basicConfig(level='INFO')

    # Comment out this line after downloading the county results.
    download_county_results()

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
    rla_totals['Gwinnett'] -= 119461

    official_totals = read_official_totals()

    assert len(rla_totals) == 159
    assert set(rla_totals) == set(official_totals)

    write_output(official_totals, rla_totals=rla_totals)


if __name__ == '__main__':
    main()
