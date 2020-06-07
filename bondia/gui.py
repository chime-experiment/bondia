from bokeh.themes.theme import Theme
from caput.config import Property, Reader
import datetime
import holoviews as hv
from jinja2 import Environment, FileSystemLoader
import panel as pn
import pathlib

from .plots.delayspectrum import DelaySpectrumPlot


class BondiaGui(Reader):
    config_delayspectrum = Property(None, dict, "delay_spectrum")
    template_name = Property("mwc", str, "html_template")
    width_drawer_widgets = Property(220, int)

    def __init__(self):
        hv.extension("bokeh")
        hv.renderer("bokeh").theme = Theme(json={})  # Reset Theme
        pn.extension()

        env = Environment(
            loader=FileSystemLoader(pathlib.Path(__file__).parent / "templates")
        )
        jinja_template = env.get_template(f"{self.template_name}.html")

        self.template = pn.Template(jinja_template)

        self.template.add_variable("subtitle", "CHIME Daily Validation")
        self.template.add_variable("app_title", "bon dia")

        self.plot = {}
        self.toggle_plot = {}

    def populate_template(self):
        print(self.config_delayspectrum)
        if self.config_delayspectrum:
            delay = DelaySpectrumPlot.from_config(self.config_delayspectrum)
            self.plot[delay.id] = delay

        day_selector = pn.widgets.Select(
            name="Select LSD", options=delay.index, width=self.width_drawer_widgets
        )

        # Fille the template with components
        components = [("day_selector", day_selector)]

        # Fill in the plot selection toggle buttons
        for p in self.plot.values():
            self.toggle_plot[p.id] = pn.widgets.Toggle(
                name=f"Deactivate {p.name}",
                button_type="success",
                value=True,
                width=self.width_drawer_widgets,
            )
            self.toggle_plot[p.id].param.watch(self.update_widget, "value")
            self.toggle_plot[p.id].param.trigger("value")

            components.append((f"toggle_{p.id}", self.toggle_plot[p.id]))
            components.append((f"plot_{p.id}", p.panel_row))

        for l, c in components:
            self.template.add_panel(l, c)

    def start_server(self):
        self.template.show(port=8008)

    def update_widget(self, event):
        print(event)
        id = "delay_spectrum"
        toggle = self.toggle_plot[id]
        if event.new:
            self.plot[id].panel_row = True
            toggle.button_type = "success"
            toggle.name = "Deactivate Delay Spectrum"
        else:
            self.plot[id].panel_row = False
            toggle.button_type = "danger"
            toggle.name = "Activate Delay Spectrum"
