#!/bin/bash

. $(VENVDIR)/bin/activate

if [ "x$PYTHONPATH" = "x" ] ; then
    export PYTHONPATH=$(pwd)
fi

if [ "x${PYTHON}" = "x" ] ; then
    PYTHON=python
fi

echo "+++++++++++++++++++++++++++"
type ${PYTHON}
${PYTHON} --version
echo "+++++++++++++++++++++++++++"

TMPGPX=$(mktemp XXXXXX.gpx)
TMPCSV=$(mktemp XXXXXX.csv)

trap "rm -f ${TMPGPX} ${TMPCSV}" EXIT

runcov () {
    echo "run: $1" 1>&2
    ${PYTHON} "$@"
}

VERBOSE=
export DOCOVER=
while getopts 'vhc' OPTION; do
    case "$OPTION" in
        c)
	    export DOCOVER=true
            RUNCOV='coverage run -a --rcfile=.coveragerc'
            runcov () {
                echo "cover: $1" 1>&2
                ${RUNCOV} "$@"
            }
            ;;
        v)
            VERBOSE=-v
            ;;
        h)
            echo "usage: $0 [ -v ]" 1>&2
            exit 0
            ;;
    esac
done
shift "$(($OPTIND -1))"

# Run our official unit tests
runcov $(which pytest) --cov=rollergpx $VERBOSE
PYT=$?

runcov rollergpx/rollergpx.py -v -g 5.4 < scripts/short.gpx > ${TMPGPX}
LON=$(grep -E 'lon=' ${TMPGPX} | awk '{print $3}' | sort | uniq -c)
if [ "${LON}" != '  56 lon="-87.65">' ] ; then
    echo "wrong output count or wrong longitude: ${LON}" 1>&2
    exit 1
fi
runcov rollergpx/rollergpx.py -g 5.4 --course=rollergpx/data/velodrome.csv < scripts/short.gpx > ${TMPGPX}
LON=$(grep -E 'lon=' ${TMPGPX} | tail -1)
if [ "${LON}" != '   <trkpt lat="42.12332125487012" lon="-87.81742459719388">' ] ; then
    echo "wrong ending longitude: ${LON}" 1>&2
    exit 1
fi
COUNT=$(grep -E 'lon=' ${TMPGPX} | wc -l)
if [ "${COUNT}" -ne 56 ] ; then
    echo "wrong <trkpt> count: ${COUNT}" 1>&2
    exit 1
fi

runcov rollergpx/gpxtolatlong.py < rollergpx/data/velodrome.gpx > ${TMPCSV}
if ! cmp -s ${TMPCSV} rollergpx/data/velodrome.csv ; then
    echo "gpxtolatlong mismatch" 1>&2
    exit 1
fi

rm -rf htmlcov
coverage html
