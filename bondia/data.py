import datetime
import time
import logging
import re
import bisect
import pathlib
from collections import OrderedDict
# import signal
# import sys
# import threading
# from dataclasses import dataclass
import functools
from typing import Type, Dict, Union

from ch_util.ephemeris import csd_to_unix, unix_to_csd, unix_to_datetime
from caput.config import Property, Reader
from ch_pipeline.core.containers import RingMap
from draco.core.containers import DelaySpectrum, RFIMask, SystemSensitivity

logger = logging.getLogger(__name__)

LSD_TAG_PATTERN = re.compile(r"^\d+$")

FILE_TYPES = {
    "delayspectrum": "delayspectrum_lsd_*.h5",
    "delayspectrum_hpf": "delayspectrum_hpf_lsd_*.h5",
    "ringmap": "ringmap_validation_freqs_lsd_*.h5",
    "ringmap_intercyl": "ringmap_intercyl_validation_freqs_lsd_*.h5",
    "sensitivity": "sensitivity_validation_lsd_*.h5",
    "rfi": "rfi_mask_lsd_*.h5",
}

CONTAINER_TYPES: Dict[str, Type[Union[DelaySpectrum, RingMap]]] = {
    "delayspectrum": DelaySpectrum,
    "delayspectrum_hpf": DelaySpectrum,
    "ringmap": RingMap,
    "ringmap_intercyl": RingMap,
    "sensitivity": SystemSensitivity,
    "rfi": RFIMask,
}


class DataLoader(Reader):
    path = Property(proptype=pathlib.Path)
    interval = Property(proptype=int, default=600)
    max_days_in_memory = Property(proptype=int, default=10)

    # Set up periodic data file indexing
    # self._periodic_indexer = None
    # self._indexing_done = threading.Event()
    # self._exit_event = threading.Event()

    # def stop_indexer(signum, frame):
    #     self._exit_event.set()
    #     if self._periodic_indexer:
    #         self._periodic_indexer.join()
    #     sys.exit()

    # signal.signal(signal.SIGINT, stop_indexer)

    # def _periodic_index(self):
    #     """Periodically index new files."""
    #     if not self._exit_event.is_set():
    #         if not self.index_files(self.path):
    #             logger.debug(f"No new files found. Indexing again in {self.interval}s")
    #         self._indexing_done.set()
    #         timer = threading.Timer(self.interval, self._periodic_index)
    #         timer.start()

    def _finalise_config(self):
        """Index files after caput config reader is done."""
        self.index = DataIndex(self.path, self.interval)
        self._perm_cache = {}
        self.cache = LRUCache(self.max_days_in_memory)
        # if self.path:
        #     # Start periodic indexing thread and wait until it ran once.
        #     self._periodic_indexer = threading.Thread(
        #         target=self._periodic_index, daemon=True
        #     )
        #     self._periodic_indexer.start()
        #     self._indexing_done.wait()
        # else:
        #     logger.debug("No data path in config, skipping...")

    # def lsds(self, revision: str):
    #     return sorted(self.index[revision].keys())

    # def days(self, revision: str):
    #     # return [day.lsd for day in self.days(revision)]
    #     return [self.index[revision][lsd].day for lsd in self.lsds(revision)]

    # @property
    # def revisions(self):
    #     return sorted(self.index.keys())

    # @property
    # def latest_revision(self):
    #     """
    #     Get latest revision.

    #     Note
    #     ----
    #     This assumes the revisions being numbered like "rev_00", "rev_01", "rev_17", where their
    #     order is the same as the revision strings sorted by python string comparison.
    #     """
    #     return self.revisions[-1]

    def _load_lsd_file(self, revision: str, lsd: str, file_type: str):
        """Load the data of one day from disk."""
        id = revision+lsd
        lsd_files = self.cache.get(id, {})

        if lsd_files:
            # There is already an entry for this rev:lsd combo
            file = lsd_files.get(file_type, None)

            if file is not None:
                # This file is already cached
                return file

        # Get the indexed file path for this specific file
        f = self.index[revision][lsd][file_type]

        if f is None:
            logger.warn(f"No {file_type} files for {revision}, {lsd} available.")
            return

        logger.debug(f"Loading {file_type} file for {revision}, {lsd}...")

        # Load the file
        try:
            file = self._load_file_from_path(f, CONTAINER_TYPES[file_type])
        except Exception:
            return None

        # Add the newly loaded file to the cache and push
        lsd_files[file_type] = file
        self.cache.put(id, lsd_files)

        return file

    def _load_file_from_path(self, path: pathlib.Path, container, keep: bool = False):
        """Load a file from a path into a container."""
        id = str(path)

        file = self._perm_cache.get(id, None)

        if file is None:
            logger.debug(f"Loading file from '{path}'...")
            file = container.from_file(path)

            if keep:
                self._perm_cache[id] = file

        return file


