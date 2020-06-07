import datetime

from bondia.utils.day import Day


def test_from_lsd():
    day = Day.from_lsd(2401)
    assert day.date == datetime.date(year=2020, month=6, day=5)
    assert day.__repr__() == "2020-06-05 (PT)"


def test_from_date():
    day = Day.from_date(datetime.date(year=2017, month=9, day=13))
    assert day.__repr__() == "2017-09-13 (PT)"
    assert day.lsd == 1401
