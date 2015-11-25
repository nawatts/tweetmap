# Tweetmap

Generate heatmaps from Tweets and GeoJSON features.

## Installation:

Mac OS:
```Shell
brew install geos
pip install -r requirements.txt
```

## Usage:

```
usage: tweetmap.py [-h] [-k KEY_PATH [KEY_PATH ...]]
                   [-l {lat-lon-array,lon-lat-array,lat-lon-dict}]
                   [-p PROJECTION] [-f FEATURES_FILE] [--hue HUE]
                   [-o OUTPUT_FILE]
                   data_files [data_files ...]

positional arguments:
  data_files            Files containing Tweets to locate
                        Each file must contain one JSON encoded Tweet per line

optional arguments:
  -h, --help            show this help message and exit
  -k KEY_PATH [KEY_PATH ...], --key-path KEY_PATH [KEY_PATH ...]
                        Key path to location coordinates within Tweet

                        coordinates coordinates for Twitter API Tweets
                        See https://dev.twitter.com/overview/api/tweets

                        geo coordinates for Gnip Activity Streams
                        See http://support.gnip.com/sources/twitter/data_format.html
  -l {lat-lon-array,lon-lat-array,lat-lon-dict}, --location-format {lat-lon-array,lon-lat-array,lat-lon-dict}
                        Format of coordinates within Tweet

                        lon-lat-array for Twitter API Tweets
                        See https://dev.twitter.com/overview/api/tweets

                        lat-lon-array for Gnip Activity Streams
                        See http://support.gnip.com/sources/twitter/data_format.html
  -p PROJECTION, --projection PROJECTION
                        Map projection to use
                        See pyproj.pj_list for available projections
                        http://jswhit.github.io/pyproj/pyproj-module.html#pj_list
  -f FEATURES_FILE, --features-file FEATURES_FILE
                        File containing features to locate Tweets in
                        File must contain a GeoJSON formatted FeatureCollection object
                        See http://geojson.org/geojson-spec.html#feature-collection-objects
  --hue HUE             Hue (in range of [0, 1.0]) of shading on map
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Path to output heatmap image to
                        Image format will be determined by file extension
                        Formats supported by matplotlib can be used
                        See http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.savefig
```

### Feature Sets GeoJSON

The world map GeoJSON was obtained from https://gist.github.com/markmarkoh/2969317/.

The US states and counties GeoJSON files were downloaded from http://eric.clst.org/Stuff/USGeoJSON.
They are based off shapefiles provided by the United States Census Bureau.
