import copy
import json


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


def check_props(geojson, checks):
    """TODO document this madness :D"""
    for feature in geojson['features']:
        for prop, check in checks.items():
            assert prop in feature['properties'], 'Required property "{}" missing'.format(prop)
            assert check(feature['properties'][prop]), 'Property "{}" check failed'.format(prop)


def replace_geometry(data, geom):
    """TODO document this madness :D"""
    data_geojson, data_key_fn = data
    geom_geojson, geom_key_fn = geom

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
    result_geojson = copy.deepcopy(data_geojson)
    for feature in result_geojson['features']:
        key = data_key_fn(feature['properties'])
        assert collected_geom[key] != 'PLACEHOLDER', 'Missing geometry for key {}'.format(key)
        feature['geometry'] = collected_geom[key]

    return result_geojson
