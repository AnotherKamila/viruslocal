import json
import yaml

from pathlib import Path
from doit.tools import config_changed

from viruslocal import geoutils
from viruslocal.utils import debug, download, load_json, save_json

DEFAULT_TASKS = ['data']
CANTONS = ['ZH']
DATA = Path('./data')
DATA.mkdir(exist_ok=True)

with open('./data_sources.yml') as f:
    DATA_SOURCES = yaml.safe_load(f)


DOIT_CONFIG = {
    'default_tasks': DEFAULT_TASKS,
    'action_string_formatting': 'new',
}

def tsk(basename, task, obj=None):
    """Merge in some defaults for task creation"""
    if not obj: obj, task = task, None  # argument order
    return {
        'basename': basename,
        'name':     task,
        'title':    lambda t: f'{t.name}  -> {t.targets[0]}',
        'clean':    True,
        **obj,  # merge in, overriding previous
    }

# TODO make use of https://pydoit.org/tasks.html#keywords-on-python-action

def task_data():
    "Prepare data"
    return {'task_dep': ['data:*'], 'actions': []}

def task_data_download():
    """Download raw data files from Swiss open data sources

    See data_sources.yml for attribution and info on where I discovered them.
    With thanks to opendata.swiss.
    """
    for name, meta in DATA_SOURCES.items():
        yield tsk('data:download', name, {
            'title':    lambda task: f'{task.name} ({meta["description"]})  -> {task.targets[0]}',
            'targets':  [DATA/meta['filename']],
            'actions':  [(download, (meta['url'], DATA/meta['filename']))],
            'uptodate': [config_changed(meta['url'])],
        })

def task_data_split_by_canton():
    """Split data by canton

    Filter out the raw files to create per-canton data. We do this to avoid
    having to work with large files, as we always do things per canton anyway.
    """
    for canton in CANTONS:
        fname = 'plz-{}.geojson'.format(canton)
        yield tsk('data:split_by_canton', canton, {
            'targets':  [DATA/fname],
            'file_dep': [DATA/'plz.geojson'],
            'actions':  [(geoutils.filter_canton, (DATA/'plz.geojson', canton, DATA/fname))],
        })

# TODO update doc
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
    my_props = {'ortbez': 'ortbez27', 'plz': 'postleitzahl'}
    for canton in CANTONS:
        in_fname  = 'plz-{}-fixed.geojson'.format(canton)
        out_fname = 'plz-{}-fewprops.geojson'.format(canton)
        yield tsk('data:cleanup', canton, {
            'targets':  [DATA/out_fname],
            'file_dep': [DATA/in_fname],
            'actions':  [(geoutils.copy_props, (my_props, DATA/in_fname, DATA/out_fname))],
        })

def task_data_simplify():
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
        yield tsk('data:simplify', canton, {
            'file_dep': [DATA/'plz-{}-fewprops.geojson'.format(canton)],
            'targets':  [DATA/'plz-{}-lowres.geojson'.format(canton)],
            'actions':  ['mapshaper snap {dependencies} -simplify 10% keep-shapes -o {targets}'],
        })

def task_data_sanity_check():
    """Check assumptions about data files"""

    ### Check assumptions about properties in GeoJSON files
    files = {
        'plz.geojson': {
            'postleitzahl': lambda p: isinstance(p, int) and 1000 <= p <= 9999,
            'plz_zz':       lambda p: isinstance(p, str) and len(p) == 2,
        },
        'PLZO_PLZ.geojson': {
            'PLZ':     lambda p: isinstance(p, int) and 1000 <= p <= 9999,
            'ZUSZIFF': lambda p: isinstance(p, int) and 0 <= p <= 99,
        },
    }
    for fname, checks in files.items():
        yield tsk('data:sanity_check', fname, {
            'title':    lambda task: f'{task.name}  -> {next(iter(task.file_dep))}',
            'file_dep': [DATA/fname],
            'actions':  [(geoutils.check_props, (DATA/fname, checks))],
        })

    # ### Check consistency among data sources
    # yield {
    #     'basename': 'data:sanity_check',
    #     'name':     'plzzz',  # XD
    #     'title':    lambda task: f'{task.name}  -> {" ".join(task.file_dep)}',
    #     'file_dep': [DATA/'plz.geojson'],
    #     'actions':  [(check_file, (DATA/fname, checks))],
    # }

def task_data_join_swisstopo_geometry():
    """Join SwissTopo PLZ geo data with the Swiss Post DB

    The Swiss Post has Interesting Opinions about geography (they believe in
    flat Earth and such). The topo data from the city of Zurich can be
    persuaded to actually match the map, so we use that for the geometry, and
    take the data from the post's file.
    """
    geom_key = lambda props: f"{props['PLZ']:04d}{props['ZUSZIFF']:02d}"
    data_key = lambda props: f"{props['postleitzahl']:04d}{props['plz_zz']}"
    for canton in CANTONS:
        data_f   = f'plz-{canton}.geojson'
        geom_f   = 'PLZO_PLZ.geojson'
        target_f = f'plz-{canton}-fixed.geojson'
        yield tsk('data:join_swisstopo_geometry', canton, {
            'file_dep': [DATA/data_f, DATA/geom_f, DATA/'plz.geojson'],
            'task_dep': ['data:sanity_check:{}'.format(f) for f in [geom_f, 'plz.geojson']],
            'targets':  [DATA/target_f],
            'actions':  [(geoutils.replace_geometry, [], dict(
                    data=(DATA/data_f, data_key),
                    geom=(DATA/geom_f, geom_key),
                    save_as=DATA/target_f,
                ))]
        })
