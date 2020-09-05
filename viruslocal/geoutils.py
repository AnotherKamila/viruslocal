import copy
import json

from .utils import as_json, save_json

def filter_canton(geojson, canton, save_as=None):
    def keep(feature):
        return (feature['geometry'] != None and
                feature['properties']['kanton'] == canton)

    geojson = as_json(geojson)
    res = copy.copy(geojson)
    res['features'] = [ f for f in geojson['features'] if keep(f) ]

    if save_as: save_json(res, save_as)
    else: return res


def copy_props(props_dict, geojson, save_as=None):
    geojson = as_json(geojson)
    res = copy.copy(geojson)
    for f in res['features']:
        f['properties'] = { k: f['properties'][v] for k, v in props_dict.items() }

    if save_as: save_json(res, save_as)
    else: return res


# def offset_coordinates(geojson, offset=(-0.00117, -0.00133)):
#     """
#     Offsets the coordinates in the GeoJSON file by an offset eyeballed to
#     approximately fix up the Special Swiss Coordinate Grid around Zurich.
#     """
#     geojson = as_json(geojson)
#     for f in geojson['features']:
#         for polygon in f['geometry']['coordinates']:
#             for point in polygon:
#                 point[0] += offset[0]
#                 point[1] += offset[1]


def check_props(geojson, checks):
    """TODO document this madness :D"""
    geojson = as_json(geojson)
    for feature in geojson['features']:
        for prop, check in checks.items():
            assert prop in feature['properties'], 'Required property "{}" missing'.format(prop)
            assert check(feature['properties'][prop]), 'Property "{}" check failed'.format(prop)


def replace_geometry(data, geom, save_as=None):
    """TODO document this madness :D"""
    data_geojson, data_key_fn = data
    geom_geojson, geom_key_fn = geom
    data_geojson = as_json(data_geojson)
    geom_geojson = as_json(geom_geojson)

    # 1. just remember which data we will need
    collected_geom = {}
    for feature in data_geojson['features']:
        key = data_key_fn(feature['properties'])
        collected_geom[key] = 'PLACEHOLDER'

    # 2. collect the needed geometry in an easy to index form
    for feature in geom_geojson['features']:
        key = geom_key_fn(feature['properties'])
        if key in collected_geom:
            collected_geom[key] = feature['geometry']

    # 3. stick it into result
    res = copy.deepcopy(data_geojson)
    for feature in res['features']:
        key = data_key_fn(feature['properties'])
        assert collected_geom[key] != 'PLACEHOLDER', 'Missing geometry for key {}'.format(key)
        feature['geometry'] = collected_geom[key]

    if save_as: save_json(res, save_as)
    else: return res
