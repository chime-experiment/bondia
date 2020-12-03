import logging
import numpy as np
import panel
import param

from ch_util.ephemeris import csd_to_unix, unix_to_csd
from caput.config import Reader, Property

from .plot import BondiaPlot
from ..util.flags import get_flags_cached, get_flags


logger = logging.getLogger(__name__)


class HeatMapPlot(BondiaPlot, param.Parameterized):
    """
    Base class for common features used in heat map plots.

    Attributes
    ----------
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

    # parameters
    transpose = param.Boolean(default=False)
    logarithmic_colorscale = param.Boolean(default=False)
    serverside_rendering = param.Selector()
    colormap_range = param.Range(constant=False)

    def __init__(self, name: str, activated: bool = True, **params):
        BondiaPlot.__init__(self, name, activated)
        param.Parameterized.__init__(self, **params)
        self.colormap_range = self.zlim if hasattr(self, "zlim") else (-5, 5)

        # TODO: for some reason this has to be done before panel.serve
        # See https://discourse.holoviz.org/t/panel-serve-with-num-procs-breaks-if-importing-datashade/1353
        from holoviews.operation.datashader import datashade, rasterize

        self.param["serverside_rendering"].objects = [None, rasterize, datashade]
        self.serverside_rendering = rasterize

    @param.depends("serverside_rendering", watch=True)
    def update_serverside_rendering(self):
        # TODO: for some reason this has to be done before panel.serve
        # See https://discourse.holoviz.org/t/panel-serve-with-num-procs-breaks-if-importing-datashade/1353
        from holoviews.operation.datashader import datashade

        # Disable colormap range selection if using datashader (because it uses auto values)
        self.param["colormap_range"].constant = self.serverside_rendering == datashade

    def make_selection(self, data, key):
        objects = list(data.index_map[key])
        default = data.index_map[key][0]
        return objects, default


class RaHeatMapPlot(HeatMapPlot, param.Parameterized, Reader):
    """
    Base class for heat maps with right ascention (RA) on the x-axis.
    """

    _cache_flags = Property(proptype=bool, key="cache_flags", default=False)
    _cache_reset_time = Property(
        proptype=int, key="flag_cache_reset_seconds", default=86400
    )

    flag_mask = param.Boolean(default=True)
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

    def __init__(self, name: str, activated: bool = True, config=None, **params):
        HeatMapPlot.__init__(self, name, activated, **params)
        self.read_config(config)

    @property
    def param_control(self):
        """Overwrite param_control to use MultiChoice widget for the flags selection."""
        p = panel.param.Param(
            self.param,
            expand_button=False,
            widgets={
                "flags": panel.widgets.MultiChoice,
            },
            width=325,
        )
        return panel.Column(p)

    def _flags_mask(self, index_map_ra):
        if self._cache_flags:
            flag_time_spans = get_flags_cached(self.flags, self._cache_reset_time)
        else:
            flag_time_spans = get_flags(
                self.flags,
                csd_to_unix(self.lsd.lsd),
                csd_to_unix(self.lsd.lsd + 1),
            )
        csd_arr = self.lsd.lsd + index_map_ra / 360.0
        flag_mask = np.zeros_like(csd_arr, dtype=np.bool)
        for type_, ca, cb in flag_time_spans:
            flag_mask[(csd_arr > unix_to_csd(ca)) & (csd_arr < unix_to_csd(cb))] = True
        return flag_mask[:, np.newaxis]
