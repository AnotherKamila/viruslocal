import json
import requests
import sys
import yaml

from pathlib import Path
from doit.tools import config_changed

CANTONS = ['ZH']
DATA = Path('./data')
DATA.mkdir(exist_ok=True)

with open('./data_sources.yml') as f:
    DATA_SOURCES = yaml.safe_load(f)


# utils -- TODO move to its own file

def debug(*args, **kwargs):
    print(
        "{} {}".format(
            " ".join("{}".format(a) for a in args),
            " ".join("{}={}".format(k, v) for k, v in kwargs.items()),
        ),
        file=sys.stderr,
    )

def filter_canton(geojson, canton):
    def keep(feature):
        return (feature['geometry'] != None and
                feature['properties']['kanton'] == canton)

    return {
        'type': geojson['type'],
        'features': [ f for f in geojson['features'] if keep(f) ],
    }


def offset_coordinates(geojson, offset=(-0.00117, -0.00133)):
    """
    Offsets the coordinates in the GeoJSON file by an offset eyeballed to
    approximately fix up the Special Swiss Coordinate Grid around Zurich.
    """
    for f in geojson['features']:
        for polygon in f['geometry']['coordinates']:
            for point in polygon:
                point[0] += offset[0]
                point[1] += offset[1]


def download(url, fname):
    with open(fname, 'wb') as f:
        f.write(requests.get(url).content)

def save_json(data, fname):
    with open(fname, 'w') as f:
        json.dump(data, f)

# TODO would be neat to somehow use doit's stuff to not have to load the same
# file multiple times
def load_json(fname):
    with open(fname) as f:
        return json.load(f)

# end utils

DOIT_CONFIG = {'action_string_formatting': 'new'}

# TODO make task title formatting pretty

def task_data():
    "Prepare data"
    # TODO implement dependencies on all data tasks

    return {
        'actions': [],
    }

def task_data_download():
    """Download raw data files from Swiss open data sources

    See data_sources.yml for attribution and info on where I discovered them.
    With thanks to opendata.swiss.
    """
    for name, meta in DATA_SOURCES.items():
        yield {
            'basename': 'data:download',
            'name':     name,
            'title':    lambda task: f'{task.name} ({meta["description"]})  -> {task.targets[0]}',
            'targets':  [DATA/meta['filename']],
            'actions':  [(download, (meta['url'], DATA/meta['filename']))],
            'uptodate': [config_changed(meta['url'])],
        }

def task_data_split_by_canton():
    """Split data by canton

    Filter out the raw files to create per-canton data. We do this to avoid
    having to work with large files, as we always do things per canton anyway.
    """

    def save_canton(canton, fname):
        save_json(filter_canton(load_json(DATA/'plz.geojson'), canton), fname)

    for canton in CANTONS:
        fname = 'plz-{}.geojson'.format(canton)
        yield {
            'basename': 'data:split_by_canton',
            'name':     canton,
            'title':    lambda task: f'{task.name}  -> {task.targets[0]}',
            'targets':  [DATA/fname],
            'file_dep': [DATA/'plz.geojson'],
            'actions':  [(save_canton, (canton, DATA/fname))],
        }

def task_data_cleanup():
    """Fixup coordinates and remove unused properties

    Switzerland uses its own Very Special coordinate grid. Swisstopo.ch
    provides conversion tools at
    https://www.swisstopo.admin.ch/de/karten-daten-online/calculation-services.html ,
    but that does not work with GeoJSON, and I did not want to convert back and
    forth between things (or convert the coordinates one by one).
    Thus, I eyeballed a constant offset that looks about right around Zurich O:-)

    We also remove unneeded properties to make the resulting GeoJSON files
    smaller and thus faster to download to the client.
    """

    def prodify(geojson):
        for f in geojson['features']:
            # centerpoint = f['properties']['geo_point_2d']
            new_props = {'ortbez': 'ortbez27', 'plz': 'postleitzahl'}
            f['properties'] = { k: f['properties'][v] for k, v in new_props.items() }
            # f['properties']['centerpoint'] = [centerpoint['lat'], centerpoint['lon']]

    def save_fixed(in_fname, out_fname):
        geojson = load_json(in_fname)
        offset_coordinates(geojson)
        prodify(geojson)
        save_json(geojson, out_fname)

    for canton in CANTONS:
        in_fname  = 'plz-{}.geojson'.format(canton)
        out_fname = 'plz-{}-fixed.geojson'.format(canton)
        yield {
            'basename': 'data:cleanup',
            'name':     canton,
            'title':    lambda task: f'{task.name}  -> {task.targets[0]}',
            'targets':  [DATA/out_fname],
            'file_dep': [DATA/in_fname],
            'actions':  [(save_fixed, (DATA/in_fname, DATA/out_fname))],
        }

def task_geodata_simplify():
    """Simplify geometry to make the geo data faster to render

    Even after splitting by canton and removing unused properties, the GeoJSON
    file is about 5MB and takes a good while to load and render.
    Thus, here we simplify the geometry by removing vertices from "almost
    straight" lines. This reduces precision a little, but saves a lot of space.

    We use [Mapshaper](https://github.com/mbloch/mapshaper), which you need to
    install using `npm` (see the GitHub page for detailed instructions).
    The settings below were picked by trial and error and seem to produce a
    decent tradeoff between precision and file size, but suggestions on
    improving this step would be very welcome.
    """
    for canton in CANTONS:
        yield {
            'basename': 'geodata:simplify',
            'name':     canton,
            'title':    lambda task: f'{task.name}  -> {task.targets[0]}',
            'file_dep': [DATA/'plz-{}-fixed.geojson'.format(canton)],
            'targets':  [DATA/'plz-{}-lowres.geojson'.format(canton)],
            'actions':  ['mapshaper {dependencies} -simplify 10% keep-shapes -o {targets}'],
        }
