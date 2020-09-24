import copy
import holoviews as hv
import logging
import numpy as np
import os
import panel
import param
import warnings

from holoviews.operation.datashader import datashade, rasterize
from holoviews.plotting.util import process_cmap
from matplotlib import cm as matplotlib_cm

from caput.config import Reader, Property
from ch_pipeline.core import containers as ccontainers
from ch_util import ephemeris, tools

from .plot import BondiaPlot

# TODO: the ephemeris module will get moved to caput soon
from ..util.ephemeris import source_transit, source_rise_set
from ..util.exception import DataError
from ..util.flags import get_flags_cached

logger = logging.getLogger(__name__)


class RingMapPlot(param.Parameterized, BondiaPlot, Reader):
    """
    Attributes
    ----------
    lsd : int
        Local stellar day.
    transpose
        Transpose the plot if True. Default `True`.
    log
        True for logarithmic color map (z-values). Default `False`.
    colormap_range
        (optional, if using datashader) Select limits of color map values (z-values). Default
        `None`.
    serverside_rendering
        True to use datashader. Automatically selects colormap for every zoom level, sends
        pre-rendered images to client. Default `True`.
    """

    # Display text for polarization option: mean of XX and YY
    mean_pol_text = "Mean(XX, YY)"

    # Limits to display in ringmap heatmap
    xlim = (-1, 1)
    ylim = (0, 360)
    zlim = (-5, 5)

    # Config
    _stack_path = Property(proptype=str, key="stack")
    _cache_reset_time = Property(
        proptype=int, key="flag_cache_reset_seconds", default=20
    )  # 86400)

    # parameters
    transpose = param.Boolean(default=True)
    logarithmic_colorscale = param.Boolean(default=False)
    # Default: turn on datashader and disable colormap range
    serverside_rendering = param.Selector(
        objects=[None, rasterize, datashade], default=rasterize
    )
    colormap_range = param.Range(default=zlim, constant=False)

    # Hide lsd, revision selectors by setting precedence < 0
    lsd = param.Selector(precedence=-1)
    revision = param.Selector(precedence=-1)
    beam = param.ObjectSelector()
    polarization = param.ObjectSelector()
    frequency = param.ObjectSelector()

    # FIXME: implement
    mark_moon = param.Boolean(default=True)
    mark_day_time = param.Boolean(default=True)

    template_subtraction = param.Boolean(default=True)
    crosstalk_removal = param.Boolean(default=True)
    weight_mask = param.Boolean(default=True)
    weight_mask_threshold = param.Number(default=40, bounds=(0, 100))
    flag_mask = param.Boolean(default=False)
    flags = param.ListSelector(
        objects=[
            "bad_calibration_fpga_restart",
            "globalflag",
            "acjump",
            "acjump_sd",
            "rain",
            "rain_sd",
            "bad_calibration_acquisition_restart",
            "misc",
            "rain1mm",
            "rain1mm_sd",
            "srs/bad_ringmap_broadband",
            "bad_calibration_gains",
            "snow",
            "decorrelated_cylinder",
        ],
        default=[
            "bad_calibration_fpga_restart",
            "acjump_sd",
            "bad_calibration_acquisition_restart",
            "rain1mm_sd",
            "srs/bad_ringmap_broadband",
            "bad_calibration_gains",
            "snow",
            "decorrelated_cylinder",
        ],
    )

    def __init__(self, data, config, **params):
        self.data = data
        self.selections = None
        self._chime_obs = ephemeris.chime_observer()

        BondiaPlot.__init__(self, "Ringmap")
        param.Parameterized.__init__(self, **params)
        self.read_config(config)

    def _finalise_config(self):
        if self._stack_path is None:
            logger.debug("No ringmap stack path supplied. Deactivating...")
            self.template_subtraction = False
            self.param["template_subtraction"].constant = True
        elif not os.path.isfile(self._stack_path):
            raise DataError(f"Ringmap stack file not found in path {self._stack_path}.")

    @param.depends("serverside_rendering", watch=True)
    def update_serverside_rendering(self):
        # Disable colormap range selection if using datashader (because it uses auto values)
        self.param["colormap_range"].constant = self.serverside_rendering == datashade

    def make_selection(self, data, key):
        objects = list(data.index_map[key])
        default = data.index_map[key][0]
        return objects, default

    @param.depends("lsd", watch=True)
    def update_freqs(self):
        try:
            rm = self.data.load_file(self.revision, self.lsd, "ringmap")
        except DataError as err:
            logger.error(f"Unable to get available frequencies from file: {err}")
            return
        self.param["frequency"].objects = [f[0] for f in rm.index_map["freq"]]
        self.frequency = rm.index_map["freq"][0][0]

    @param.depends("lsd", watch=True)
    def update_beam(self):
        try:
            rm = self.data.load_file(self.revision, self.lsd, "ringmap")
        except DataError as err:
            logger.error(f"Unable to get available beams from file: {err}")
            return
        self.param["beam"].objects, self.beam = self.make_selection(rm, "beam")

    @param.depends("lsd", watch=True)
    def update_pol(self):
        try:
            rm = self.data.load_file(self.revision, self.lsd, "ringmap")
        except DataError as err:
            logger.error(f"Unable to get available polarisations from file: {err}")
            return
        objects, value = self.make_selection(rm, "pol")
        if "XX" in objects and "YY" in objects:
            objects.append(self.mean_pol_text)
            value = self.mean_pol_text
        self.param["polarization"].objects = objects
        self.polarization = value

    @param.depends("weight_mask", watch=True)
    def update_weight_threshold_selection(self):
        self.param["weight_mask_threshold"].constant = not self.weight_mask

    @property
    def param_control(self):
        p = panel.param.Param(
            self.param,
            expand_button=False,
            widgets={
                "flags": panel.widgets.MultiChoice,
            },
        )
        return panel.Column(p)

    @param.depends(
        "lsd",
        "transpose",
        "logarithmic_colorscale",
        "serverside_rendering",
        "colormap_range",
        "beam",
        "polarization",
        "frequency",
        "mark_day_time",
        "mark_moon",
        "crosstalk_removal",
        "template_subtraction",
        "weight_mask",
        "weight_mask_threshold",
        "flag_mask",
        "flags",
    )
    def view(self):
        try:
            container = self.data.load_file(self.revision, self.lsd, "ringmap")
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
            flag_time_spans = get_flags_cached(self.flags, self._cache_reset_time)
            csd_arr = self.lsd.lsd + container.index_map["ra"] / 360.0
            flag_mask = np.zeros_like(csd_arr, dtype=np.bool)
            chime_obs = ephemeris.chime_observer()
            u2l = chime_obs.unix_to_lsd
            for type_, ca, cb in flag_time_spans:
                flag_mask[(csd_arr > u2l(ca)) & (csd_arr < u2l(cb))] = True
            flag_mask = flag_mask[:, np.newaxis]
            rmap = np.where(flag_mask, np.nan, rmap)

        if self.weight_mask:
            rms = np.squeeze(container.rms[sel_pol, sel_freq])
            if self.polarization == self.mean_pol_text:
                rms = np.nanmean(rms, axis=0)
            weight_mask = tools.invert_no_zero(rms) < self.weight_mask_threshold
            weight_mask = weight_mask[:, np.newaxis]
            rmap = np.where(weight_mask, np.nan, rmap)

        if self.template_subtraction:
            rm_stack = ccontainers.RingMap.from_file(
                self._stack_path, freq_sel=sel_freq
            )
            rm_stack = np.squeeze(rm_stack.map[sel_beam, sel_pol, sel_freq])
            if self.polarization == self.mean_pol_text:
                rm_stack = np.nanmean(rm_stack, axis=0)

            # FIXME: this is a hack. remove when rinmap stack file fixed.
            rmap -= rm_stack.reshape(rm_stack.shape[0], -1, 2).mean(axis=-1)

        if self.crosstalk_removal:
            # The mean of an all-nan slice (masked?) is nan. We don't need a warning about that.
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", r"All-NaN slice encountered")
                rmap -= np.nanmedian(rmap, axis=0)

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
            eph = ephemeris.skyfield_wrapper.ephemeris

            # Start and end times of the CSD
            st = self._chime_obs.lsd_to_unix(self.lsd.lsd)
            et = self._chime_obs.lsd_to_unix(self.lsd.lsd + 1)

            moon_time, moon_dec = source_transit(
                self._chime_obs.skyfield_obs(), eph["moon"], st, et, return_dec=True
            )

            if len(moon_time):
                lunar_transit = self._chime_obs.unix_to_lsd(moon_time[0])
                lunar_dec = moon_dec[0]
                lunar_ra = (lunar_transit % 1) * 360.0
                lunar_za = np.sin(np.radians(lunar_dec - 49.0))
                if self.transpose:
                    img *= hv.Ellipse(lunar_ra, lunar_za, (5.5, 0.15))
                else:
                    img *= hv.Ellipse(lunar_za, lunar_ra, (0.04, 21))

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
            height=500,
            responsive=True,
            shared_axes=False,
        )

        return panel.Row(img, width_policy="max")
