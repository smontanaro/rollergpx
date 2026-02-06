#!/bin/bash

if [ "x$PYTHONPATH" = "x" ] ; then
    export PYTHONPATH=$(pwd)/rollergpx
fi

if [ "x${PYTHON}" = "x" ] ; then
    PYTHON=python
fi

echo "+++++++++++++++++++++++++++"
type ${PYTHON}
${PYTHON} --version
echo "+++++++++++++++++++++++++++"

# Mac requires gsleep for subsecond sleeps, Linux doesn't.
if [ "x$(which gsleep | egrep -v 'not found')" = "x" ] ; then
    SLEEP=sleep
else
    SLEEP=gsleep
fi

# Mac requires gdate for %N
if [ "x$(which gdate | egrep -v 'not found')" = "x" ] ; then
    DATE=date
else
    DATE=gdate
fi

TMPGPX=$(mktemp XXXXXX.gpx)

trap "rm -f ${TMPGPX}" EXIT

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

coverage run -a rollergpx/rollergpx.py -v -g 5.4 < scripts/short.gpx > ${TMPGPX}
LON=$(grep -E 'lon=' ${TMPGPX} | awk '{print $3}' | sort | uniq -c)
if [ "${LON}" != '  56 lon="-87.65">' ] ; then
    echo "wrong output count or wrong longitude: ${LON}" 1>&2
    exit 1
fi
coverage run -a rollergpx/rollergpx.py -g 5.4 --course=rollergpx/data/velodrome.csv < scripts/short.gpx > ${TMPGPX}
LON=$(grep -E 'lon=' ${TMPGPX} | tail -1)
if [ "${LON}" != '   <trkpt lat="42.12338838861973" lon="-87.81744031363048">' ] ; then
    echo "wrong ending longitude: ${LON}" 1>&2
    exit 1
fi
COUNT=$(grep -E 'lon=' ${TMPGPX} | wc -l)
if [ "${COUNT}" -ne 56 ] ; then
    echo "wrong <trkpt> count: ${COUNT}" 1>&2
    exit 1
fi

rm -rf htmlcov
coverage html
