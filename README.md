# Ballots Cast Comparison

## Georgia - November 3, 2020 General Election

This repo contains code to download and compare the ballots cast totals
reported before the RLA in Georgia (i.e. the "Official" results posted
on [Georgia's election results website](https://results.enr.clarityelections.com/GA/105369/web.264614/#/summary)) with after.


## To Run

Use Python 3.6+. Then:

    $ pip install requests
    $ python process.py

Then comment out the `download_county_results()` line after downloading the
county results for the first time.

The above writes the file `output.csv` to the repo root.  For convenience,
we have also stored this file in the repo for you.

**Read the comments in the code for more details, explanation, and
some disclaimers!**
