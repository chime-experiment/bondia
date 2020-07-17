from ch_util.ephemeris import csd_to_unix, unix_to_csd
import datetime
import time


class Day:
    def __init__(self, lsd: int, date: datetime.date):
        self._lsd = lsd
        self._date = date

    @classmethod
    def from_lsd(cls, lsd: int):
        unix = csd_to_unix(lsd)
        lsd = int(lsd)
        date = datetime.date.fromtimestamp(unix)
        day = cls(lsd, date)
        return day

    @classmethod
    def from_date(cls, date: datetime.date):
        unix = time.mktime(date.timetuple())
        lsd = int(unix_to_csd(unix))
        day = cls(lsd, date)
        return day

    @property
    def lsd(self):
        return self._lsd

    @property
    def date(self):
        return self._date

    def __repr__(self):
        return f"{self.lsd} [{self.date.isoformat()} (PT)]"

    def closest_after(self, days):
        for day in reversed(days):
            if self._lsd >= day.lsd:
                return day
        return self.closest_before(days)

    def closest_before(self, days):
        for day in days:
            if self._lsd <= day.lsd:
                return day
        return self.closest_after(days)
