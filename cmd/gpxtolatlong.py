#!/usr/bin/env python3

"write lat/long details from GPX file to CSV format for use as course data"

import argparse
import csv
import sys

import gpx
from haversine import haversine, Unit

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract lat/long bits from a GPX file to use as course data",
        allow_abbrev=False)

    parser.add_argument(
        "infile", "-i", default="/dev/stdin",
        help="GPX file from which to harvest lat/long data")

    parser.add_argument(
        "outfile", "-o", default="/dev/stdout",
        help="Generated CSV file containing lat/long/distance details for the course")

    return parser.parse_args()


def main():
    options = parse_args()

    ride = gpx.read_gpx(options.infile)
    ride.wpt = ride.trk[0][0]

    writer = csv.DictWriter(options.outfile, fieldnames="lat long dist".split())
    writer.writeheader()

    ride.wpt = ride.trk[0][0]

    pt = (ride.wpt[0].lat, ride.wpt[0].lon)

    writer.writerow({"lat": pt[0], "long": pt[1], "dist": 0.0})

    tot = 0.0
    for wpt in ride.wpt[1:]:
        nxt = (wpt.lat, wpt.lon)
        if nxt != pt:
            dst = haversine(pt, nxt, unit=Unit.KILOMETERS)
            tot += dst
            pt = nxt
            writer.writerow({"lat": pt[0], "long": pt[1], "dist": dst})

    return 0


if __name__ == "__main__":
    sys.exit(main())
