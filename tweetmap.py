#!/usr/bin/env python3

import argparse
import copy
import csv
import fileinput
import functools
import json
import multiprocessing
import sys
import textwrap

from collections import Counter
from colorsys import hls_to_rgb
from descartes import PolygonPatch
from matplotlib import pyplot
from matplotlib.colors import rgb2hex
from numbers import Number
from pyproj import Proj
from shapely.geometry import shape, MultiPolygon, Point, Polygon

def AlbersUsaProjection():
    """
    Create function to project coordinates using an Albers USA projection.
    """

    # Based on D3's AlbersUSA projection
    # https://github.com/mbostock/d3/blob/master/src/geo/albers-usa.js
    # http://spatialreference.org/ref/esri/usa-contiguous-albers-equal-area-conic/
    lower48 = Proj("+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")
    # http://spatialreference.org/ref/epsg/nad83-alaska-albers/
    alaska = Proj("+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")
    # http://spatialreference.org/ref/esri/hawaii-albers-equal-area-conic/
    hawaii = Proj("+proj=aea +lat_1=8 +lat_2=18 +lat_0=13 +lon_0=-157 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs")

    def _projection(lon, lat):
        """
        Project coordinates using an AlbersUSA projection.

        Arguments:
        lon -- Longitude of coordinate to project.
        lat -- Latitude of coordinate to project.
        """
        if lat > 50:
            (x, y) = alaska(lon, lat)
            x = x * 0.35 - 2250000
            y = y * 0.35 - 1250000
            return (x, y)
        elif lon < -140:
            (x, y) = hawaii(lon, lat)
            x = x - 1250000
            y = y - 1750000
            return (x, y)
        else:
            (x, y) = lower48(lon, lat)
            if lat < 20: # Puerto Rico
                x = x - 1125000
                y = y + 750000
            return (x, y)

    return _projection

def projected_features(features, projection):
    """
    Project coordinates in a collection of features.

    Arguments:
    features -- The features whose coordinates to project.
    projection -- The projection to project with.
    """

    def _project_coordinates(coordinates):
        """
        Helper function to project coordinates in a feature. Modifies coordinates in place.

        Feature coordinates are nested lists of coordinates.
        Ex. A point feature would be [lon, lat]
            A polygon feature [[lon1, lat1], [lon2, lat2], ...]
            A multi polygon feature [[[p1lon1, p1lat1], ...], [[p2lon1, p2lat1], ...], ...]

        This function recurses to handle all those cases.

        Arguments:
        coordinates -- The coordinates to project.
        """
        # A list of two numbers is a coordinate
        if [isinstance(c, Number) for c in coordinates] == [True, True]:
            return list(projection(*coordinates))
        # Otherwise, it's a list of coordinates, so recurse
        else:
            return [_project_coordinates(c) for c in coordinates]

    p_features = copy.deepcopy(features)
    for f in p_features:
        f["geometry"]["coordinates"] = _project_coordinates(f["geometry"]["coordinates"])
    return p_features

def feature_set_bounds(features):
    """
    Find the bounds of a collection of features.

    Arguments:
    features -- The features to find boundaries of.

    Returns:
    ((min x, max x), (min y, max y))
    """

    min_x = min_y = sys.float_info.max
    max_x = max_y = sys.float_info.min

    def _find_coordinate_bounds(coordinates):
        # See project_coordinate documentation for explanation of coordinates argument.

        nonlocal min_x, min_y, max_x, max_y

        # A list of two numbers is a coordinate
        if [isinstance(c, Number) for c in coordinates] == [True, True]:
            [x, y] = coordinates
            max_x = max(max_x, x)
            min_x = min(min_x, x)
            max_y = max(max_y, y)
            min_y = min(min_y, y)

        # Otherwise, it's a list of coordinates, so recurse
        else:
            for c in coordinates:
                _find_coordinate_bounds(c)

    for f in features:
        _find_coordinate_bounds(f["geometry"]["coordinates"])

    return ((min_x, max_x), (min_y, max_y))

def extract_location(keypath, location_format):
    """
    Create a function to extract a location (as a shapely.geometry.Point) from an object.

    Arguments
    keypath -- the keypath where the location object can be found
    location_format -- the format of the location object
        "lat-lon-array" - [<lat>, <lon>]
        "lon-lat-array" - [<lon>, <lat>]
        "lat-lon-dict"  - {"lat": <lat>, "lon": <lon>}
    """
    def _extract_location(obj):
        """
        Extract a location (as a shapely.geometry.Point) from an object.

        Arguments:
        obj -- The object to extract a location from.
        """
        try:
            location = functools.reduce(lambda o, p: o[p], keypath, obj)
            if location_format == "lat-lon-array":
                return Point(reversed(location))
            elif location_format == "lon-lat-array":
                return Point(location)
            elif location_format == "lat-lon-dict":
                return Point([location["lon"], location["lat"]])
            else:
                raise ValueError("Invalid location format: \"%s\"" % location_format)
        except (KeyError, IndexError, TypeError):
            return None

    return _extract_location

def find_containing_feature(features):
    """
    Create a function to find which out of the given features contains a specific point.

    Arguments:
    features -- Iterable collection of GeoJSON formatted features.
    """
    def _find_containing_feature(point):
        """
        Find which out of a collection of features contains a specific point.

        Arguments:
        point -- shapely.geometry.Point. The point whose containing feature we want to find.
        """
        for f in features:
            s = shape(f["geometry"])
            if s.contains(point):
                return f["properties"]["id"]
        return None
    return _find_containing_feature

