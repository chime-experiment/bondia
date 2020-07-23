from caput.config import Property, Reader
import holoviews as hv
from jinja2 import Environment, PackageLoader
from jinja2.exceptions import TemplateNotFound
import logging
import panel as pn

from .data import DataLoader
from .util.exception import ConfigError
from .gui import BondiaGui

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class BondiaServer(Reader):
    _config_data_paths = Property({}, proptype=dict, key="data_paths")
    _template_name = Property("mwc", str, "html_template")
    _width_drawer_widgets = Property(220, int)
    _root_url = Property(proptype=str, default="", key="root_url")

    def __init__(self):
        hv.extension("bokeh")
        # hv.renderer("bokeh").theme = Theme(json={})  # Reset Theme
        pn.extension()

        try:
            env = Environment(loader=PackageLoader("bondia"))
        except ModuleNotFoundError:
            raise EnvironmentError(
                "Unable to find 'bondia' package ressources: templates."
            )

        try:
            self._template = env.get_template(f"{self._template_name}.html")
        except TemplateNotFound:
            raise ConfigError(f"Can't find template '{self._template_name}'.")

    def _finalise_config(self):
        self.data = DataLoader.from_config(self._config_data_paths)
        if not self.data.index:
            raise ConfigError("No data available.")

    def gui_instance(self):
        # logger.debug(f"Starting user session {pn.state.curdoc.session_context.id}.")
        instance = BondiaGui(
            self._template, self._width_drawer_widgets, self.data
        ).render()
        return instance

    @property
    def root_url(self):
        return self._root_url
