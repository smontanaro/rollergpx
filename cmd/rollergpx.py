#!/usr/bin/env python

"""
Read a GPX file and produce a new one with details from a cadence-enhanced
roller ride.

Lots of people have smart trainers these days. I only have rollers, but in the
presence of something which can track cadence and knowledge of my gearing, I
can calculate the distance ridden during a roller session. My setup happens to
be a Wahoo Elemnt Bolt v1 and a Wahoo Tickr X heart rate monitor (which also
measures cadence), but I suppose anything which records your time and cadence
will suffice.

To make this work, you need gearing details. I use Sheldon Brown's gain ratio
and crank length to translate cadence into linear velocity:

https://www.sheldonbrown.com/gain.html

Inputs to that calculation are the crank arm length, tire circumference, and
chainring and sprocket tooth counts. Note that this will only work if you don't
shift gears!!! That works for me because I can rarely tolerate the boredom of
riding in my basement for more than 30 minutes or so. My goal here is simply to
have something plausible to upload to Strava so my January and February
mileages don't look so bad. YMMV.

"""

import argparse
import csv
import math
import sys

import gpx
from haversine import haversine

def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Augment a GPX file with distance details",
        allow_abbrev=False)

    parser.add_argument(
        "--crank", "-c", type=int, default=170,
        help="Crank arm length in millimeters")

    parser.add_argument(
        "--gain-ratio", "-g", type=float, default=5.0,
        help="Gain ratio, per Sheldon Brown: https://www.sheldonbrown.com/gain.html")

    parser.add_argument(
        "--course", "-C", default="",
        help="CSV file containing lat/long/distance details for the course")

    options = parser.parse_args(args)

    return options


class Course:
    "Hold lat/long details of a course and progress through it."
    def __init__(self, course_csv):
        if not course_csv:
            # no course data, give a default in Lake Michigan near Evanston
            self.points = [
                {"lat": 42.04, "long": -87.65, "dist": 0.0},
                {"lat": 42.06, "long": -87.65, "dist": 2.223901604671227},
                ]
        else:
            with open(course_csv, encoding="utf-8") as course:
                reader = csv.DictReader(course)
                self.points = list(reader)
                # convert lat/long/dist to floats
                for point in self.points:
                    for key in ("lat", "long", "dist"):
                        try:
                            point[key] = float(point[key])
                        except KeyError:
                            pass
                if "dist" not in reader.fieldnames:
                    # populate the segment distances
                    cur = 0
                    points = self.points
                    points[cur]["dist"] = 0.0
                    for nxt in range(1, len(points)):
                        pt1 = (points[cur]["lat"], points[cur]["long"])
                        pt2 = (points[nxt]["lat"], points[nxt]["long"])
                        points[nxt]["dist"] = haversine(pt1, pt2)
                        cur = nxt

        # current position along the course (might be betweeen two fixed
        # points)
        self.current = (self.points[0]["lat"], self.points[0]["long"])
        # index of next fixed point along the course
        self.next = 1

        # A course is deemed "out and back" if the distance between first
        # and last points is at least one kilometer.
        last = (self.points[-1]["lat"], self.points[-1]["long"])
        self.out_and_back = haversine(self.current, last) >= 1

    def move(self, distance):
        "Move along the course by the set distance (km)."
        # add distance to the position, following the course, returning the
        # new position
        points = self.points
        while distance:
            pt1 = self.current
            pt2 = (points[self.next]["lat"], points[self.next]["long"])
            next_waypoint = haversine(pt1, pt2)
            if next_waypoint < distance:
                distance -= next_waypoint
                self.next += 1
                self.current = pt2
                if self.next == len(points):
                    if self.out_and_back:
                        self.points = list(reversed(self.points))
                    self.next = 0
            else:
                ratio = distance / next_waypoint
                distance = 0
                clat = pt1[0] + (pt2[0] - pt1[0]) * ratio
                clon = pt1[1] + (pt2[1] - pt1[1]) * ratio
                self.current = (clat, clon)

        return self.current

def main(args=None):
    options = parse_args(args)

    ride = gpx.read_gpx("/dev/stdin")
    ride.wpt = ride.trk[0][0]

    # elevate the cadence value to a top level attribute (hopefully will change
    # at some point -- current extension gpx implementation is too low-level)
    for wpt in ride.wpt:
        for attr in wpt.extensions.elements[0]:
            if attr.tag.endswith("cad"):
                wpt.cad = int(attr.text)
                break

    # km
    crank_circum = options.crank * 0.000001 * math.pi
    course = Course(options.course)
    wpt1 = ride.wpt[0]
    for wpt2 in ride.wpt[1:]:
        # minutes
        dt = (wpt2.time - wpt1.time).total_seconds() * 60
        mean_cadence = (wpt2.cad + wpt1.cad) / 2
        # revolutions per minute
        revs = mean_cadence / dt
        dist = revs * options.gain_ratio * crank_circum
        (lat, long) = course.move(dist)
        wpt2.lat = lat
        wpt2.lon = long
        wpt1 = wpt2

    # have to undo the .wpt shortcut (again, hopefully this won't be necessary indefinitely)
    ride.wpt = []
    ride.write_gpx("/dev/stdout")

    return 0


if __name__ == "__main__":
    sys.exit(main())
