import os
import glob

from caput.config import Property, Reader
from ch_pipeline.core import containers
import logging
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import panel as pn
import param
import holoviews as hv
from holoviews.operation.datashader import datashade, rasterize
from holoviews.plotting.util import process_cmap
from holoviews import streams
from pathlib import Path
import numpy as np

from .plot import BondiaPlot
from ..utils.day import Day

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DelaySpectrumPlot(param.Parameterized, BondiaPlot, Reader):
    """
    Attributes
    ----------
    lsd : int
        Local stellar day.
    transpose
        Transpose the plot if True. Default `False`.
    log
        True for logarithmic color map (z-values). Default `True`.
    use_datashader
        True to use datashader. Automatically selects colormap for every zoom level, sends
        pre-rendered images to client. Default `True`.
    clim
        (optional, if using datashader) Select limits of color map values (z-values). Default
        `None`.
    """

    data_path = Property(proptype=Path)

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
                self._index[cc] = containers.DelaySpectrum.from_file(filename)
                new_lsd.append(cc)
                logger.info("Loaded new data from LSD {}".format(cc))

        return new_lsd

    # parameters
    transpose = param.Boolean(default=False)
    log = param.Boolean(default=True)
    use_datashader = param.Boolean(default=False)
    clim = param.Range(default=(0.1, 10000))
    lsd = param.Selector()

    @param.depends("lsd", "transpose", "log", "use_datashader", "clim")
    def view(self):
        print("plotting lsd {}".format(self.lsd))

        spectrum = self.index[self.lsd]
        x, y = spectrum.index_map["baseline"].T

        range_delay = np.percentile(spectrum.index_map["delay"] * 1e3, [0, 100])

        ux, uix = np.unique(np.round(x).astype(np.int), return_inverse=True)

        nplot = ux.size

        width = np.ones(nplot)
        width[-1] = 1.2

        gs = gridspec.GridSpec(
            2, nplot, width_ratios=width, height_ratios=[0.55, 0.45], wspace=0.125
        )
        import panel

        bounds = []
        all_img = panel.Row()
        self.subplot_title = ["x = 0 m", "x = 22 m", "x = 44 m", "x = 66 m"]

        for pp, pux in enumerate(ux):
            if not pux:
                slc = slice(0, 1)
            else:
                slc = slice(0, 2)

            plt.subplot(gs[slc, pp])

            # Get the baselines for this cylinder separation
            this_cyl_sep = np.flatnonzero(uix == pp)

            # Sort the indices by the N-S baseline distance
            this_cyl_sep = this_cyl_sep[np.argsort(y[this_cyl_sep])]

            # Determine span of data
            range_y = np.percentile(y[this_cyl_sep], [0, 100])

            extent = (range_y[0], range_y[-1], range_delay[0], range_delay[1])

            # Discard baselines that are set to zero
            this_cyl_sep = this_cyl_sep[
                np.any(spectrum.spectrum[this_cyl_sep, :] > 0.0, axis=-1)
            ]

            # Make image
            if self.transpose:
                extent = (range_y[0], range_y[-1], range_delay[0], range_delay[1])
                self.mplot[pp] = spectrum.spectrum[this_cyl_sep, :].T
            else:
                extent = (range_delay[0], range_delay[1], range_y[0], range_y[-1])
                print(extent)
                self.mplot[pp] = spectrum.spectrum[this_cyl_sep, :]

            i = 2048
            j = len(self.mplot[pp])

            print(f"baseline size: {spectrum.index_map['baseline'].size}")
            print(f"extent: {extent}")
            img = hv.Image(
                (range(i), range(j), self.mplot[pp]),
                datatype=["image", "grid"],
                kdims=["tau [nsec]", "y [m]"],  # extents=(512,0,2048,0),
            ).opts(
                colorbar=True,
                clim=self.clim,
                logz=self.log,
                cmap=process_cmap("inferno", provider="matplotlib"),
                title=self.subplot_title[pp],
                ylim=(0, len(self.mplot[pp]) * 2),
                tools=["ybox_select"],
                active_tools=["ybox_select"],
            )

            bounds.append(streams.BoundsY(source=img, rename={"boundsy": f"sel_{pp}"}))

            if not self.use_datashader:
                all_img.append(img)
            else:
                cmap_inferno = matplotlib.cm.__dict__["inferno"]
                cmap_inferno.set_under("black")
                cmap_inferno.set_bad("lightgray")
                all_img.append(
                    (
                        datashade(img, width=800, height=1600, cmap=cmap_inferno)
                        * hv.QuadMesh(
                            rasterize(img, width=800, height=1600, dynamic=False)
                        )
                    )
                )

            # plt.vlines(0.0, extent[2], extent[3], color='white', linestyle=':', linewidth=1.5)
            # plt.hlines(0.0, extent[0], extent[1], color='white', linestyle=':', linewidth=1.5)
            #
            # sep = 20.0
            # plt.yticks(np.arange(np.sign(range_y[0]) * sep * (np.abs(range_y[0]) // int(sep)),
            #                      sep * (range_y[1] // int(sep) + 1), sep))
            #
            # if rng is not None:
            #     plt.xlim(rng)
            #
            # if transpose:
            #     plt.xlabel("y [m]")
            #     if not pp:
            #         plt.ylabel(r"$\tau$ [nsec]")
            # else:
            #     plt.xlabel(r"$\tau$ [nsec]")
            #     if not pp:
            #         plt.ylabel("y [m]")
            # plt.title("x = %d m" % pux)
            #
            # if pp == (nplot - 1):
            #     cbar = plt.colorbar(img, label='Delay Spectrum')

        # def combine_selections(**kwargs):
        #     """
        #     Combines selections on all available plots into a single selection by index.
        #     """
        #     if all(not v for v in kwargs.values()):
        #         return slice(None)
        #     selection = {}
        #     for key, bounds in kwargs.items():
        #         if bounds is None:
        #             continue
        #         elif len(bounds) == 2:
        #             selection[key] = bounds
        #         else:
        #             xbound, ybound = key.split('__')
        #             selection[xbound] = bounds[0], bounds[2]
        #             selection[ybound] = bounds[1], bounds[3]
        #     return sorted(set(data.select(**selection).data.index))

        self.selection = hv.DynamicMap(self.select_data, streams=bounds)
        return all_img

    def select_data(self, **kwargs):
        print(f"select data {kwargs}")

        def parse_kwargs(kwargs):
            for num, sel in kwargs.items():
                if sel is not None:
                    if self.selections is None or sel != self.selections[num]:
                        return num, sel
            return None, None

        name, selection = parse_kwargs(kwargs)
        self.selections = kwargs
        if name is None:
            pp = 0
        else:
            pp = int(name[4:])
        print(f"parsed select {name}: {selection}")
        print(f"mplot y size: {self.mplot[pp].shape}")

        if selection is None:
            selection = (0, 2)
        else:
            selection = (int(selection[0]), int(selection[1]))
        i = 2048
        j = selection[1] - selection[0]

        img = hv.Image(
            (
                range(i),
                range(selection[0], selection[1]),
                self.mplot[pp][selection[0] : selection[1], :],
            ),
            datatype=["image", "grid"],
            kdims=["tau [nsec]", "y [m]"],
        ).opts(
            colorbar=True,
            clim=self.clim,
            logz=self.log,
            cmap=process_cmap("inferno", provider="matplotlib"),
            title=self.subplot_title[pp],
        )
        return img

    @param.depends("lsd")
    def title(self):
        return f"## Delay Spectrum (LSD {self.lsd})"

    def panel(self):
        return pn.Column(self.title, self.view)

    def __init__(self, name: str = "Delay Spectrum"):
        self._index = {}
        self.selections = None
        self.mplot = {}
        BondiaPlot.__init__(self, name)

    def _finalise_config(self):
        self.index_files(self.data_path)
        DelaySpectrumPlot.__dict__["lsd"].default = list(self.index.keys())[-1]
        DelaySpectrumPlot.__dict__["lsd"].objects = self.index
