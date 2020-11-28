# Georgia - November 3, 2020 General Election

## Ballots Cast Comparison Tool

This repo contains a Python script to download and compare the totals for "ballots cast" that were reported before the risk-limiting audit (RLA)
with the corresponding totals reported in the RLA report.  The totals
reported before the RLA are taken from the "Official" totals reported on
[Georgia's state election results page](https://results.enr.clarityelections.com/GA/105369/web.264614/#/summary).

The output of the script can be seen in the [`output.csv`](output.csv) file
included in this repo.

The reason this script is needed is that Georgia's election results page
doesn't seem to include "ballots cast" in the downloadable CSV files, etc.
It only includes the candidate totals.  The ballots cast are, however,
available in Scytl's JSON endpoints. (Note that categories corresponding
to the other RLA columns, like Invalid Write-In, Valid Write-in,
Blank/Undervote, and Overvote, don't seem to be available in the JSON
endpoints.)

**Read the comments in the code for more details, explanation, and
some disclaimers!**

## To Run

Use Python 3.6+. Then:

    $ pip install requests
    $ python process.py

Then comment out the `download_county_results()` line after downloading the
county results for the first time.

The above writes the file `output.csv` to the repo root.  For convenience,
we have also stored this file in the repo for you.
