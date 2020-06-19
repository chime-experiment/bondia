from bokeh.themes.theme import Theme
from caput.config import Property, Reader
import holoviews as hv
from jinja2 import Environment, FileSystemLoader
import logging
import panel as pn
import pathlib

from .data import DataLoader
from .util.exception import ConfigError
from .gui import BondiaGui

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class BondiaServer(Reader):
    _config_data_paths = Property({}, proptype=dict, key="data_paths")
    _template_name = Property("mwc", str, "html_template")
    _width_drawer_widgets = Property(220, int)

    def __init__(self):
        hv.extension("bokeh")
        hv.renderer("bokeh").theme = Theme(json={})  # Reset Theme
        pn.extension()

        env = Environment(
            loader=FileSystemLoader(pathlib.Path(__file__).parent / "template")
        )
        self._template = env.get_template(f"{self._template_name}.html")

    def _finalise_config(self):
        self.data = DataLoader.from_config(self._config_data_paths)
        if not self.data.index:
            raise ConfigError("No data available.")

    def gui_instance(self):
        logger.debug("Starting user session.")
        instance = BondiaGui(
            self._template, self._width_drawer_widgets, self.data
        ).render()
        return instance
