import functools
import json
import requests
import sys
from pathlib import Path
from pprint import pprint

def debug(*args, **kwargs):
    print(
        "{} {}".format(
            " ".join("{}".format(a) for a in args),
            " ".join("{}={}".format(k, v) for k, v in kwargs.items()),
        ),
        file=sys.stderr,
    )

def pdebug(*args, **kwargs):
    for arg in args:
        print('*** ', end='', file=sys.stderr)
        pprint(arg, stream=sys.stderr)
    for k,v in kwargs.items():
        print(f'*** {k}: ', end='', file=sys.stderr)
        pprint(v, stream=sys.stderr)

def download(url, fname):
    with open(fname, 'wb') as f:
        f.write(requests.get(url).content)

def save_json(data, fname):
    with open(fname, 'w') as f:
        json.dump(data, f)

@functools.lru_cache(maxsize=32)
def load_json(fname):
    """Caches the file in memory if it has already been loaded.

    The assumption is that files do not change during a single execution
    (though they may change between executions, but that's fine).
    """
    with open(fname) as f:
        return json.load(f)

def as_json(obj):
    """Turns things into dicts by parsing them as JSON.

    When passed a file path or file object, it will read and parse it.
    No-op on things that are already dicts.
    Allows functions to transparently accept filenames, file objects, or
    already-parsed data.
    """
    if isinstance(obj, dict): return obj
    if hasattr(obj, 'read'):  return json.load(obj)
    if isinstance(obj, str) or isinstance(obj, Path):
        return load_json(obj)
    return ValueError(f"Don't know how to read type '{type(obj)}' as JSON")

