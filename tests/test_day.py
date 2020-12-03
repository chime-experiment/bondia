import datetime
import os

from caput import time as ctime

from bondia.util.day import Day


# Download the required Skyfield files from a mirror on a CHIME server.
#
# The upstream servers for the timescale and ephemeris data can be
# flaky. Use this to ensure a copy will be downloaded at the risk of it
# being potentially out of date. This is useful for things like CI
# servers, but otherwise letting Skyfield do it's downloading is a
# better idea.
#
mirror_url = "https://bao.chimenet.ca/skyfield/"

files = [
    "Leap_Second.dat",
    "finals2000A.all",
    "de421.bsp",
    "deltat.data",
    "deltat.preds",
]

loader = ctime.skyfield_wrapper.load
for file in files:
    if not os.path.exists(loader.path_to(file)):
        loader.download(mirror_url + file)


def test_from_lsd():
    day = Day.from_lsd(2401)
    assert day.date == datetime.date(year=2020, month=6, day=5)
    assert day.__repr__() == "2401 [2020-06-05 (PT)]"


def test_from_date():
    day = Day.from_date(datetime.date(year=2017, month=9, day=13))
    assert day.__repr__() == "1401 [2017-09-13 (PT)]"
    assert day.lsd == 1401