def shape2patches(s, **kwargs):
    """
    Convert a shapely.geometry.shape object into a descartes.PolygonPatch object in order to plot it.

    Arguments:
    s -- shapely.geometry.shape. The shape to convert to PolygonPatches.
    kwargs -- Keyword arguments to pass to PolygonPatch constructor.
    """
    if isinstance(s, MultiPolygon):
        return [PolygonPatch(p, **kwargs) for p in s.geoms]
    elif isinstance(s, Polygon):
        return [PolygonPatch(s, **kwargs)]
    else:
        raise TypeError("Unable to convert shape to patches")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("-k", "--key-path",
        default=["coordinates", "coordinates"],
        help=textwrap.dedent("""\
            Key path to location coordinates within Tweet

            coordinates coordinates for Twitter API Tweets
            See https://dev.twitter.com/overview/api/tweets

            geo coordinates for Gnip Activity Streams
            See http://support.gnip.com/sources/twitter/data_format.html"""),
        nargs="+")
    parser.add_argument("-l", "--location-format",
        choices=["lat-lon-array", "lon-lat-array", "lat-lon-dict"],
        default="lon-lat-array",
        help=textwrap.dedent("""\
            Format of coordinates within Tweet

            lon-lat-array for Twitter API Tweets
            See https://dev.twitter.com/overview/api/tweets

            lat-lon-array for Gnip Activity Streams
            See http://support.gnip.com/sources/twitter/data_format.html"""))
    parser.add_argument("-p", "--projection",
        default="albersUsa",
        help=textwrap.dedent("""\
            Map projection to use
            See pyproj.pj_list for available projections
            http://jswhit.github.io/pyproj/pyproj-module.html#pj_list"""))
    parser.add_argument("-f", "--features-file",
        default="feature_sets/us_states.geo.json",
        help=textwrap.dedent("""\
            File containing features to locate Tweets in
            File must contain a GeoJSON formatted FeatureCollection object
            See http://geojson.org/geojson-spec.html#feature-collection-objects"""))
    parser.add_argument("--hue",
        default=0.6,
        type=float,
        help="Hue (in range of [0, 1.0]) of shading on map")
    parser.add_argument("-o", "--output-file",
        help=textwrap.dedent("""\
            Path to output heatmap image to
            Image format will be determined by file extension
            Formats supported by matplotlib can be used
            See http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.savefig"""))
    parser.add_argument("data_files",
        help=textwrap.dedent("""\
            Files containing Tweets to locate
            Each file must contain one JSON encoded Tweet per line"""),
        nargs="+")

    args = parser.parse_args(sys.argv[1:])

    # Read features from file.
    features = None
    with open(args.features_file, "r") as f:
        features = json.loads(f.read())["features"]

    # Process Tweets. Decode each one, extract its location, and identify the feature containing it.
    extract = extract_location(args.key_path, args.location_format)
    identify_feature = find_containing_feature(features)
    def process_tweet(line):
        return identify_feature(extract(json.loads(line)))

    counter = Counter()
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    for feature_id in pool.imap_unordered(process_tweet, fileinput.input(files=args.data_files), chunksize=10):
        counter[feature_id] = counter[feature_id] + 1
    pool.close()
    pool.join()

    if len(list(counter)) == 1 and list(counter)[0] == None:
        print("Unable to locate any tweets", file=sys.stderr)
        sys.exit(1)

    # Get the highest Tweet count for a feature.
    most_common = counter.most_common(2)
    max_count = most_common[0][1]
    if most_common[0][0] is None:
        max_count = most_common[1][1]

    def feature_fill_color(count, max_count):
        """
        Set fill color of a feature based on the number of Tweets it contains.

        Arguments:
        count -- Number of Tweets contained in the feature to fill.
        max_count -- Max number of Tweets contained in any feature.
        """
        c = count / max_count
        l = 0.5 + (1 - c) / 2
        rgb = hls_to_rgb(args.hue, l, 1)
        return rgb2hex(list(rgb))

    # Project features to draw them on the map.
    projection = None
    if args.projection == "albersUsa":
        projection = AlbersUsaProjection()
    else:
        projection = Proj(proj=args.projection)
    projected_features = projected_features(features, projection)

    fig = pyplot.figure(1, figsize=(10,5))
    bounds = feature_set_bounds(projected_features)
    plot = fig.add_subplot(111, xlim=bounds[0], ylim=[n * 1.05 for n in bounds[1]])

    writer = csv.writer(sys.stdout)
    writer.writerow(["Feature", "Tweet Count"])

    for feature in sorted(projected_features, key=lambda f: f["properties"]["name"]):

        # Output features' Tweet counts.
        if counter[feature["properties"]["id"]]:
            writer.writerow([feature["properties"]["name"], counter[feature["properties"]["id"]]])

        # Plot the projected features.
        color = feature_fill_color(counter[feature["properties"]["id"]], max_count)
        patches = shape2patches(shape(feature["geometry"]), fc=color)
        for patch in patches:
            plot.add_patch(patch)

    if counter[None]:
        writer.writerow(["Unknown Location", counter[None]])

    # Save or show map.
    pyplot.axis("off")
    if args.output_file:
        pyplot.savefig(args.output_file, format="svg", bbox_inches="tight")
    else:
        pyplot.show()
