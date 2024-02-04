# Copyright (c) 2023-2024 Berlin zaehlt Mobilitaet
# SPDX-License-Identifier: MIT

# @file    common.py
# @author  Michael Behrisch
# @date    2023-01-15

import argparse
import json
import pprint
import random
import sys
import time

import requests


GEO_JSON_NAME = "bzm_telraam_segments.geojson"


class ConnectionProvider:
    def __init__(self, tokens, url):
        self._connections = []
        for t in tokens:
            s = requests.Session()
            s.headers.update({ 'X-Api-Key': t })
            self._connections.append(s)
        self._index = random.randint(0, len(self._connections) - 1)
        self._num_queries = 0
        self._url = url

    def request(self, path, method='GET', payload='', retries=0, required=None):
        for _ in range(retries + 1):
            self._num_queries += 1
            time.sleep(1.1 / len(self._connections))
            conn = self._connections[self._index]
            self._index = (self._index + 1) % len(self._connections)
            response = conn.request(method, self._url + path, data=payload).json()
            if response.get("message") == "Too Many Requests":
                print("Warning:", response["message"], file=sys.stderr)
                continue
            if "errorMessage" in response:
                print("Error on %s %s." % (path, payload), response["errorMessage"],
                      response.get("errorType"), response.get("stackTrace"), file=sys.stderr)
            elif required and required not in response:
                print("Format error on %s %s." % (path, payload), file=sys.stderr)
                pprint.pp(response, sys.stderr)
            return response
        return {}

    def print_stats(self):
        print(len(self._connections), "connections", self._num_queries, "queries")


def get_options(args=None, json_default="sensor.json"):
    parser = argparse.ArgumentParser()
    # Berlin as in https://github.com/DLR-TS/sumo-berlin
    parser.add_argument("-b", "--bbox", default="12.78509,52.17841,13.84308,52.82727",
                        help="bounding box to retrieve in geo coordinates west,south,east,north")
    parser.add_argument("-u", "--url", default="telraam-api.net",
                        help="Download from the given Telraam server")
    parser.add_argument("-s", "--secrets-file", default="secrets.json",
                        metavar="FILE", help="Read Telraam API and database credentials from FILE")
    parser.add_argument("--js-file", default="sensor-geojson.js",
                        metavar="FILE", help="Write Geo-JSON as javascript to FILE")
    parser.add_argument("-j", "--json-file", default=json_default,
                        metavar="FILE", help="Write / read Geo-JSON for segments to / from FILE")
    parser.add_argument("--excel",
                        help="Excel input file")
    parser.add_argument("--osm", action="store_true", default=False,
                        help="recreate OpenStreetMap data even if it is present")
    parser.add_argument("-d", "--database",
                        help="Database output file or URL")
    parser.add_argument("--csv",
                        help="Output prefix for monthly csv files")
    parser.add_argument("--csv-segments",
                        help="Output prefix for csv segment files")
    parser.add_argument("-y", "--csv-start-year", type=int,
                        help="First year to retrieve when writing csv")
    parser.add_argument("-r", "--retry", type=int, default=1,
                        help="number of retries on failure")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="increase verbosity, twice enables verbose sqlalchemy output")
    options = parser.parse_args(args=args)
    with open(options.secrets_file, encoding="utf8") as sf:
        options.secrets = json.load(sf)
    if not options.database:
        options.database = options.secrets.get("database", "backup.db")
    if "+" not in options.database and "://" not in options.database:
        options.database = "sqlite+pysqlite:///" + options.database
    if options.url and "://" not in options.url:
        options.url = "https://" + options.url
    return options
