import copy
import holoviews as hv
import logging
import numpy as np
import panel
import param

from holoviews.plotting.util import process_cmap
from matplotlib import cm as matplotlib_cm

from caput.config import Reader, Property
from ch_pipeline.core.containers import RFIMask
from ch_util.ephemeris import chime, csd, skyfield_wrapper, csd_to_unix, unix_to_csd

from .heatmap import RaHeatMapPlot

from ..util.exception import DataError
from ..util.plotting import hv_image_with_gaps

logger = logging.getLogger(__name__)


class SensitivityPlot(RaHeatMapPlot, Reader):
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
    zlim_estimate = (0.88, 0.9)

    # parameters
    # Hide lsd, revision selectors by setting precedence < 0
    lsd = param.Selector(precedence=-1)
    revision = param.Selector(precedence=-1)

    polarization = param.ObjectSelector()
    mark_day_time = param.Boolean(default=True)
    mask_rfi = param.Boolean(default=True)
    divide_by_estimate = param.Boolean(default=False)

    def __init__(self, data, config, **params):
        self.data = data
        self.selections = None

        RaHeatMapPlot.__init__(
            self, "Sensitivity", activated=True, config=config, **params
        )
        self.height = 650
        self.read_config(config)
        self.logarithmic_colorscale = True

        # Register callback for switching colormap range between normalized using estimate and normal
        self.param.watch(self._changed_estimate, "divide_by_estimate", onlychanged=True)

    def _changed_estimate(self, *events):
        """When the divide_by_estimate option is changed, we keep track of what the colormap range was."""
        for event in events:
            if event.old:
                # divide_by_estimate was deactivated
                self.zlim_estimate = self.colormap_range
                # Make sure view is triggered also if the colormap stays the same
                if self.zlim == self.colormap_range:
                    self.param.trigger("colormap_range")
                self.colormap_range = self.zlim
            else:
                # dicide_by_estimate was activated
                self.zlim = self.colormap_range
                # Make sure view is triggered also if the colormap stays the same
                if self.zlim_estimate == self.colormap_range:
                    self.param.trigger("colormap_range")
                self.colormap_range = self.zlim_estimate

    @param.depends("lsd", "revision", watch=True)
    def update_pol(self):
        if self.lsd is None:
            return
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
        self.param.trigger("polarization")

    @param.depends(
        "lsd",
        "transpose",
        "logarithmic_colorscale",
        "serverside_rendering",
        "colormap_range",
        "polarization",
        "mark_day_time",
        "mask_rfi",
        "flag_mask",
        "flags",
        "height",
    )
    def view(self):
        if self.lsd is None:
            return panel.pane.Markdown("No data selected.")
        try:
            sens_container = self.data.load_file(self.revision, self.lsd, "sensitivity")
        except DataError as err:
            return panel.pane.Markdown(
                f"Error: {str(err)}. Please report this problem."
            )

        # Index map for ra (x-axis)
        sens_csd = csd(sens_container.time)
        index_map_ra = (sens_csd - self.lsd.lsd) * 360
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

        if self.flag_mask:
            sens = np.where(self._flags_mask(index_map_ra).T, np.nan, sens)

        # Set flagged data to nan
        sens = np.where(sens == 0, np.nan, sens)

        if self.mask_rfi:
            try:
                rfi_container = self.data.load_file(self.revision, self.lsd, "rfi")
            except DataError as err:
                return panel.pane.Markdown(
                    f"Error: {str(err)}. Please report this problem."
                )
            rfi = np.squeeze(rfi_container.mask[:])

            # This is expected to be either ch_pipeline.core.containers RFIMask or
            # draco.core.containers.RFIMask. The first is true for data free of RFI,
            # the second is true for data affected by RFI.
            if isinstance(rfi_container, RFIMask):
                logger.debug(
                    f"Inverting rfi mask, because container is a {type(rfi_container)}."
                )
                rfi = ~rfi

            # calculate percentage masked to print later
            rfi_percentage = round(np.count_nonzero(rfi) / rfi.size * 100)

            sens *= np.where(rfi, np.nan, 1)

        if self.divide_by_estimate:
            estimate = np.squeeze(sens_container.radiometer[:, sel_pol])
            if self.polarization == self.mean_pol_text:
                estimate = np.squeeze(np.nanmean(estimate, axis=1))
            estimate = np.where(estimate == 0, np.nan, estimate)
            sens = sens / estimate

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
        if self.mask_rfi:
            image_opts["title"] = f"RFI mask: {rfi_percentage}%"

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
            # Calculate the sun rise/set times on this sidereal day

            # Start and end times of the CSD
            start_time = csd_to_unix(self.lsd.lsd)
            end_time = csd_to_unix(self.lsd.lsd + 1)

            times, rises = chime.rise_set_times(
                skyfield_wrapper.ephemeris["sun"],
                start_time,
                end_time,
                diameter=-10,
            )
            sun_rise = 0
            sun_set = 0
            for t, r in zip(times, rises):
                if r:
                    sun_rise = (unix_to_csd(t) % 1) * 360
                else:
                    sun_set = (unix_to_csd(t) % 1) * 360

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
            height=self.height,
            responsive=True,
            bgcolor="lightgray",
            shared_axes=True,
        )

        return panel.Row(img, width_policy="max")
