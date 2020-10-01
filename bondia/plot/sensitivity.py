import copy
import holoviews as hv
import logging
import numpy as np
import panel
import param

from holoviews.plotting.util import process_cmap
from matplotlib import cm as matplotlib_cm

from caput.config import Reader, Property
from ch_util import ephemeris

from .heatmap import HeatMapPlot

# TODO: the ephemeris module will get moved to caput soon
from ..util.ephemeris import source_rise_set
from ..util.exception import DataError
from ..util.plotting import hv_image_with_gaps

logger = logging.getLogger(__name__)


class SensitivityPlot(HeatMapPlot, Reader):
    """
    Attributes
    ----------
    lsd : int
        Local stellar day.
    """

    # Display text for polarization option: mean of XX and YY
    mean_pol_text = "Mean(XX, YY)"

    # Limits to display in ringmap heatmap
    ylim = (400, 800)
    xlim = (0, 360)
    zlim = (0.01, 0.1)

    # Config
    _cache_reset_time = Property(
        proptype=int, key="flag_cache_reset_seconds", default=86400
    )
    _cache_flags = Property(proptype=bool, key="cache_flags", default=False)

    # parameters
    # Hide lsd, revision selectors by setting precedence < 0
    lsd = param.Selector(precedence=-1)
    revision = param.Selector(precedence=-1)

    polarization = param.ObjectSelector()
    mark_day_time = param.Boolean(default=True)
    mask_rfi = param.Boolean(default=True)

    def __init__(self, data, config, **params):
        self.data = data
        self.selections = None
        self._chime_obs = ephemeris.chime_observer()

        HeatMapPlot.__init__(self, "Sensitivity", activated=True, **params)
        self.read_config(config)
        self.logarithmic_colorscale = True

    @param.depends("lsd", watch=True)
    def update_pol(self):
        try:
            rm = self.data.load_file(self.revision, self.lsd, "sensitivity")
        except DataError as err:
            logger.error(f"Unable to get available polarisations from file: {err}")
            return
        objects, value = self.make_selection(rm, "pol")
        if "XX" in objects and "YY" in objects:
            objects.append(self.mean_pol_text)
            value = self.mean_pol_text
        self.param["polarization"].objects = objects
        self.polarization = value

    @param.depends(
        "lsd",
        "transpose",
        "logarithmic_colorscale",
        "serverside_rendering",
        "colormap_range",
        "polarization",
        "mark_day_time",
        "mask_rfi",
    )
    def view(self):
        try:
            sens_container = self.data.load_file(self.revision, self.lsd, "sensitivity")
        except DataError as err:
            return panel.pane.Markdown(
                f"Error: {str(err)}. Please report this problem."
            )

        # Index map for ra (x-axis)
        sens_csd = ephemeris.csd(sens_container.time)
        index_map_ra = (sens_csd % 1) * 360
        axis_name_ra = "RA [degrees]"

        # Index map for frequency (y-axis)
        index_map_f = np.linspace(800.0, 400.0, 1024, endpoint=False)
        axis_name_f = "Frequency [MHz]"

        # Apply data selections
        if self.polarization == self.mean_pol_text:
            sel_pol = np.where(
                (sens_container.index_map["pol"] == "XX")
                | (sens_container.index_map["pol"] == "YY")
            )[0]
            sens = np.squeeze(sens_container.measured[:, sel_pol])
            sens = np.squeeze(np.nanmean(sens, axis=1))
        else:
            sel_pol = np.where(sens_container.index_map["pol"] == self.polarization)[0]
            sens = np.squeeze(sens_container.measured[:, sel_pol])

        if self.mask_rfi:
            try:
                rfi_container = self.data.load_file(self.revision, self.lsd, "rfi")
            except DataError as err:
                return panel.pane.Markdown(
                    f"Error: {str(err)}. Please report this problem."
                )
            rfi = np.squeeze(rfi_container.mask[:])
            sens *= np.where(rfi, np.nan, 1)

        if self.transpose:
            sens = sens.T
            index_x = index_map_f
            index_y = index_map_ra
            axis_names = [axis_name_f, axis_name_ra]
            xlim, ylim = self.ylim, self.xlim
        else:
            index_x = index_map_ra
            index_y = index_map_f
            axis_names = [axis_name_ra, axis_name_f]
            xlim, ylim = self.xlim, self.ylim

        image_opts = {
            "clim": self.colormap_range,
            "logz": self.logarithmic_colorscale,
            "cmap": process_cmap("viridis", provider="matplotlib"),
            "colorbar": True,
            "xticks": [0, 60, 120, 180, 240, 300, 360],
        }
        overlay_opts = {
            "xlim": xlim,
            "ylim": ylim,
        }

        # Fill in missing data
        img = hv_image_with_gaps(
            index_x, index_y, sens, opts=image_opts, kdims=axis_names
        ).opts(**overlay_opts)

        if self.serverside_rendering is not None:
            # set colormap
            cmap_inferno = copy.copy(matplotlib_cm.get_cmap("viridis"))

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
                # TODO: set xticks like above
            )

        if self.mark_day_time:
            # Calculate the sun rise/set times on this sidereal day (it's not clear to me there
            # is exactly one of each per day, I think not)
            sf_obs = self._chime_obs.skyfield_obs()

            # Start and end times of the CSD
            start_time = self._chime_obs.lsd_to_unix(self.lsd.lsd)
            end_time = self._chime_obs.lsd_to_unix(self.lsd.lsd + 1)

            times, rises = source_rise_set(
                sf_obs,
                ephemeris.skyfield_wrapper.ephemeris["sun"],
                start_time,
                end_time,
                diameter=-10,
            )
            sun_rise = 0
            sun_set = 0
            for t, r in zip(times, rises):
                if r:
                    sun_rise = (self._chime_obs.unix_to_lsd(t) % 1) * 360
                else:
                    sun_set = (self._chime_obs.unix_to_lsd(t) % 1) * 360

            # Highlight the day time data
            opts = {
                "color": "grey",
                "alpha": 0.5,
                "line_width": 1,
                "line_color": "black",
                "line_dash": "dashed",
            }

            span = hv.HSpan if self.transpose else hv.VSpan
            if sun_rise < sun_set:
                img *= span(sun_rise, sun_set).opts(**opts)
            else:
                img *= span(self.xlim[0], sun_set).opts(**opts)
                img *= span(sun_rise, self.xlim[-1]).opts(**opts)

        img.opts(
            # Fix height, but make width responsive
            height=500,
            responsive=True,
            bgcolor="lightgray",
        )

        return panel.Row(img, width_policy="max")
