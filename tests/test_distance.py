import datetime

from rollergpx.rollergpx import Course, DEFAULT_COURSE, CadenceDetail

def test_distance_at_constant_cadence():
    course = Course(DEFAULT_COURSE, dist_per_rev=0.001)
    # 60 RPM for exactly 1 minute should give 60 revolutions
    t0 = datetime.datetime(2025, 1, 1, 12, 0, 0)
    t1 = datetime.datetime(2025, 1, 1, 12, 1, 0)
    course.compute_distance(CadenceDetail(stamp=t0, cadence=60))  # initialize
    dist = course.compute_distance(CadenceDetail(stamp=t1, cadence=60))
    assert abs(dist - 0.06) < 1e-9  # 60 revs * 0.001 km/rev
