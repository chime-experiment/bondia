"""
Utility functions to look up transit, rise and set times of sources.

This will hopefully be part of caput soon, so we can remove this file.
"""

import numpy as np

from scipy.optimize import brentq

from caput import time as ctime

_timescale = ctime.skyfield_wrapper.timescale


def source_ha(obs, source, t):
    time = _timescale.tt_jd(t)
    lst = time.gast * 15 + obs.positives[-1].longitude.degrees
    ra = obs.at(time).observe(source).radec(epoch=time)[0]._degrees

    return (((lst - ra) + 180) % 360) - 180


def source_alt(obs, source, t):
    from skyfield.positionlib import _to_altaz

    time = _timescale.tt_jd(t)
    pos = obs.at(time).observe(source)
    alt = _to_altaz(pos.position.au, pos.observer_data, None, None)[0].degrees

    return alt


def _search_interval(t0, t1=None, step=0.2):
    t0 = ctime.ensure_unix(t0)
    t1 = ctime.ensure_unix(t1) if t1 is not None else t0 + 24 * 3600.0
    t0, t1 = [ctime.unix_to_skyfield_time(t) for t in [t0, t1]]

    t0jd = t0.tt
    t1jd = t1.tt

    # Form a grid of points to find intervals to search over
    tx = np.linspace(int(t0jd), int(t1jd), int(np.ceil((t1jd - t0jd) / step)))

    return tx


def source_transit(obs, source, t0, t1=None, step=0.2, lower=False, return_dec=False):
    """Find the transit times of the given source in an interval.

    Parameters
    ----------
    obs : skyfield observer
        Location of observer.
    source : skyfield source
        The source we are calculating the transit of.
    t0 : float unix time, or datetime
        The start time to search for. Any type that be converted to a UNIX time by
        caput.
    t1 : float unix time, or datetime, optional
        The end time of the search interval. If not set, this is 1 day after the start
        time `t0`.
    step : float
        The initial search step in days. This is used to find the approximate location
        between transits, and should be set to something less than the spacing between
        transits.
    lower : bool, optional
        By default this only returns the upper (regular) transit. This will cause lower
        transits to be returned instead.
    return_dec : bool, optional
        If set, also return the declination of the source at transit.

    Returns
    -------
    times : np.ndarray
        UNIX times of transits.
    dec : np.ndarray
        Only returned if `return_dec` is set. Declination of source at transit.
    """

    # The function to find routes for. For the upper transit we just search for HA=0,
    # for the lower transit we need to rotate the 180 -> -180 transition to be at 0.
    def f(t):
        ha = source_ha(obs, source, t)
        return ha if not lower else (ha % 360.0) - 180.0

    # Calculate the HA at the initial search points
    tx = _search_interval(t0, t1, step)
    h = f(tx)

    transits = []

    # Search through intervals
    for ta, tb, ha, hb in zip(tx[:-1], tx[1:], h[:-1], h[1:]):

        # Entries are the same sign, so there is no solution in between.
        # Here we need to deal with the case where one edge might be an exact transit,
        # hence the strictly greater than 0.0
        if ha * hb > 0.0:
            continue

        # Skip lower transit (or the upper transit if lower=True)
        if ha > hb:
            continue

        root = brentq(f, ta, tb, xtol=1e-6)

        transits.append(root)

    if not transits:
        return (np.array([]), np.array([])) if return_dec else np.array([])

    # Convert into UNIX times
    t_sf = _timescale.tt_jd(np.array(transits))
    t_unix = ctime.ensure_unix(t_sf.utc_datetime())

    if return_dec:
        dec = obs.at(t_sf).observe(source).cirs_radec(epoch=t_sf)[1].degrees
        return t_unix, dec
    else:
        return t_unix


def source_rise_set(obs, source, t0, t1=None, step=0.2, diameter=0.0):
    """Find all times a sources rises or sets in an interval.

    Parameters
    ----------
    obs : skyfield observer
        Location of observer.
    source : skyfield source
        The source we are calculating the rising and setting of.
    t0 : float unix time, or datetime
        The start time to search for. Any type that be converted to a UNIX time by
        caput.
    t1 : float unix time, or datetime, optional
        The end time of the search interval. If not set, this is 1 day after the start
        time `t0`.
    step : float
        The initial search step in days. This is used to find the approximate location
        between transits, and should be set to something less than the spacing between
        transits.
    diameter : float
        The size of the source in degrees. Use this to ensure the whole source is below
        the horizon. Also, if the local horizon is higher (i.e. mountains), this can be
        set to a negative value to account for this.

    Returns
    -------
    times : np.ndarray
        Source rise/set times as UNIX epoch times.
    rising : np.ndarray
        Boolean array of whether the time corresponds to a rising (True) or
        setting (False).
    """

    # The function to find roots for. This is just the altitude of the source with an
    # offset for it's finite size
    def f(t):
        return source_alt(obs, source, t) + diameter / 2

    # Calculate the altitude of the source edge at on the source interval
    tx = _search_interval(t0, t1, step)
    alt = f(tx)

    times = []
    rising = []

    # Search over intervals
    for ta, tb, aa, ab in zip(tx[:-1], tx[1:], alt[:-1], alt[1:]):

        # Entries are the same sign, so no solution in between
        if aa * ab > 0.0:
            continue

        root = brentq(f, ta, tb, xtol=1e-6)

        # Save time, and if the source was rising or not (i.e. altitude is increasing)
        times.append(root)
        rising.append(ab > aa)

    if not times:
        return np.array([], dtype=np.float64), np.array([], dtype=np.bool)

    t_unix = ctime.ensure_unix(_timescale.tt_jd(np.array(times)).utc_datetime())

    return t_unix, np.array(rising)
