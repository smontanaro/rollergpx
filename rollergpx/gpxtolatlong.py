#!/usr/bin/env python3

"write lat/long details from GPX file to CSV format for use as course data"

import argparse
import csv
import sys
import xml.etree.ElementTree as ET

from haversine import haversine, Unit


EPS = 10e-8

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract lat/long bits from a GPX file to use as course data",
        allow_abbrev=False)

    parser.add_argument(
        "--infile", "-i", default="/dev/stdin",
        help="GPX file from which to harvest lat/long data")

    parser.add_argument(
        "--outfile", "-o", default="/dev/stdout",
        help="Generated CSV file containing lat/long/distance details for the course")

    return parser.parse_args()


def main():
    options = parse_args()

    with open(options.infile, encoding="utf-8") as infile:
        tree = ET.parse(infile)

    tot = 0.0
    dist = 0.0
    with open(options.outfile, "w", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames="lat long dist".split())
        writer.writeheader()

        lastpt = ()
        for trkpt in tree.iterfind(".//{*}trkpt"):
            thispt = (float(trkpt.attrib["lat"]), float(trkpt.attrib["lon"]))
            if thispt == lastpt:
                # The GPX file for the velodrome course I created in RwGPS
                # appears to duplicate all the points. ¯\_(ツ)_/¯
                continue
            if lastpt:
                dist = haversine(thispt, lastpt, unit=Unit.KILOMETERS)
                tot += dist
            lastpt = thispt
            writer.writerow({"lat": thispt[0],
                            "long": thispt[1],
                            "dist": dist})

    print(f"total distance: {tot:.2f}km", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
