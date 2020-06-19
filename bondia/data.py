from caput.config import Property, Reader
from draco.core import containers
import glob
import logging
import numpy as np
import os
from pathlib import Path

from .util.day import Day

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DataLoader(Reader):
    delay_spectrum = Property(proptype=Path)

    def __init__(self):
        self._index = {}

    def _finalise_config(self):
        """Do things after caput config reader is done."""
        if self.delay_spectrum:
            self.index_files(self.delay_spectrum)
        else:
            logger.debug("No path to delay spectrum data in config, skipping...")

    @property
    def index(self):
        return self._index

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
        files = []
        for d in dirs:
            files += sorted(glob.glob(os.path.join(d, "delayspectrum_lsd_*.h5")))
        logger.debug("Found files: {}".format(files))

        lsd = np.array(
            [int(os.path.splitext(os.path.basename(ff))[0][-4:]) for ff in files]
        )
        new_lsd = []

        for cc, filename in zip(lsd, files):
            if cc not in self._index:
                cc = Day.from_lsd(cc)
                logger.info(f"Found new data for day {cc}.")
                self._index[cc] = filename
                new_lsd.append(cc)

        return new_lsd

    def load_file(self, day: Day):
        """Load the delay spectrum of one day from a file."""
        if isinstance(self._index[day], containers.DelaySpectrum):
            return self._index[day]
        logger.info(f"Loading day {day}.")
        self._index[day] = containers.DelaySpectrum.from_file(self._index[day])
        return self._index[day]
