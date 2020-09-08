from caput.config import Property, Reader
from draco.core import containers
import glob
import logging
import numpy as np
import os
from pathlib import Path
import signal
import sys
import threading

from .util.day import Day

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DataLoader(Reader):
    delay_spectrum = Property(proptype=Path)
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
            self.index_files(self.delay_spectrum)
            self._indexing_done.set()
            timer = threading.Timer(self.interval, self._periodic_index)
            timer.start()

    def _finalise_config(self):
        """Index files after caput config reader is done."""
        if self.delay_spectrum:
            # Start periodic indexing thread and wait until it ran once.
            self._periodic_indexer = threading.Thread(
                target=self._periodic_index, daemon=True
            )
            self._periodic_indexer.start()
            self._indexing_done.wait()
        else:
            logger.debug("No path to delay spectrum data in config, skipping...")

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
        (Re)index delay spectrum files.

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

        new_lsd = {}
        for d in dirs:
            rev_dirs = glob.glob(os.path.join(d, "rev_*"))
            for rev_dir in rev_dirs:
                if not os.path.isdir(rev_dir):
                    logger.debug(
                        f"Skipping {rev_dir} because it's not a (revision) directory."
                    )
                    continue
                rev = os.path.split(rev_dir)[-1]
                files = sorted(
                    glob.glob(os.path.join(rev_dir, "*/delayspectrum_lsd_*.h5"))
                )
                logger.debug(f"Found {rev} files: {files}")

                if rev not in self._index:
                    self._index[rev] = {}

                lsd = np.array(
                    [
                        int(os.path.splitext(os.path.basename(ff))[0][-4:])
                        for ff in files
                    ]
                )

                for cc, filename in zip(lsd, files):
                    if cc not in self.lsds(rev):
                        cc = Day.from_lsd(cc)
                        self._index[rev][cc] = filename
                        if rev not in new_lsd:
                            new_lsd[rev] = []
                        new_lsd[rev].append(cc)
                if rev in new_lsd:
                    logger.info(f"Found new {rev} data for days {new_lsd[rev]}.")
        return new_lsd

    def load_file(self, revision: str, day: Day):
        """Load the delay spectrum of one day from a file."""
        if isinstance(self._index[revision][day], containers.DelaySpectrum):
            return self._index[revision][day]
        logger.info(f"Loading revision {revision} data for day {day}.")
        self._index[revision][day] = containers.DelaySpectrum.from_file(
            self._index[revision][day]
        )
        return self._index[revision][day]
