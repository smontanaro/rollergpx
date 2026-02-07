"simple(minded) test for the gpx to latlong script"

import xml.etree.ElementTree as ET

from haversine import haversine
from rollergpx.gpxtolatlong import process_tree
from tests import close, TSTGPX


def test_process():
    with open(TSTGPX, encoding="utf-8") as infile:
        tree = ET.parse(infile)
        records = process_tree(tree)
        pt0 = (records[-2]["lat"], records[-2]["long"])
        pt1 = (records[-1]["lat"], records[-1]["long"])
        dist = haversine(pt0, pt1)
        assert records[0] == {"lat": 42.0404620,
                              "long": -87.6936040,
                              "dist": 0.0,}
        assert close(records[-1]["dist"], dist)