class LRUCache:
    def __init__(self, size: int):
        self._size = size
        self._cache = OrderedDict()

    def get(self, key: str, default = None):
        try:
            value = self._cache.pop(key)
        except KeyError:
            return default
        # Put item back at front of queue
        self._cache[key] = value

        return value

    def put(self, key: str, value):
        try:
            # Remove this key if it already exists
            self._cache.pop(key)
        except KeyError:
            # Remove least recently used item if needed
            if len(self._cache) >= self._size:
                self._cache.popitem(last=False)

        self._cache[key] = value


class DataIndex:
    def __init__(self, directories, interval: int = 0, run_now: bool = False):
        if isinstance(directories, (list, set, tuple)):
            self.directories = [pathlib.Path(i) for i in directories]
        else:
            self.directories = [pathlib.Path(directories)]

        self._index = {}
        # self._sorted_keys = []

        self._auto_refresh(interval, run_now)

    def __getitem__(self, key):
        return self._index[key]

    def keys(self):
        return self._index.keys()

    def values(self):
        return self._index.values()

    def items(self):
        return self._index.items()

    def _auto_reindex(self, interval: int, run_now: bool):
        if interval == 0:
            return
        ...

    def _reindex(self):
        """(Re)index data files."""

        for dir in self.directories:
            # find directories that match the revision pattern
            # In theory the .glob should only return dirs since we use the
            # / in the pattern
            rev_directories = ((x.name, x) for x in dir.glob("rev_*/") if x.is_dir())

            for rev, rev_path in rev_directories:

                if rev not in self._index:
                    self._index[rev] = {}

                existing_lsds = set(self._index[rev].keys())

                lsd_directories = (
                    (x.name, x)
                    for x in rev_path.glob("*/")
                    if (re.search(LSD_TAG_PATTERN, x) and x.is_dir())
                )

                for lsd, lsd_path in lsd_directories:
                    # Only updates if lsd not in rev dict
                    self._index[rev].setdefault(lsd, DataIndexDay(lsd, rev, lsd_path))
                    # Update files available for lsd
                    self._index[rev][lsd]._reindex()

                new_lsds = existing_lsds ^ self._index[rev].keys()
                if new_lsds:
                    logger.info(f"Found new {rev} data for day(s) {new_lsds}.")


class DataIndexDay:
    def __init__(self, lsd: str, rev: str, path: str):
        self.date = unix_to_datetime(csd_to_unix(str(lsd)))
        self.lsd = int(lsd)
        self.start_time = csd_to_unix(self.lsd)
        self.end_time = csd_to_unix(self.lsd + 1)

        self._rev = rev
        self._path = path
        self._index = dict.fromkeys(FILE_TYPES.keys())
        self._id = self.__repr__()

    @staticmethod
    def lsd_from_date(date: datetime.date):
        unix = time.mktime(date.timetuple())

        return int(unix_to_csd(unix))

    def __getitem__(self, key: str):
        return self._index[key]

    @functools.cache
    def __repr__(self):
        return f"{self.lsd} [{self.date.isoformat()} (PT)]"

    def _reindex(self):

        for file_type, file_type_glob in FILE_TYPES.items():

            files_matched = self._path.glob(file_type_glob)

            if len(files_matched) != 1:
                logger.warn(
                    f"Found {len(files_matched)} {file_type} files in {self._path} (Expected 1)."
                )
                continue

            logger.debug(f"Found {self._rev} file for lsd {self.lsd}: {file}")

            file = files_matched[0]
            lsd = int(file.stem[-4:])

            if lsd != self.lsd:
                logger.warn(
                    f"Found file for LSD {lsd} when expecting LSD {self.lsd}: {file}"
                )
                continue

            self._index[file_type] = file


def closest_after(lsd, days):
    for day in reversed(days):
        if lsd >= day:
            return day
    return closest_before(lsd, days)


def closest_before(lsd, days):
    for day in days:
        if lsd <= day:
            return day
    return closest_after(lsd, days)

#     def closest_after(self, days):
#         for day in reversed(days):
#             if self.lsd >= day.lsd:
#                 return day
#         return self.closest_before(days)

#     def closest_before(self, days):
#         for day in days:
#             if self.lsd <= day.lsd:
#                 return day
#         return self.closest_after(days)
