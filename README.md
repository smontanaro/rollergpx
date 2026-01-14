# rollergpx

The `rollergpx` program adds distance info to a GPX file generated while
riding rollers. This requires cadence info in the input GPX file.

The `gpxtolatlong` program takes a GPX file and spits out a CSV file
containing the lat/long details from the file and computed distance in km
between the individual points. The output CSV file can be used as the
`--course` option to `rollergpx`. The `data` directory contains a suitable
file converted from a RideWithGPS route which describes the Ed Rudolph
Velodrome in Northbrook, IL.

## rollergpx

Lots of people have smart trainers these days. I only have rollers, but in
the presence of something which can track cadence and knowledge of my
gearing, I can calculate the distance ridden during a roller session. My
setup happens to be a Wahoo Elemnt Bolt v1 and a Wahoo Tickr X heart rate
monitor (which also measures cadence), but I suppose anything which records
your time and cadence will suffice.

To make this work, you need gearing details. I use Sheldon Brown's gain ratio
and crank length to translate cadence into linear velocity:

https://www.sheldonbrown.com/gain.html

Inputs to that calculation are the crank arm length, tire circumference, and
chainring and sprocket tooth counts. Note that this currentyly only works if
you don't shift gears!!! That works for me because I can rarely tolerate the
boredom of riding in my basement for more than 30 minutes or so. My goal
here is simply to have something plausible to upload to Strava so my January
and February mileages don't look so bad. YMMV.

## TODO

- Allow gear changes using the "lap" feature on my Wahoo (maybe)
- Add some tests
    - In particular, I need to make sure I have the crossover from end to
      start done right. It's quite possible I'm losing or adding some
      distance.
- Namespace names on output are incorrect. I still have to zap "ns0"
  references.
