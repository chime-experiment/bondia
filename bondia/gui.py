import panel as pn

from .plot.delayspectrum import DelaySpectrumPlot


class BondiaGui:
    def __init__(self, template, width_drawer_widgets, data_loader):
        self._width_drawer_widgets = width_drawer_widgets
        self._template = template
        self._plot = {}
        self._toggle_plot = {}
        self._data = data_loader

    def populate_template(self, template):
        delay = DelaySpectrumPlot(self._data)
        self._plot[delay.id] = delay

        # Load revision, lsd selectors and set initial values
        rev_selector = pn.widgets.Select(
            options=list(self._data.revisions),
            width=self._width_drawer_widgets,
            name="Select Data Revision",
            value=self._data.latest_revision,
        )
        delay.revision = rev_selector.value
        day_selector = pn.widgets.Select(
            options=list(self._data.days(delay.revision)),
            width=self._width_drawer_widgets,
            name="Select Sidereal Day",
        )
        delay.lsd = day_selector.value

        def update_days(day_selector, event):
            """Update days depending on selected revision."""
            old_selected_day = day_selector.value
            day_selector.options = list(self._data.days(event.new))
            new_selected_day = old_selected_day.closest_after(day_selector.options)
            day_selector.value = new_selected_day

        # Link selected day, revision to plots
        rev_selector.link(delay, value="revision")
        rev_selector.link(day_selector, callbacks={"value": update_days})
        day_selector.link(delay, value="lsd")

        # Fill the template with components
        components = [("day_selector", day_selector), ("rev_selector", rev_selector)]

        # Fill in the plot selection toggle buttons
        for p in self._plot.values():
            self._toggle_plot[p.id] = pn.widgets.Toggle(
                name=f"Deactivate {p.name}",
                button_type="success",
                value=True,
                width=self._width_drawer_widgets,
            )
            self._toggle_plot[p.id].param.watch(self.update_widget, "value")
            self._toggle_plot[p.id].param.trigger("value")

            components.append((f"toggle_{p.id}", self._toggle_plot[p.id]))
            components.append((f"plot_{p.id}", p.panel_row))

        for l, c in components:
            template.add_panel(l, c)
        return template

    def render(self):
        template = pn.Template(self._template)

        template.add_variable("subtitle", "CHIME Daily Validation")
        template.add_variable("app_title", "BON DIA")

        return self.populate_template(template)

    def update_widget(self, event):
        id = "delay_spectrum"
        toggle = self._toggle_plot[id]
        if event.new:
            self._plot[id].panel_row = True
            toggle.button_type = "success"
            toggle.name = "Deactivate Delay Spectrum"
        else:
            self._plot[id].panel_row = False
            toggle.button_type = "danger"
            toggle.name = "Activate Delay Spectrum"
