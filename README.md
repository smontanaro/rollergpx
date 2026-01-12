# rollergpx

The `rollergpx` program adds distance info to a GPX file generated
while riding rollers. This requires cadence info in the input GPX
file. In my sheltered existence, I have an old Wahoo Bolt v1 and a
Wahoo Tickr X which measures both heart rate and cadence. I'm certain
there are more sophisticated tools out there.

The `gpxtolatlong` program takes a GPX file and spits out a CSV file
containing the lat/long details from the file and computed distance in
km between the individual points. The output CSV file can be used as
the `--course` option to `rollergpx`. The `data` directory contains a
suitable file converted from a RideWithGPS route which describes the
Ed Rudolph Velodrome in Northbrook, IL.
