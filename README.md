# Georgia - November 3, 2020 General Election

## Ballots Cast Comparison Tool

This repo contains a Python script to download and compare certain
vote totals reported before and after [Georgia's risk-limiting audit
(RLA)](https://sos.ga.gov/index.php/elections/historic_first_statewide_audit_of_paper_ballots_upholds_result_of_presidential_race) of the
Presidential contest.

The totals reported before the RLA are taken from the "Official" totals
reported on [Georgia's state election results
page](https://results.enr.clarityelections.com/GA/105369/web.264614/#/summary). The RLA totals are taken from the CSV RLA report, which is available
at the above link. The CSV is also included in the
[`input-data`](input-data) directory of this repo.

The output of the script can be seen in the [`output.csv`](output.csv) file
included in this repo.

The reason this script is needed is that Georgia's election results page
doesn't seem to include "ballots cast" in the downloadable CSV files, etc.
It only includes the candidate totals.  The ballots cast total is, however,
available in Scytl's XML downloads. You can also see the ballots cast
numbers in the user interface of the website. For example, for Appling
County, you can see it here (look at "Ballots Cast" in the "VOTER TURNOUT"
box on the right):
https://results.enr.clarityelections.com/GA/Appling/105371/web.264614/#/summary?v=271560%2F

(Note that categories corresponding to certain other columns in the RLA
report, like Invalid Write-In and Valid Write-in, don't seem to be
available anywhere in the official totals, even in the XML downloads.)

**Read the comments in the code for more details, explanation, and
some disclaimers!**

## To Run

Use Python 3.6+. Then:

    $ pip install requests
    $ python process.py

The above writes the file `output.csv` to the repo root.  For convenience,
we have also stored this file in the repo for you, as well as some
intermediate results files in the [`cache`](cache) directory.
