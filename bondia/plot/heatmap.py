import logging
import param

from holoviews.operation.datashader import datashade, rasterize

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
    transpose = param.Boolean(default=True)
    logarithmic_colorscale = param.Boolean(default=False)
    serverside_rendering = param.Selector(
        objects=[None, rasterize, datashade], default=rasterize
    )
    colormap_range = param.Range(constant=False)

    def __init__(self, name: str, activated: bool = True, **params):
        BondiaPlot.__init__(self, name, activated)
        param.Parameterized.__init__(self, **params)
        self.colormap_range = self.zlim if hasattr(self, "zlim") else (-5, 5)

    @param.depends("serverside_rendering", watch=True)
    def update_serverside_rendering(self):
        # Disable colormap range selection if using datashader (because it uses auto values)
        self.param["colormap_range"].constant = self.serverside_rendering == datashade

    def make_selection(self, data, key):
        objects = list(data.index_map[key])
        default = data.index_map[key][0]
        return objects, default