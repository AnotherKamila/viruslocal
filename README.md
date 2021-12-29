# VirusLocal

Guess what? **Work in Progress!!!** :D

Despite that:
[![Open in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/anotherkamila/viruslocal/HEAD?labpath=voila%2Frender%2Fcovid19-zrh.ipynb)


## TODO describe what this is

[![contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/anotherkamila/songbook-web/issues)
[![Say Thanks!](https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg)](https://saythanks.io/to/AnotherKamila)


## How to run

0. Install requirements:
   - Python requirements: managed with pipenv -- run `pipenv sync`
   - to regenerate geo data, install Mapshaper: `sudo npm install -g mapshaper`
1. download and pre-process data: `pipenv run doit`
2. Actually getting the case numbers is currently manual :'( To be fixed; in the meantime I'm just committing an .xlsx on occasion XD
3. run it:
   - in jupyterlab: `pipenv run jupyter lab`
   - as a standalone app: `voila covid19-zrh.ipynb`
