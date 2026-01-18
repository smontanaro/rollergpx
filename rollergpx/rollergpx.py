#!/usr/bin/env python

"""
Read a GPX file and produce a new one with details from a cadence-enhanced
roller ride.

See README.md for more details.
"""

import argparse
import csv
import datetime
import math
import sys
import xml.etree.ElementTree as ET

import dateutil.parser
from haversine import haversine

EPOCH = datetime.datetime.fromtimestamp(0)

__all__ = ["Course"]

def parse_args():
    parser = argparse.ArgumentParser(
        description="Augment a GPX file with distance details",
        allow_abbrev=False)

    parser.add_argument(
        "--crank-length", "-c", type=int, default=170,
        help="Crank arm length in millimeters")

    parser.add_argument(
        "--gain-ratio", "-g", type=float, default=5.0,
        help="Gain ratio, per Sheldon Brown: https://www.sheldonbrown.com/gain.html")

    parser.add_argument(
        "--course", "-C", default="",
        help="CSV file containing lat/long/distance details for the course")

    parser.add_argument(
        "--verbose", "-v", default=False, action='store_true',
        help="add a bit of debugging output")

    return parser.parse_args()


class Course:
    """Hold lat/long details of a course and progress through it.

    * course_csv - CSV file containing lat/long details for a course you will "ride"
    * dist_per_rev - Distance (in km) per revolution of the cranks
    * verbose - Display a bit of debugging output if True

    Normal usage is to create a Course object, then repeatedly call its
    update_lat_long with a series of <trkpt> elements from a GPX file, e.g.:

    tree = ET.parse("/some/gpx/file")
    for trkpt in tree.iterfind(".//{*}trkpt"):
        course.update_lat_long(trkpt)

    """
    def __init__(self, course_csv, dist_per_rev, verbose):
        self.last_cadence = 0
        self.last_stamp = EPOCH
        self.dist_per_rev = dist_per_rev
        self.nmoves = 0
        self.total = 0.0
        self.verbose = verbose

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
        "Move along the course by the given distance (km)."
        # add distance to the position, following the course, returning the
        # new position
        self.nmoves += 1
        if distance:
            points = self.points
            while distance:
                pt1 = self.current
                pt2 = (points[self.next]["lat"], points[self.next]["long"])
                next_waypoint = haversine(pt1, pt2)
                if next_waypoint <= distance:
                    # remaining distance at least reaches pt2. Adjust and
                    # continue.
                    distance -= next_waypoint
                    self.current = pt2
                    self.next += 1
                    if self.next == len(points):
                        if self.verbose:
                            print(f"end of course, next=={self.next},"
                                  f" moves={self.nmoves},"
                                  f" distance={self.total:.2f}km",
                                  file=sys.stderr)
                        if self.out_and_back:
                            # flip and go the other way
                            if self.verbose:
                                print("out and back", file=sys.stderr)
                            self.points = list(reversed(self.points))
                        self.next = 0
                else:
                    # distance from pt1 to pt2 is greater than the remaining
                    # distance. Adjust our current position to that fractional
                    # distance, but don't advance self.next, then return.
                    frac = distance / next_waypoint
                    assert 0.0 < frac <= 1.0
                    distance = 0
                    clat = pt1[0] + (pt2[0] - pt1[0]) * frac
                    clon = pt1[1] + (pt2[1] - pt1[1]) * frac
                    self.current = (clat, clon)

        return [str(x) for x in self.current]

    def cadence(self, trkpt):
        cadence = 0
        cadstr = self._child_tag_text(trkpt, "cad").strip()
        if cadstr:
            cadence = int(cadstr)
        return cadence

    def timestamp(self, trkpt):
        dt = EPOCH
        dtstr = self._child_tag_text(trkpt, "time").strip()
        if dtstr:
            dt = dateutil.parser.parse(dtstr)
        return dt

    def _child_tag_text(self, trkpt, tag):
        for child in trkpt.iterfind(f".//{{*}}{tag}"):
            return child.text
        return ""

    def update_lat_long(self, trkpt):
        "adjust the lat long details for the trkpt arg."
        stamp = self.timestamp(trkpt)
        assert stamp
        if self.last_stamp == EPOCH:
            # first time through
            self.last_stamp = stamp
            self.last_cadence = self.cadence(trkpt)
            (trkpt.attrib["lat"],
             trkpt.attrib["lon"]) = (str(self.points[0]["lat"]),
                                     str(self.points[0]["long"]))
            return

        cadence = self.cadence(trkpt)
        delta_t = (stamp - self.last_stamp).total_seconds() * 60
        mean_cadence = (cadence + self.last_cadence) / 2
        revs = mean_cadence / delta_t
        # km
        distance = revs * self.dist_per_rev
        self.total += distance
        (trkpt.attrib["lat"],
         trkpt.attrib["lon"]) = self.move(distance)

        # set up for the next move
        self.last_stamp = stamp
        self.last_cadence = cadence

        return

def main():
    options = parse_args()

    tree = ET.parse("/dev/stdin")

    # constant - compute just once (crank length is the radius, so 2πr!)
    crank_circum = 2 * options.crank_length * 0.000001 * math.pi
    dist_per_rev = crank_circum * options.gain_ratio

    course = Course(options.course, dist_per_rev, options.verbose)

    for trkpt in tree.iterfind(".//{*}trkpt"):
        course.update_lat_long(trkpt)

    if options.verbose:
        print(f"Total distance: {course.total:.2f}km",
              file=sys.stderr)

    print("""<?xml version="1.0" encoding="UTF-8"?>""")
    ET.register_namespace("gpxtpx", "http://www.garmin.com/xmlschemas/TrackPointExtension/v1")
    ET.register_namespace("", "http://www.topografix.com/GPX/1/1")
    tree.write(sys.stdout, encoding="unicode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
