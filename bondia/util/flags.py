import logging
import threading
import time

from functools import lru_cache
from typing import List

from chimedb import dataflag as df
from chimedb.core import connect as chimedbconnect

logger = logging.getLogger(__name__)

# Keep track of the cache age (thread-safe).
cache_ts_lock = threading.Lock()
cache_ts = 0


def get_flags_cached(flag_types: List[str], cache_reset_time: int = -1):
    """
    Get CHIME data flags from the database.

    This function is cached for performance, but the cache can get reset periodically.

    Parameters
    ----------
    flag_types: List[str]
        Types of flags to request.
    cache_reset_time: int
        Seconds after which to reset the cache to get fresh flags.

    Returns
    -------
    List[Tuple[str, float, float]]
        List of flags: type name with start and end time.
    """
    # Clear the cache and get fresh flags once in a while
    global cache_ts
    with cache_ts_lock:
        now = time.time()
        if cache_reset_time != -1 and now - cache_ts > cache_reset_time:
            logger.debug(f"Resetting data flag cache...")
            get_one_flag_type.cache_clear()
            cache_ts = now

    flags = []
    for ft in flag_types:
        flags += get_one_flag_type(ft)
    logger.debug(f"Flag cache stats: {get_one_flag_type.cache_info()}")
    return flags


@lru_cache(maxsize=None, typed=True)
def get_one_flag_type(flag_type: str):
    """
    Get data flags of one type from the CHIME db.

    This function is cached for performance.

    Parameters
    ----------
    flag_type: str
        Name of the requested flag type.

    Returns
    -------
    List[Tuple[str, float, float]]
        List of flags: type name with start and end time.
    """
    chimedbconnect()
    flags = (
        df.DataFlag.select()
        .join(df.DataFlagType)
        .where(df.DataFlagType.name << [flag_type])
    )
    return [(f.type.name, f.start_time, f.finish_time) for f in flags]
