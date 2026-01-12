#!/usr/bin/env python3

"write lat/long details from GPX file to CSV format for use as course data"

import csv
import sys

import gpx
from haversine import haversine, Unit

ride = gpx.read_gpx("/dev/stdin")

writer = csv.DictWriter(sys.stdout, fieldnames="lat long dist".split())
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
        print(nxt, dst, tot, file=sys.stderr)
        writer.writerow({"lat": pt[0], "long": pt[1], "dist": dst})
