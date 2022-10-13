from collections import OrderedDict, deque
import glob
import logging
import os
from pathlib import Path
import signal
import sys
import threading
from typing import Type, Dict, Union

from caput.config import Property, Reader
from ch_pipeline.core.containers import RingMap
from draco.core.containers import DelaySpectrum, RFIMask, SystemSensitivity

from bondia.util.day import Day
from bondia.util.exception import DataError

logger = logging.getLogger(__name__)

FILE_TYPES = {
    "delayspectrum": "delayspectrum_lsd_*.h5",
    "ringmap": "ringmap_validation_freqs_lsd_*.h5",
    "ringmap_intercyl": "ringmap_intercyl_validation_freqs_lsd_*.h5",
    "sensitivity": "sensitivity_validation_lsd_*.h5",
    "rfi": "rfi_mask_lsd_*.h5",
}
CONTAINER_TYPES: Dict[str, Type[Union[DelaySpectrum, RingMap]]] = {
    "delayspectrum": DelaySpectrum,
    "ringmap": RingMap,
    "ringmap_intercyl": RingMap,
    "sensitivity": SystemSensitivity,
    "rfi": RFIMask,
}


class DataLoader(Reader):
    path = Property(proptype=Path)
    interval = Property(proptype=int, default=600)
    max_days_in_memory = Property(proptype=int, default=10)

    def __init__(self):
        self.num_days_in_memory = 0
        self._index = {}
        self._index_by_path = {}
        self._lru = {}

        # Set up periodic data file indexing
        self._periodic_indexer = None
        self._indexing_done = threading.Event()
        self._exit_event = threading.Event()

        def stop_indexer(signum, frame):
            self._exit_event.set()
            if self._periodic_indexer:
                self._periodic_indexer.join()
            sys.exit()

        signal.signal(signal.SIGINT, stop_indexer)

    def _periodic_index(self):
        """Periodically index new files."""
        if not self._exit_event.is_set():
            if not self.index_files(self.path):
                logger.debug(f"No new files found. Indexing again in {self.interval}s")
            self._indexing_done.set()
            timer = threading.Timer(self.interval, self._periodic_index)
            timer.start()

    def _finalise_config(self):
        """Index files after caput config reader is done."""
        if self.path:
            # Start periodic indexing thread and wait until it ran once.
            self._periodic_indexer = threading.Thread(
                target=self._periodic_index, daemon=True
            )
            self._periodic_indexer.start()
            self._indexing_done.wait()
        else:
            logger.debug("No data path in config, skipping...")

    @property
    def index(self):
        return self._index

    def days(self, revision: str):
        return list(self._index[revision].keys())

    def lsds(self, revision: str):
        return [day.lsd for day in self.days(revision)]

    @property
    def revisions(self):
        return list(self._index.keys())

    @property
    def latest_revision(self):
        """
        Get latest revision.

        Note
        ----
        This assumes the revisions being numbered like "rev_00", "rev_01", "rev_17", where their
        order is the same as the revision strings sorted by python string comparison.
        """
        return self.revisions[-1]

    def index_files(self, dirs):
        """
        (Re)index data files.

        Parameters
        ----------
        dirs : str or list(str)

        Returns
        -------
        list(Day)
            List of new lsd found.
        """
        if isinstance(dirs, os.PathLike):
            dirs = [dirs]

        new_lsds = {}
        for d in dirs:
            rev_dirs = sorted(glob.glob(os.path.join(d, "rev_*")))
            for rev_dir in rev_dirs:
                if not os.path.isdir(rev_dir):
                    logger.debug(
                        f"Skipping {rev_dir} because it's not a (revision) directory."
                    )
                    continue
                rev = os.path.split(rev_dir)[-1]

                lsd_dirs = sorted(glob.glob(os.path.join(rev_dir, "*")))

                for lsd_dir in lsd_dirs:
                    try:
                        lsd = int(os.path.basename(lsd_dir))
                    except ValueError as err:
                        logger.debug(
                            f"Skipping dir '{lsd_dir}'. It doesn't seem to be an lsd dir: {err}"
                        )
                    day = Day.from_lsd(lsd)
                    if rev not in self._index:
                        self._index[rev] = {}
                    if day.lsd not in self.lsds(rev):
                        if rev not in new_lsds:
                            new_lsds[rev] = []
                        try:
                            new_lsd = LSD(lsd_dir, rev, day)
                        except DataError as err:
                            logger.error(
                                f"Failure loading data for {rev}, {day}: {err}"
                            )
                            continue
                        else:
                            new_lsds[rev].append(new_lsd)
                            self._index[rev][day] = new_lsd

                if rev in new_lsds and len(new_lsds[rev]) > 0:
                    logger.info(f"Found new {rev} data for day(s) {new_lsds[rev]}.")

                    # Sort the new days into the right positions in the ordered dict
                    self._index[rev] = OrderedDict(
                        sorted(self._index[rev].items(), key=lambda item: item[0].lsd)
                    )

        return new_lsds

    def load_file(self, revision: str, day: Day, file_type: str):
        """
        Load the data of one day from disk.

        Data is loaded from disk only once and then cached.
        """
        try:
            f = getattr(self._index[revision][day], file_type)
        except AttributeError:
            raise DataError(f"{file_type} for day {day}, {revision} not available.")
        except KeyError as not_found:
            raise DataError(
                f"Couldn't find data for {not_found} when loading revision {revision}, day {day}"
            )
        if f is not None:
            self._lru_push(revision, day, file_type)
            return f
        logger.debug(f"Loading {file_type} file for {revision}, {day}...")
        f = self._index[revision][day].files[file_type]
        if f is None:
            raise DataError(f"{file_type} for day {day}, {revision} not available.")
        self._free_oldest_file(file_type)
        setattr(
            self._index[revision][day],
            file_type,
            CONTAINER_TYPES[file_type].from_file(f),
        )
        self._lru_push(revision, day, file_type)
        return getattr(self._index[revision][day], file_type)

    def _free_oldest_file(self, file_type: str):
        """Remove the file from memory that had been loaded the longest time ago."""
        if file_type not in self._lru:
            self._lru[file_type] = deque()
            return
        if len(self._lru[file_type]) > self.max_days_in_memory - 1:
            i = self._lru_pop(file_type)
            setattr(self._index[i[0]][i[1]], file_type, None)

    def _lru_pop(self, file_type):
        """
        Get indices of least recently used file.

        Returns
        -------
        Tuple[str, Day]
            revision and day
        """
        i = self._lru[file_type].popleft()
        logger.debug(f"Removing {file_type} for {i[0]}, day {i[1]} from memory")
        return i

    def _lru_push(self, revision: str, day: Day, file_type: str):
        """
        Signal recent usage of file indices.

        Parameters
        ----------
        revision : str
            Revision key
        day : Day
            Day
        file_type : str
            File type name
        """
        if file_type not in self._lru:
            self._lru[file_type] = deque()
        indices = (revision, day)
        if indices in self._lru[file_type]:
            self._lru[file_type].remove(indices)
            logger.debug(
                f"Keeping {file_type} for {revision}, day {day} in memory longer."
            )
        self._lru[file_type].append(indices)

    def load_file_from_path(self, path: os.PathLike, container):
        """
        Load a special file from path.

        Data is loaded from disk only once and then cached.
        """
        try:
            return self._index_by_path[path]
        except KeyError:
            if not os.path.isfile(path):
                raise DataError(f"Couldn't find a file at path '{path}'")
            logger.debug(f"Loading special file from path '{path}'...")
            self._index_by_path[path] = container.from_file(path)
            return self._index_by_path[path]


class LSD:
    def __init__(self, path: os.PathLike, rev: str, day: Day):
        self._day = day
        self.files = {}

        for file_type, file_type_glob in FILE_TYPES.items():
            file = glob.glob(os.path.join(path, file_type_glob))
            if len(file) != 1:
                raise DataError(
                    f"Found {len(file)} {file_type} files in {path} (Expected 1)."
                )
            file = file[0]

            logger.debug(f"Found {rev} file for lsd {day}: {file}")

            lsd = int(os.path.splitext(os.path.basename(file))[0][-4:])
            if lsd != day.lsd:
                raise DataError(
                    f"Found file for LSD {lsd} when expecting LSD {day.lsd}: {file}"
                )

            self.files[file_type] = file
            setattr(self, file_type, None)

    def __repr__(self):
        return self._day.__repr__()
