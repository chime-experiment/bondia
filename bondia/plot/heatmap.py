import logging
import param

from .plot import BondiaPlot


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
