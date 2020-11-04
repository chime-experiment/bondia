import logging
import panel as pn
import param

from chimedb.dataflag.orm import DataFlagOpinion

from . import opinion
from .plot.delayspectrum import DelaySpectrumPlot
from .plot.ringmap import RingMapPlot
from .plot.sensitivity import SensitivityPlot


logger = logging.getLogger(__name__)


class BondiaGui(param.Parameterized):
    def __init__(self, template, width_drawer_widgets, data_loader, config_plots):
        self._width_drawer_widgets = width_drawer_widgets
        self._template = template
        self._plot = {}
        self._toggle_plot = {}
        self._opinion_buttons = {}
        self._data = data_loader
        self._config_plots = config_plots
        self._opinion_header = pn.pane.Markdown(
            "####Opinion", width=width_drawer_widgets
        )

        # TODO: remove after https://github.com/holoviz/panel/commit/203a16c10cb8fd4c55ec7887fade561ecc222938
        pn.pane.Alert.priority = 0
        pn.pane.Alert._rename = dict(pn.pane.Markdown._rename, alert_type=None)

        # TODO: once https://github.com/holoviz/panel/issues/1723 fixed, set width
        # width=width_drawer_widgets, sizing_mode="fixed"
        self._opinion_warning = pn.pane.Alert(
            "You didn't give your opinion yet.", alert_type="primary"
        )

    def _choose_lsd(self):
        if hasattr(self, "day_selector"):
            selected_day = self.day_selector.value
        else:
            selected_day = None

        days = self._data.days(self.rev_selector.value)
        if self.current_user is None:
            return days[-1]
        day = opinion.get_day_without_opinion(
            selected_day, days, self.rev_selector.value, self.current_user
        )
        logger.debug(f"Chose new LSD to display: {day}.")

        # If day doesn't change, the opinion UI is not updated. So we do it here...
        if hasattr(self, "day_selector") and day == selected_day:
            self.day_selector.param.trigger("value")

        return day

    def _update_opinion_warning(self, target, event):
        self._opinion_warning.alert_type = "primary"
        if self.current_user is None:
            self._opinion_warning.object = """
            Log in to give your opinion
            """
        elif opinion.get(event.new, self.rev_selector.value, self.current_user):
            self._opinion_warning.object = """
            **You already voted on the data quality of this day.** Choose a different option to change your decision.
            """
        else:
            self._opinion_warning.object = "You didn't give your opinion yet."

    def _update_opinion_button(self, lsd, button):
        self._opinion_buttons[
            button
        ].disabled = self.current_user is None or button == opinion.get(
            lsd, self.rev_selector.value, self.current_user
        )

    @pn.depends(pn.state.param.busy, watch=True)
    def _indicator(self, busy=False):
        # TODO: Replace with this when available: https://github.com/holoviz/panel/pull/1730
        return pn.indicators.LoadingSpinner(value=busy, width=20, height=20)

    def populate_template(self, template):
        self._plot = [
            DelaySpectrumPlot(self._data, self._config_plots.get("delayspectrum", {})),
            SensitivityPlot(self._data, self._config_plots.get("sensitivity", {})),
            RingMapPlot(self._data, self._config_plots.get("ringmap", {})),
        ]

        # Load revision, lsd selectors and set initial values
        self.rev_selector = pn.widgets.Select(
            options=list(self._data.revisions),
            width=self._width_drawer_widgets,
            name="Select Data Revision",
            value=self._data.latest_revision,
        )
        self.day_selector = pn.widgets.Select(
            options=list(self._data.days(self.rev_selector.value)),
            width=self._width_drawer_widgets,
            name="Select Sidereal Day",
            value=self._choose_lsd(),
        )

        def update_days(day_selector, event):
            """Update days depending on selected revision."""
            day_selector.value = self._choose_lsd()

        # Add a title over the plots showing the selected day and rev (and keep it updated)
        data_description = pn.pane.Markdown(
            f"<h4>LSD {self.day_selector.value} - {self.rev_selector.value}</h4>",
            width=800,
        )

        def update_data_description_day(data_description, event):
            data_description.object = (
                f"<h4>LSD {event.new} - {self.rev_selector.value}</h4>"
            )

        # It's enough to link the day selector to the description, since the revision selector
        # already is linked to the day selector in update_days.
        self.day_selector.link(
            data_description, callbacks={"value": update_data_description_day}
        )

        # Fill the template with components
        template.add_panel("data_description", data_description)
        template.add_panel("data_description1", data_description)
        template.add_panel("data_description2", data_description)
        template.add_panel("day_selector", self.day_selector)
        template.add_panel("rev_selector", self.rev_selector)

        # Loading spinner
        template.add_panel("busy_indicator", pn.Column(self._indicator))

        # Opinion buttons
        template.add_panel("opinion_header", self._opinion_header)
        template.add_panel("opinion_warning", self._opinion_warning)
        self._opinion_buttons["good"] = pn.widgets.Button(
            name="Mark day as good",
            button_type="success",
            width=self._width_drawer_widgets,
        )
        self._opinion_buttons["bad"] = pn.widgets.Button(
            name="Mark day as bad",
            button_type="danger",
            width=self._width_drawer_widgets,
        )
        self._opinion_buttons["unsure"] = pn.widgets.Button(
            name="I don't know",
            button_type="default",
            width=self._width_drawer_widgets,
        )
        for decision in DataFlagOpinion.decision.enum_list:
            # Add functionality to opinion button
            self._opinion_buttons[decision].param.watch(
                lambda event, d=decision: self._click_opinion(event, d), "clicks"
            )

            # Add button to the template
            template.add_panel(f"opinion_{decision}", self._opinion_buttons[decision])

            # Update buttons when opinion given
            self.day_selector.link(
                self._opinion_buttons[decision],
                callbacks={
                    "value": lambda target, event, d=decision: self._update_opinion_button(
                        event.new, d
                    )
                },
            )

        # Update opinion warning and buttons when LSD is changed
        self.day_selector.link(
            self._opinion_warning, callbacks={"value": self._update_opinion_warning}
        )

        # Trigger opinion UI callbacks once now
        self.day_selector.param.trigger("value")

        for plot in self._plot:
            plot.revision = self.rev_selector.value
            plot.lsd = self.day_selector.value

            # Link selected day, revision to plots
            self.rev_selector.link(plot, value="revision")
            self.day_selector.link(plot, value="lsd")

            # Fill in the plot selection toggle buttons
            self._toggle_plot[plot.id] = pn.widgets.Toggle(
                name=f"Deactivate {plot.name_}",
                button_type="success",
                value=True,
                width=self._width_drawer_widgets,
            )

            def toggle_plot(event, toggle_plot):
                if event.new:
                    toggle_plot.panel_row = True
                    self._toggle_plot[toggle_plot.id].button_type = "success"
                    self._toggle_plot[
                        toggle_plot.id
                    ].name = f"Deactivate {toggle_plot.name_}"
                else:
                    toggle_plot.panel_row = False
                    self._toggle_plot[toggle_plot.id].button_type = "danger"
                    self._toggle_plot[
                        toggle_plot.id
                    ].name = f"Activate {toggle_plot.name_}"

            self._toggle_plot[plot.id].param.watch(
                lambda event, tplot=plot: toggle_plot(event, tplot), "value"
            )
            self._toggle_plot[plot.id].param.trigger("value")

            template.add_panel(f"toggle_{plot.id}", self._toggle_plot[plot.id])
            template.add_panel(f"plot_{plot.id}", plot.panel_row)
            template.add_variable(f"title_{plot.id}", plot.name_)

        self.rev_selector.link(self.day_selector, callbacks={"value": update_days})
        return template

    def _click_opinion(self, event, decision):
        lsd = self.day_selector.value
        try:
            opinion.insert(
                self.current_user,
                lsd,
                self.rev_selector.value,
                decision,
            )
        except BaseException as err:
            logger.error(
                f"Failure inserting opinion for user {self.current_user}, revision {self.rev_selector.value}, "
                f"LSD {lsd}: {decision} ({err})"
            )
            self._opinion_warning.alert_type = "danger"
            self._opinion_warning.object = (
                f"Error adding opinion for LSD {lsd.lsd}. Please report this problem."
            )
        else:
            self._opinion_warning.alert_type = "success"
            self._opinion_warning.object = f"Opinion added for LSD {lsd.lsd}"
            self.day_selector.value = self._choose_lsd()

    @property
    def current_user(self):
        return pn.state.user

    def render(self):
        template = pn.Template(self._template)

        template.add_variable("subtitle", "CHIME Daily Validation")
        template.add_variable("app_title", "BON DIA")
        template.add_variable("username", self.current_user)
        template.add_variable("num_unvalidated", 19)

        return self.populate_template(template)
