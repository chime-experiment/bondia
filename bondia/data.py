from typing import Type, Dict, Union

from caput.config import Property, Reader
from ch_pipeline.core import containers as ccontainers
from ch_pipeline.core.containers import RingMap
from draco.core import containers

import glob
import logging
import os
from pathlib import Path
import signal
import sys
import threading

from draco.core.containers import DelaySpectrum

from .util.day import Day
from .util.exception import DataError

logger = logging.getLogger(__name__)

FILE_TYPES = {
    "delayspectrum": "delayspectrum_lsd_*.h5",
    "ringmap": "ringmap_validation_freqs_lsd_*.h5",
    "sensitivity": "sensitivity_validation_lsd_*.h5",
    "rfi": "rfi_mask_lsd_*.h5",
}
CONTAINER_TYPES: Dict[str, Type[Union[DelaySpectrum, RingMap]]] = {
    "delayspectrum": containers.DelaySpectrum,
    "ringmap": ccontainers.RingMap,
    "sensitivity": containers.SystemSensitivity,
    "rfi": containers.RFIMask,
}


class DataLoader(Reader):
    path = Property(proptype=Path)
    interval = Property(proptype=int, default=600)

    def __init__(self):
        self._index = {}

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
        return sorted(self.revisions)[-1]

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
            rev_dirs = glob.glob(os.path.join(d, "rev_*"))
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

        return new_lsds

    def load_file(self, revision: str, day: Day, file_type: str):
        """Load the data of one day from disk."""
        try:
            f = getattr(self._index[revision][day], file_type)
        except AttributeError:
            raise DataError(f"{file_type} for day {day}, {revision} not available.")
        except KeyError as not_found:
            raise DataError(
                f"Couldn't find data for {not_found} when loading revision {revision}, day {day}"
            )
        if isinstance(f, CONTAINER_TYPES[file_type]):
            return getattr(self._index[revision][day], file_type)
        logger.debug(f"Loading {file_type} file for {revision}, {day}...")
        path = getattr(self._index[revision][day], file_type)
        if path is None:
            raise DataError(f"{file_type} for day {day}, {revision} not available.")
        setattr(
            self._index[revision][day],
            file_type,
            CONTAINER_TYPES[file_type].from_file(path),
        )
        return getattr(self._index[revision][day], file_type)


class LSD:
    def __init__(self, path: os.PathLike, rev: str, day: Day):
        self._day = day

        for file_type, file_type_glob in FILE_TYPES.items():
            file = glob.glob(os.path.join(path, file_type_glob))
            if len(file) > 1:
                raise DataError(
                    f"Found {len(file)} {file_type} files in {path} (Expected 1)."
                )
            elif len(file) == 0:
                logger.warning(
                    f"Found {len(file)} {file_type} files in {path} (Expected 1)."
                )
                continue
            file = file[0]

            logger.debug(f"Found {rev} file for lsd {day}: {file}")

            lsd = int(os.path.splitext(os.path.basename(file))[0][-4:])
            if lsd != day.lsd:
                raise DataError(
                    f"Found file for LSD {lsd} when expecting LSD {day.lsd}: {file}"
                )

            setattr(self, file_type, file)

    def __repr__(self):
        return self._day.__repr__()
