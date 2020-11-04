import copy
import holoviews as hv
import logging
import panel
import param
import numpy as np

from holoviews.plotting.util import process_cmap
from matplotlib import cm as matplotlib_cm

from .heatmap import HeatMapPlot
from ..util.exception import DataError

logger = logging.getLogger(__name__)


class DelaySpectrumPlot(HeatMapPlot):
    """
    Attributes
    ----------
    lsd : int
        Local stellar day.
    """

    # default value for colormap range
    zlim = (0.1, 10000)

    # parameters
    helper_lines = param.Boolean(default=True)

    # Hide lsd, revision selectors by setting precedence < 0
    lsd = param.Selector(precedence=-1)
    revision = param.Selector(precedence=-1)

    def __init__(self, data, config, **params):
        self.data = data
        self.selections = None
        HeatMapPlot.__init__(self, "Delay Spectrum", activated=True, **params)

        # set default values
        self.transpose = True
        self.logarithmic_colorscale = True

    @param.depends(
        "lsd",
        "transpose",
        "logarithmic_colorscale",
        "serverside_rendering",
        "colormap_range",
        "helper_lines",
    )
    def view(self):
        if self.lsd is None:
            return panel.pane.Markdown("No data selected.")
        try:
            spectrum = self.data.load_file(self.revision, self.lsd, "delayspectrum")
        except DataError as err:
            return panel.pane.Markdown(
                f"Error: {str(err)}. Please report this problem."
            )

        x, y = spectrum.index_map["baseline"].T

        # Index map for delay (x-axis)
        index_map_delay_nsec = spectrum.index_map["delay"] * 1e3

        ux, uix = np.unique(np.round(x).astype(np.int), return_inverse=True)

        # Fill a column with plots (one per pair of cylinders)
        imgs = {}
        mplot = {}
        ylim = None
        for pp, pux in reversed(list(enumerate(ux))):
            # Get the baselines for this cylinder separation
            this_cyl_sep = np.flatnonzero(uix == pp)

            # Sort the indices by the N-S baseline distance
            this_cyl_sep = this_cyl_sep[np.argsort(y[this_cyl_sep])]

            # Determine span of data (y-axis)
            range_y = np.percentile(y[this_cyl_sep], [0, 100])
            range_x = np.percentile(index_map_delay_nsec, [0, 100])

            # Discard baselines that are set to zero
            this_cyl_sep = this_cyl_sep[
                np.any(spectrum.spectrum[this_cyl_sep, :] > 0.0, axis=-1)
            ]

            # TODO: what do we do in this case?
            # See https://github.com/chime-experiment/bondia/issues/23
            if len(this_cyl_sep) == 0:
                continue

            # Index map for baseline (y-axis)
            baseline_index = y[this_cyl_sep]

            # Plot for south-west baseline == 0 is done last. Keep the same y-axis range for it.
            if pux != 0 or ylim is None:
                ylim_max = (range_y[0], range_y[-1])
            xlim = (range_x[0], range_x[-1])
            ylim = ylim_max

            # axis names
            axis_name_tau = "τ [nsec]"
            axis_name_y = "y [m]"

            # Make image
            if self.transpose:
                mplot[pp] = spectrum.spectrum[this_cyl_sep, :].T
                index_x = baseline_index
                index_y = index_map_delay_nsec
                xlim, ylim = ylim, xlim
                axis_names = [axis_name_y, axis_name_tau]
            else:
                mplot[pp] = spectrum.spectrum[this_cyl_sep, :]
                index_x = index_map_delay_nsec
                index_y = baseline_index
                axis_names = [axis_name_tau, axis_name_y]

            # holoviews checks for regular sampling before plotting an Image.
            # The CHIME baselines are not regularly sampled enough to pass through the default rtol
            # (1e-6), but we anyways want to plot the delay spectrum in an Image, not a QuadMesh.
            img = hv.Image(
                (index_x, index_y, mplot[pp]),
                datatype=["image", "grid"],
                kdims=axis_names,
                rtol=2,
            ).opts(
                clim=self.colormap_range,
                logz=self.logarithmic_colorscale,
                cmap=process_cmap("inferno", provider="matplotlib"),
                # Show colorbar only in rightmost plot (convert from numpy bool).
                colorbar=bool(pux == ux[-1]),
                # Show yaxis only in leftmost plot
                yaxis="left" if pux == ux[0] else None,
                title=f"x = {pux} m",
                xlim=xlim,
                ylim=ylim,
            )

            if self.serverside_rendering is None:
                if self.helper_lines:
                    img = (img * hv.VLine(0) * hv.HLine(0)).opts(
                        hv.opts.VLine(color="white", line_width=3, line_dash="dotted"),
                        hv.opts.HLine(color="white", line_width=3, line_dash="dotted"),
                    )
            else:
                # set colormap
                cmap_inferno = copy.copy(matplotlib_cm.get_cmap("inferno"))
                cmap_inferno.set_under("black")
                cmap_inferno.set_bad("lightgray")

                # Set z-axis normalization (other possible values are 'eq_hist', 'cbrt').
                if self.logarithmic_colorscale:
                    normalization = "log"
                else:
                    normalization = "linear"

                # datashade/rasterize the image
                img = self.serverside_rendering(
                    img,
                    cmap=cmap_inferno,
                    precompute=True,
                    x_range=xlim,
                    y_range=ylim,
                    normalization=normalization,
                )

                if self.helper_lines:
                    img = (img * hv.VLine(0) * hv.HLine(0)).opts(
                        hv.opts.VLine(color="white", line_width=3, line_dash="dotted"),
                        hv.opts.HLine(color="white", line_width=3, line_dash="dotted"),
                    )
            img.opts(
                # Fix height, but make width responsive
                height=500,
                responsive=True,
                shared_axes=False,
            )

            imgs[pux] = img

        imgs = hv.NdLayout(imgs, kdims="x [m]")
        imgs.opts(merge_tools=True, shared_axes=False)
        all_img = panel.Row(imgs, width_policy="max")
        return all_img
