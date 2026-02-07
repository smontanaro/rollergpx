"unit tests for rollergpx"

# test_rollergpx.py
import datetime
import xml.etree.ElementTree as ET

import pytest

from rollergpx.rollergpx import (
    Course, CadenceDetail, PositionDetail, DEFAULT_COURSE
)
from tests import close, TSTGPX, EPOCH


class TestComputeDistance:
    """Test the distance computation logic."""

    def test_first_observation_returns_zero(self):
        course = Course(DEFAULT_COURSE, dist_per_rev=0.001)
        detail = CadenceDetail(cadence=60, stamp=datetime.datetime(2025, 1, 1, 12, 0, 0))
        assert course.compute_distance(detail) == 0.0

    def test_constant_cadence_one_minute(self):
        """60 RPM for 1 minute = 60 revolutions."""
        course = Course(DEFAULT_COURSE, dist_per_rev=0.001)  # 1 meter per rev
        t0 = datetime.datetime(2025, 1, 1, 12, 0, 0)
        t1 = datetime.datetime(2025, 1, 1, 12, 1, 0)

        course.compute_distance(CadenceDetail(cadence=60, stamp=t0))
        dist = course.compute_distance(CadenceDetail(cadence=60, stamp=t1))

        assert close(dist, 0.060)      # 60 revs * 0.001 km/rev

    def test_varying_cadence_uses_mean(self):
        """Cadence changing from 60 to 80 should use mean of 70."""
        course = Course(DEFAULT_COURSE, dist_per_rev=0.001)
        t0 = datetime.datetime(2025, 1, 1, 12, 0, 0)
        t1 = datetime.datetime(2025, 1, 1, 12, 1, 0)

        course.compute_distance(CadenceDetail(cadence=60, stamp=t0))
        dist = course.compute_distance(CadenceDetail(cadence=80, stamp=t1))

        assert close(dist, 0.070)       # 70 revs * 0.001 km/rev

    def test_zero_cadence(self):
        """Zero cadence for the interval means no distance."""
        course = Course(DEFAULT_COURSE, dist_per_rev=0.001)
        t0 = datetime.datetime(2025, 1, 1, 12, 0, 0)
        t1 = datetime.datetime(2025, 1, 1, 12, 1, 0)

        course.compute_distance(CadenceDetail(cadence=0, stamp=t0))
        dist = course.compute_distance(CadenceDetail(cadence=0, stamp=t1))

        assert dist == 0.0

    def test_missing_timestamp(self):
        course = Course(DEFAULT_COURSE, dist_per_rev=0.001)
        with open(TSTGPX, encoding="utf-8") as infile:
            tree = ET.parse(infile)
            for trkpt in tree.iterfind(".//{*}trkpt"):
                for tag in trkpt.iterfind(".//{*}time"):
                    trkpt.remove(tag)
                    detail = course.extract_cadence(trkpt)
                    assert detail.stamp == EPOCH


class TestMove:
    """Test course traversal."""

    def make_simple_course(self):
        """A simple 3-point course, each segment ~1.11 km apart."""
        points = [
            PositionDetail(lat=0.0, long=0.0),
            PositionDetail(lat=0.01, long=0.0),   # ~1.11 km north
            PositionDetail(lat=0.02, long=0.0),   # ~1.11 km further north
        ]
        return Course(points, dist_per_rev=0.001)

    def test_move_within_segment(self):
        course = self.make_simple_course()
        course.move(0.5)  # move 0.5 km
        # Should be partway to first waypoint
        assert course.next == 1
        assert course.current.lat > 0.0
        assert course.current.lat < 0.01

    def test_move_past_waypoint(self):
        course = self.make_simple_course()
        course.move(1.5)  # more than first segment
        # Should have passed first waypoint
        assert course.next == 2
        assert course.current.lat > 0.01

    def test_zero_distance_move(self):
        course = self.make_simple_course()
        course.move(0.0)  # more than first segment
        assert course.next == 1
        assert course.current.lat == 0.0

    def test_move_wraps_on_loop_course(self):
        """A loop course (start ≈ end) should wrap around."""
        points = [
            PositionDetail(lat=0.0, long=0.0),
            PositionDetail(lat=0.005, long=0.0),
            PositionDetail(lat=0.005, long=0.005),
            PositionDetail(lat=0.0, long=0.005),
            PositionDetail(lat=0.0, long=0.0),  # back to start
        ]
        course = Course(points, dist_per_rev=0.001)
        assert not course.out_and_back  # it's a loop

        # Move farther than total course length
        for _ in range(50):
            course.move(0.5)

        # Should have wrapped multiple times
        assert course.nmoves == 50


class TestOutAndBack:
    """test out-and-back course"""

    def test_out_and_back_detected(self):
        """Course with distant endpoints is out-and-back."""
        points = [
            PositionDetail(lat=0.0, long=0.0),
            PositionDetail(lat=0.02, long=0.0),  # ~2.2 km away
        ]
        course = Course(points, dist_per_rev=0.001)
        assert course.out_and_back

    def test_loop_not_out_and_back(self):
        """Course returning to start is not out-and-back."""
        points = [
            PositionDetail(lat=0.0, long=0.0),
            PositionDetail(lat=0.01, long=0.0),
            PositionDetail(lat=0.0, long=0.0),
        ]
        course = Course(points, dist_per_rev=0.001)
        assert not course.out_and_back


class TestFromCsv:
    """test csv file reading"""
    def test_empty_path_uses_default(self):
        course = Course.from_csv("", dist_per_rev=0.001)
        assert course.points == DEFAULT_COURSE

    def test_loads_csv_file(self, tmp_path):
        csv_file = tmp_path / "course.csv"
        csv_file.write_text("lat,long\n42.0,-87.0\n42.01,-87.0\n")

        course = Course.from_csv(str(csv_file), dist_per_rev=0.001)

        assert len(course.points) == 2
        assert course.points[0].lat == 42.0
        assert course.points[1].lat == 42.01

    def test_rejects_single_point_course(self, tmp_path):
        csv_file = tmp_path / "course.csv"
        csv_file.write_text("lat,long\n42.0,-87.0\n")

        with pytest.raises(AssertionError):
            Course.from_csv(str(csv_file), dist_per_rev=0.001)
