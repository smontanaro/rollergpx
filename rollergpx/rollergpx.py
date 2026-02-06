#!/usr/bin/env python

"""
Read a GPX file and produce a new one with details from a cadence-enhanced
roller ride.

See README.md for more details.
"""

import argparse
import csv
from dataclasses import dataclass
import datetime
import logging
import math
import sys
import xml.etree.ElementTree as ET

import dateutil.parser
from haversine import haversine

EPOCH = datetime.datetime.fromtimestamp(0)

LOGGER = logging.getLogger(__name__)

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


@dataclass
class CadenceDetail:
    "Last cadence & time measurement dredged from the GPX file"
    cadence: int
    stamp: datetime.datetime


@dataclass
class PositionDetail:
    "Current position on the course and index of next position"
    # current position along the course (might be betweeen two fixed
    # points)
    lat: float
    long: float
    def as_tuple(self):
        return (self.lat, self.long)
    def as_str_tuple(self):
        return (str(self.lat), str(self.long))

# Default course in Lake Michigan to "ride" if the user doesn't specify one.
DEFAULT_COURSE = [
    PositionDetail(lat=42.04, long=-87.65),
    PositionDetail(lat=42.06, long=-87.65),
    ]


class Course:
    """Hold lat/long details of a course and progress through it.

    * course_csv - CSV file containing lat/long details for a course you will "ride"
    * dist_per_rev - Distance (in km) per revolution of the cranks

    Normal usage is to create a Course object, then repeatedly call its
    update_lat_long with a series of <trkpt> elements from a GPX file, e.g.:

    tree = ET.parse("/some/gpx/file")
    for trkpt in tree.iterfind(".//{*}trkpt"):
        course.update_lat_long(trkpt)

    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, course, dist_per_rev):
        self.points = course
        self.last = CadenceDetail(cadence=0, stamp=EPOCH)
        self.dist_per_rev = dist_per_rev
        self.nmoves = 0
        self.total = 0.0
        self.current = course[0]

        # index of next fixed point along the course
        self.next = 1

        # A course is deemed (somewhat arbitrarily) "out and back" if the
        # distance between first and last points is at least one kilometer.
        self.out_and_back = haversine(self.points[0].as_tuple(),
            self.points[-1].as_tuple()) >= 1.0

    def move(self, distance):
        "Move along the course by the given distance (km)."
        # add distance to the position, following the course, returning the
        # new position
        self.nmoves += 1
        if distance:
            while distance:
                pt1 = self.current
                pt2 = self.points[self.next]
                next_waypoint = haversine(pt1.as_tuple(), pt2.as_tuple())
                if next_waypoint <= distance:
                    # remaining distance at least reaches pt2. Adjust and
                    # continue.
                    distance -= next_waypoint
                    self.current = pt2
                    self.next += 1
                    if self.next == len(self.points):
                        LOGGER.debug("end of course, next==%d, moves=%d, distance=%.2fkm",
                                     self.next, self.nmoves, self.total)
                        if self.out_and_back:
                            # flip and go the other way
                            LOGGER.debug("out and back")
                            self.points = self.points[::-1]
                        self.next = 0
                else:
                    # distance from pt1 to pt2 is greater than the remaining
                    # distance. Adjust our current position to that fractional
                    # distance, but don't advance the next fixed point index.
                    frac = distance / next_waypoint
                    assert 0.0 < frac <= 1.0
                    distance = 0
                    clat = pt1.lat + (pt2.lat - pt1.lat) * frac
                    clon = pt1.long + (pt2.long - pt1.long) * frac
                    self.current = PositionDetail(lat=clat, long=clon)

        return self.current

    def extract_cadence(self, trkpt):
        cadence = 0
        cadstr = self.child_tag_text(trkpt, "cad").strip()
        if cadstr:
            cadence = int(cadstr)
        dt = EPOCH
        dtstr = self.child_tag_text(trkpt, "time").strip()
        if dtstr:
            dt = dateutil.parser.parse(dtstr)
        return CadenceDetail(cadence=cadence, stamp=dt)

    def child_tag_text(self, trkpt, tag):
        for child in trkpt.iterfind(f".//{{*}}{tag}"):
            return child.text
        return ""

    def compute_distance(self, detail):
        """given a timestamp and cadence, return distance in km."""
        if self.last.stamp == EPOCH:
            distance = 0.0
        else:
            # units = minutes
            delta_t = (detail.stamp - self.last.stamp).total_seconds() / 60
            # units == rev per minute
            mean_cadence = (detail.cadence + self.last.cadence) / 2
            # units = revolutions
            revs = mean_cadence * delta_t
            distance = revs * self.dist_per_rev
        self.last = detail
        return distance

    def update_lat_long(self, trkpt):
        """Extract data from GPX element, compute, and update it."""
        detail = self.extract_cadence(trkpt)
        distance = self.compute_distance(detail)

        if distance == 0.0 and self.nmoves == 0:
            (lat, long) = self.points[0].as_str_tuple()
        else:
            self.total += distance
            (lat, long) = self.move(distance).as_str_tuple()

        trkpt.attrib["lat"] = lat
        trkpt.attrib["lon"] = long

    @classmethod
    def from_csv(cls, course_csv, dist_per_rev):
        if not course_csv:
            course = DEFAULT_COURSE
        else:
            with open(course_csv, encoding="utf-8") as course:
                reader = csv.DictReader(course)
                course = []
                for coord in reader:
                    # convert lat/long to floats
                    point = PositionDetail(lat=float(coord["lat"]),
                        long=float(coord["long"]))
                    course.append(point)
        assert len(course) >= 2, "defined course must have at least two points"
        return cls(course, dist_per_rev)

def main():
    options = parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)

    tree = ET.parse("/dev/stdin")

    # constant - compute just once (crank length is the radius, so 2πr!)
    crank_circum = 2 * options.crank_length * 0.000001 * math.pi
    dist_per_rev = crank_circum * options.gain_ratio

    course = Course.from_csv(options.course, dist_per_rev)

    for trkpt in tree.iterfind(".//{*}trkpt"):
        course.update_lat_long(trkpt)

    LOGGER.debug("Total distance: %.2fkm", course.total)

    print("""<?xml version="1.0" encoding="UTF-8"?>""")
    ET.register_namespace("gpxtpx", "http://www.garmin.com/xmlschemas/TrackPointExtension/v1")
    ET.register_namespace("", "http://www.topografix.com/GPX/1/1")
    tree.write(sys.stdout, encoding="unicode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
