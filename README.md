# Tweetmap

Generate heatmaps from Tweets and GeoJSON features.


Usage:

```
tweetmap.py [-h] [-k KEY_PATH [KEY_PATH ...]]
            [-l {lat-lon-array,lon-lat-array,lat-lon-dict}]
            [-p PROJECTION] [-f FEATURES_FILE] [-o OUTPUT_FILE]
            data_files [data_files ...]
```

* `data_files`<br/>
    Files containing Tweets to locate<br/>
    Each file must contain one JSON encoded Tweet per line

* `-h, --help`<br/>
    Show this help message and exit

* `-k KEY_PATH [KEY_PATH ...], --key-path KEY_PATH [KEY_PATH ...]`<br/>
    Key path to location coordinates within Tweet

    `coordinates coordinates` for [Twitter API Tweets](https://dev.twitter.com/overview/api/tweets)

    `geo coordinates` for [Gnip Activity Streams](http://support.gnip.com/sources/twitter/data_format.html)

* ```-l {lat-lon-array,lon-lat-array,lat-lon-dict},
--location-format {lat-lon-array,lon-lat-array,lat-lon-dict}```<br/>
    Format of coordinates within Tweet

    `lon-lat-array` for [Twitter API Tweets](https://dev.twitter.com/overview/api/tweets)

    `lat-lon-array` for [Gnip Activity Streams](http://support.gnip.com/sources/twitter/data_format.html)

* `-p PROJECTION, --projection PROJECTION`<br/>
    Map projection to use<br/>
    See [pyproj.pj_list](http://jswhit.github.io/pyproj/pyproj-module.html#pj_list) for available projections<br/>

* `-f FEATURES_FILE, --features-file FEATURES_FILE`<br/>
    File containing features to locate Tweets in<br/>
    File must contain a GeoJSON formatted [FeatureCollection](http://geojson.org/geojson-spec.html#feature-collection-objects) object

* `--hue HUE`<br>
    Hue (in range of [0, 1.0]) of shading on map

* `-o OUTPUT_FILE, --output-file OUTPUT_FILE`<br/>
    Path to output heatmap image to<br/>
    Image format will be determined by file extension<br/>
    Formats supported by [matplotlib.pyplot.savefig](http://matplotlib.org/api/pyplot_api.html#matplotlib.pyplot.savefig) can be used

### Feature Sets GeoJSON

The world map GeoJSON was obtained from https://gist.github.com/markmarkoh/2969317/.

The US states and counties GeoJSON files were downloaded from http://eric.clst.org/Stuff/USGeoJSON.
They are based off shapefiles provided by the United States Census Bureau.
