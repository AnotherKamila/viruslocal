import functools
import json
import requests
import sys


def debug(*args, **kwargs):
    print(
        "{} {}".format(
            " ".join("{}".format(a) for a in args),
            " ".join("{}={}".format(k, v) for k, v in kwargs.items()),
        ),
        file=sys.stderr,
    )

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
