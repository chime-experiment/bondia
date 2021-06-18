import copy
import holoviews as hv
import logging
import numpy as np
import os
import panel
import param
import warnings

from holoviews.plotting.util import process_cmap
from matplotlib import cm as matplotlib_cm

from caput.config import Reader, Property
from ch_pipeline.core import containers as ccontainers
from ch_util import tools
from ch_util.ephemeris import csd_to_unix, unix_to_csd, skyfield_wrapper, chime

from .heatmap import RaHeatMapPlot

from ..util.exception import DataError

logger = logging.getLogger(__name__)


class RingMapPlot(RaHeatMapPlot, Reader):
    """
    Attributes
    ----------
    lsd : int
        Local stellar day.
    """

    # Display text for polarization option: mean of XX and YY
    mean_pol_text = "Mean(XX, YY)"

    # Limits to display in ringmap heatmap
    xlim = (-1, 1)
    ylim = (0, 360)
    zlim = (-5, 5)
    zlim_intercyl = (-2, 2)

    # Config
    _stack_path = Property(proptype=str, key="stack")

    # Parameters
    # Hide lsd, revision selectors by setting precedence < 0
    lsd = param.Selector(precedence=-1)
    revision = param.Selector(precedence=-1)
    beam = param.ObjectSelector()
    polarization = param.ObjectSelector()
    frequency = param.ObjectSelector()
    mark_moon = param.Boolean(default=True)
    mark_day_time = param.Boolean(default=True)
    template_subtraction = param.Boolean(default=True)
    crosstalk_removal = param.Boolean(default=True)
    weight_mask = param.Boolean(default=True)
    weight_mask_threshold = param.Number(default=10, bounds=(0, 100))
    intercylinder_only = param.Boolean(default=False)

    def __init__(self, data, config, **params):
        self.data = data
        self.selections = None

        RaHeatMapPlot.__init__(self, "Ringmap", activated=True, config=config, **params)

        # transpose by default
        self.transpose = True

        self.height = 800

        self.read_config(config)

        # Keep track of template subtraction while intercylinder ringmap is viewed
        self.template_subtraction_non_intercylinder = self.template_subtraction

        # Register callback for switching colormap range betweem intercylinder and normal
        self.param.watch(self._changed_intercyl, "intercylinder_only", onlychanged=True)

    def _finalise_config(self):
        if self._stack_path is None:
            logger.debug("No ringmap stack path supplied. Deactivating...")
            self.template_subtraction = False
            self.param["template_subtraction"].constant = True
        elif not os.path.isfile(self._stack_path):
            raise DataError(f"Ringmap stack file not found in path {self._stack_path}.")

    @param.depends("lsd", "revision", watch=True)
    def update_freqs(self):
        if self.lsd is None:
            # Anyways make sure watchers are triggered
            self.param.trigger("frequency")
            return
        try:
            rm = self.data.load_file(self.revision, self.lsd, "ringmap")
        except DataError as err:
            logger.error(f"Unable to get available frequencies from file: {err}")
            # Anyways make sure watchers are triggered
            self.param.trigger("frequency")
            return
        self.param["frequency"].objects = [f[0] for f in rm.index_map["freq"]]
        self.frequency = rm.index_map["freq"][0][0]
        # Trigger watchers also if value didn't change
        self.param.trigger("frequency")

    @param.depends("frequency", watch=True)
    def update_beam(self):
        if self.lsd is None:
            # Anyways make sure watchers are triggered
            self.param.trigger("beam")
            return
        try:
            rm = self.data.load_file(self.revision, self.lsd, "ringmap")
        except DataError as err:
            logger.error(f"Unable to get available beams from file: {err}")
            # Anyways make sure watchers are triggered
            self.param.trigger("beam")
            return
        self.param["beam"].objects, self.beam = self.make_selection(rm, "beam")
        # Trigger watchers also if value didn't change
        self.param.trigger("beam")

    @param.depends("beam", watch=True)
    def update_pol(self):
        if self.lsd is None:
            # Anyways make sure watchers are triggered
            self.param.trigger("polarization")
            return
        try:
            rm = self.data.load_file(self.revision, self.lsd, "ringmap")
        except DataError as err:
            logger.error(f"Unable to get available polarisations from file: {err}")
            # Anyways make sure watchers are triggered
            self.param.trigger("polarization")
            return
        objects, value = self.make_selection(rm, "pol")
        if "XX" in objects and "YY" in objects:
            objects.append(self.mean_pol_text)
            value = self.mean_pol_text
        self.param["polarization"].objects = objects
        self.polarization = value
        # Trigger watchers also if value didn't change
        self.param.trigger("polarization")

    @param.depends("weight_mask", watch=True)
    def update_weight_threshold_selection(self):
        self.param["weight_mask_threshold"].constant = not self.weight_mask

    def _changed_intercyl(self, *events):
        """When the intercylinder_only option is changed, we keep track of what the colormap range was."""
        for event in events:
            if event.old:
                # changing from intercylinder to normal
                self.zlim_intercyl = self.colormap_range

                # Make sure view is triggered also if the colormap and template stay the same
                if (
                    self.zlim == self.colormap_range
                    and self.template_subtraction_non_intercylinder
                    == self.template_subtraction
                ):
                    self.param.trigger("colormap_range")

                # Restore template settings
                self.param["template_subtraction"].constant = False
                self.template_subtraction = self.template_subtraction_non_intercylinder

                self.colormap_range = self.zlim
            else:
                # changing from normal to intercylinder
                self.zlim = self.colormap_range

                # Make sure view is triggered also if the colormap and template stay the same
                if (
                    self.zlim_intercyl == self.colormap_range
                    and not self.template_subtraction
                ):
                    self.param.trigger("colormap_range")

                # Save template settings
                self.template_subtraction_non_intercylinder = self.template_subtraction
                self.template_subtraction = False
                self.param["template_subtraction"].constant = True

                self.colormap_range = self.zlim_intercyl

    # No dependency on intercyl_only, because that changes the colormap range already which triggers view.
    @param.depends(
        "transpose",
        "logarithmic_colorscale",
        "serverside_rendering",
        "colormap_range",
        "polarization",
        "mark_day_time",
        "mark_moon",
        "crosstalk_removal",
        "template_subtraction",
        "weight_mask",
        "weight_mask_threshold",
        "flag_mask",
        "flags",
        "height",
    )
    def view(self):
        if self.lsd is None:
            return panel.pane.Markdown("No data selected.")
        try:
            if self.intercylinder_only:
                name = "ringmap_intercyl"
            else:
                name = "ringmap"
            container = self.data.load_file(self.revision, self.lsd, name)
        except DataError as err:
            return panel.pane.Markdown(
                f"Error: {str(err)}. Please report this problem."
            )

        # Index map for ra (x-axis)
        index_map_ra = container.index_map["ra"]
        axis_name_ra = "RA [degrees]"

        # Index map for sin(ZA)/sin(theta) (y-axis)
        index_map_el = container.index_map["el"]
        axis_name_el = "sin(\u03B8)"

        # Apply data selections
        sel_beam = np.where(container.index_map["beam"] == self.beam)[0]
        sel_freq = np.where(
            [f[0] for f in container.index_map["freq"]] == self.frequency
        )[0]
        if self.polarization == self.mean_pol_text:
            sel_pol = np.where(
                (container.index_map["pol"] == "XX")
                | (container.index_map["pol"] == "YY")
            )[0]
            rmap = np.squeeze(container.map[sel_beam, sel_pol, sel_freq])
            rmap = np.nanmean(rmap, axis=0)
        else:
            sel_pol = np.where(container.index_map["pol"] == self.polarization)[0]
            rmap = np.squeeze(container.map[sel_beam, sel_pol, sel_freq])

        if self.flag_mask:
            rmap = np.where(self._flags_mask(container.index_map["ra"]), np.nan, rmap)

        if self.weight_mask:
            try:
                rms = np.squeeze(container.rms[sel_pol, sel_freq])
            except IndexError:
                logger.error(
                    f"rms dataset of ringmap file for rev {self.revision} lsd "
                    f"{self.lsd} is missing [{sel_pol}, {sel_freq}] (polarization, "
                    f"frequency). rms has shape {container.rms.shape}"
                )
                self.weight_mask = False
            else:
                rmap = np.where(self._weights_mask(rms), np.nan, rmap)

        # Set flagged data to nan
        rmap = np.where(rmap == 0, np.nan, rmap)

        if self.crosstalk_removal:
            # The mean of an all-nan slice (masked?) is nan. We don't need a warning about that.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", r"All-NaN slice encountered")
                rmap -= np.nanmedian(rmap, axis=0)

        if self.template_subtraction:
            try:
                rm_stack = self.data.load_file_from_path(
                    self._stack_path, ccontainers.RingMap
                )
            except DataError as err:
                return panel.pane.Markdown(
                    f"Error: {str(err)}. Please report this problem."
                )

            # The stack file has all polarizations, so we can't reuse sel_pol
            if self.polarization == self.mean_pol_text:
                stack_sel_pol = np.where(
                    (rm_stack.index_map["pol"] == "XX")
                    | (rm_stack.index_map["pol"] == "YY")
                )[0]
            else:
                stack_sel_pol = np.where(
                    rm_stack.index_map["pol"] == self.polarization
                )[0]

            try:
                rm_stack = np.squeeze(rm_stack.map[sel_beam, stack_sel_pol, sel_freq])
            except IndexError as err:
                logger.error(
                    f"map dataset of ringmap stack file "
                    f"is missing [{sel_beam}, {stack_sel_pol}, {sel_freq}] (beam, polarization, "
                    f"frequency). map has shape {rm_stack.map.shape}:\n{err}"
                )
                self.template_subtraction = False
            else:
                if self.polarization == self.mean_pol_text:
                    rm_stack = np.nanmean(rm_stack, axis=0)

                # FIXME: this is a hack. remove when rinmap stack file fixed.
                rmap -= rm_stack.reshape(rm_stack.shape[0], -1, 2).mean(axis=-1)

        if self.transpose:
            rmap = rmap.T
            index_x = index_map_ra
            index_y = index_map_el
            axis_names = [axis_name_ra, axis_name_el]
            xlim, ylim = self.ylim, self.xlim
        else:
            index_x = index_map_el
            index_y = index_map_ra
            axis_names = [axis_name_el, axis_name_ra]
            xlim, ylim = self.xlim, self.ylim

        img = hv.Image(
            (index_x, index_y, rmap),
            datatype=["image", "grid"],
            kdims=axis_names,
        ).opts(
            clim=self.colormap_range,
            logz=self.logarithmic_colorscale,
            cmap=process_cmap("inferno", provider="matplotlib"),
            colorbar=True,
            xlim=xlim,
            ylim=ylim,
        )

        if self.serverside_rendering is not None:
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

        if self.mark_moon:
            # Put a ring around the location of the moon if it transits on this day
            eph = skyfield_wrapper.ephemeris

            # Start and end times of the CSD
            st = csd_to_unix(self.lsd.lsd)
            et = csd_to_unix(self.lsd.lsd + 1)

            moon_time, moon_dec = chime.transit_times(
                eph["moon"], st, et, return_dec=True
            )

            if len(moon_time):
                lunar_transit = unix_to_csd(moon_time[0])
                lunar_dec = moon_dec[0]
                lunar_ra = (lunar_transit % 1) * 360.0
                lunar_za = np.sin(np.radians(lunar_dec - 49.0))
                if self.transpose:
                    img *= hv.Ellipse(lunar_ra, lunar_za, (5.5, 0.15))
                else:
                    img *= hv.Ellipse(lunar_za, lunar_ra, (0.04, 21))

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
            if self.transpose:
                if sun_rise < sun_set:
                    img *= hv.VSpan(sun_rise, sun_set).opts(**opts)
                else:
                    img *= hv.VSpan(self.ylim[0], sun_set).opts(**opts)
                    img *= hv.VSpan(sun_rise, self.ylim[1]).opts(**opts)

            else:
                if sun_rise < sun_set:
                    img *= hv.HSpan(sun_rise, sun_set).opts(**opts)
                else:
                    img *= hv.HSpan(self.ylim[0], sun_set).opts(**opts)
                    img *= hv.HSpan(sun_rise, self.ylim[1]).opts(**opts)

        img.opts(
            # Fix height, but make width responsive
            height=self.height,
            responsive=True,
            shared_axes=True,
            bgcolor="lightgray",
        )

        return panel.Row(img, width_policy="max")

    def _weights_mask(self, rms):
        if self.polarization == self.mean_pol_text:
            rms = np.nanmean(rms, axis=0)
        weight_mask = tools.invert_no_zero(rms) < self.weight_mask_threshold
        return weight_mask[:, np.newaxis]
