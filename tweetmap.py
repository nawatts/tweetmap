#!/usr/bin/env python

import copy
import csv
import fileinput
import functools
import json
import multiprocessing
import sys

from collections import Counter
from colorsys import hls_to_rgb
from descartes import PolygonPatch
from enum import Enum
from matplotlib import pyplot
from matplotlib.colors import rgb2hex
from numbers import Number
from pyproj import Proj
from shapely.geometry import shape, MultiPolygon, Point, Polygon

class AlbersUsaProjection:

    def __init__(self):
        # Based on D3's AlbersUSA projection
        # https://github.com/mbostock/d3/blob/master/src/geo/albers-usa.js
        # http://spatialreference.org/ref/esri/usa-contiguous-albers-equal-area-conic/
        self.lower48 = Proj("+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")
        # http://spatialreference.org/ref/epsg/nad83-alaska-albers/
        self.alaska = Proj("+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")
        # http://spatialreference.org/ref/esri/hawaii-albers-equal-area-conic/
        self.hawaii = Proj("+proj=aea +lat_1=8 +lat_2=18 +lat_0=13 +lon_0=-157 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")

    def __call__(self, lon, lat):
        if lat > 50:
            (x, y) = self.alaska(lon, lat)
            x = x * 0.35 - 2250000
            y = y * 0.35 - 1250000
            return (x, y)
        elif lon < -140:
            (x, y) = self.hawaii(lon, lat)
            x = x - 1250000
            y = y - 1750000
            return (x, y)
        else:
            (x, y) = self.lower48(lon, lat)
            if lat < 20: # Puerto Rico
                x = x - 1125000
                y = y + 750000
            return (x, y)

class ProjectedFeatures:

    def __init__(self, projection, features):
        self.projection = projection
        self.features = copy.deepcopy(features)
        self.min_x = self.min_y = sys.float_info.max
        self.max_x = self.max_y = sys.float_info.min

        for f in self.features:
            f["geometry"]["coordinates"] = self._project_coordinates(f["geometry"]["coordinates"])

    def _project_coordinates(self, coordinates):
        # A list of two numbers is a coordinate
        if [isinstance(c, Number) for c in coordinates] == [True, True]:
            (x, y) = self.projection(*coordinates)
            self.max_x = max(self.max_x, x)
            self.min_x = min(self.min_x, x)
            self.max_y = max(self.max_y, y)
            self.min_y = min(self.min_y, y)
            return [x, y]
        # Otherwise, it's a list of coordinates, so recurse
        else:
            return [self._project_coordinates(c) for c in coordinates]

    def __iter__(self):
        return iter(self.features)

    def x_bounds(self):
        return [self.min_x, self.max_x]

    def y_bounds(self):
        return [self.min_y * 1.05, self.max_y * 1.05]

class LocationFormat(Enum):
    lat_lon_array = 1
    lon_lat_array = 2
    lat_lon_dict = 3

class ExtractLocation:

    def __init__(self, keypath, location_format):
        self.keypath = keypath
        self.location_format = location_format

    def __call__(self, obj):
        try:
            location = functools.reduce(lambda o, p: o[p], self.keypath, obj)
            if self.location_format == LocationFormat.lat_lon_array:
                return reversed(location)
            elif self.location_format == LocationFormat.lon_lat_array:
                return location
            elif self.location_format == LocationFormat.lat_lon_dict:
                return [location["lon"], location["lat"]]
        except (KeyError, IndexError, TypeError):
            return None

def locate_tweet(features, extract_location, tweet):
    tweet = json.loads(tweet)
    location = Point(extract_location(tweet))
    for feature in features:
        s = shape(feature["geometry"])
        if s.contains(location):
            return feature["properties"]["id"]
    return None

def shape2patches(s, **kwargs):
    if isinstance(s, MultiPolygon):
        return [PolygonPatch(p, **kwargs) for p in s.geoms]
    elif isinstance(s, Polygon):
        return [PolygonPatch(s, **kwargs)]
    else:
        raise TypeError("Unable to convert shape to patches")

if __name__ == "__main__":

    features = None
    with open("feature_sets/us_states.geo.json", "r") as f:
        features = json.loads(f.read())["features"]

    extract = ExtractLocation(["geo", "coordinates"], LocationFormat.lat_lon_array)
    counter = Counter()
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    for feature_id in pool.imap_unordered(functools.partial(locate_tweet, features, extract), fileinput.input(), chunksize=10):
        counter[feature_id] = counter[feature_id] + 1
    pool.close()
    pool.join()

    # Get the highest Tweet count for a feature
    most_common = counter.most_common(2)
    max_count = most_common[0][1]
    if most_common[0][0] is None:
        max_count = most_common[1][1]

    def feature_fill_color(count, max_count):
        c = count / max_count
        l = 0.5 + (1 - c) / 2
        rgb = hls_to_rgb(0.6, l, 1)
        return rgb2hex(list(rgb))

    projected_features = ProjectedFeatures(AlbersUsaProjection(), features)
    #projected_features = ProjectedFeatures(Proj(proj="merc"), features)

    fig = pyplot.figure(1, figsize=(10,5))
    plot = fig.add_subplot(111, xlim=projected_features.x_bounds(), ylim=projected_features.y_bounds())

    writer = csv.writer(sys.stdout)
    writer.writerow(["Feature", "Tweet Count"])

    for feature in sorted(projected_features, key=lambda f: f["properties"]["name"]):

        if counter[feature["properties"]["id"]]:
            writer.writerow([feature["properties"]["name"], counter[feature["properties"]["id"]]])

        color = feature_fill_color(counter[feature["properties"]["id"]], max_count)
        patches = shape2patches(shape(feature["geometry"]), fc=color)
        for patch in patches:
            plot.add_patch(patch)

    if counter[None]:
        writer.writerow(["Unknown Location", counter[None]])

    #pyplot.axis("off")
    #pyplot.savefig("test.svg", format="svg", bbox_inches="tight")
    pyplot.show()
