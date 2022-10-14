import logging
import holoviews as hv
import panel as pn
import param

from chimedb.dataflag.orm import DataFlagOpinion

from bondia import opinion
from bondia.plot.delayspectrum import DelaySpectrumPlot, DelaySpectrumPlotHPF
from bondia.plot.ringmap import RingMapPlot
from bondia.plot.sensitivity import SensitivityPlot


logger = logging.getLogger(__name__)

options_decision = DataFlagOpinion.decision.enum_list


class BondiaGui(param.Parameterized):

    lsd = param.ObjectSelector(label="Select Sidereal Day")
    revision = param.ObjectSelector(label="Select Data Revision")
    filter_lsd = param.Boolean(default=False, label="Hide days I have voted for")
    sort_lsds = param.Boolean(default=False, label="Sort by number of opinions")

    def __init__(
        self,
        template,
        width_drawer_widgets,
        data_loader,
        config_plots,
        root_url,
        **params,
    ):
        self._width_drawer_widgets = width_drawer_widgets
        self._template = template
        self._plot = {}
        self._toggle_plot = {}
        self._opinion_buttons = {}
        self._data = data_loader
        self._config_plots = config_plots
        self._root_url = root_url
        self._opinion_header = pn.pane.Markdown(
            "####Opinion", width=width_drawer_widgets
        )
        self._opinion_notes = pn.widgets.TextAreaInput(
            placeholder="Before inserting or changing your opinion you can type a comment about it here.",
            max_length=5000,
            width=width_drawer_widgets,
            height=100,
        )

        # TODO: once https://github.com/holoviz/panel/issues/1723 fixed, set width
        # width=width_drawer_widgets, sizing_mode="fixed"
        self._opinion_warning = pn.pane.Alert(
            "You didn't give your opinion yet.", alert_type="primary"
        )

        self._day_stats = pn.Row(pn.Column(), pn.Column(), pn.Column)

        param.Parameterized.__init__(self, **params)

        # Load revision, lsd selectors and set initial values
        self.param["revision"].objects = list(self._data.revisions)
        self.revision = self._data.latest_revision
        self.param["lsd"].objects = list(self._data.days(self.revision))
        self.lsd = self._choose_lsd()

    @param.depends("revision", "filter_lsd", "sort_lsds", watch=True)
    def update_days(self):
        """Update days depending on selected revision."""

        if self.filter_lsd and self.current_user is not None:
            days = opinion.get_days_without_opinion(
                list(self._data.days(self.revision)),
                self.revision,
                self.current_user,
            )
        else:
            days = list(self._data.days(self.revision))

        if self.sort_lsds:
            days = opinion.sort_by_num_opinions(self.revision, days)

        self.param["lsd"].objects = days

        if self.param["lsd"].objects:
            l = self._choose_lsd()
            if getattr(self, "lsd", -1) == l:
                self.lsd = l
                self.param.trigger("lsd")
            else:
                self.lsd = l

    @param.depends("lsd")
    def data_description(self):
        """A title over the plots showing the selected day and rev (and keep it updated)"""
        return pn.pane.Markdown(f"<h4>LSD {self.lsd} - {self.revision}</h4>", width=800)

    @param.depends("lsd", watch=True)
    def update_data_description_day(self):

        # Update opinion warning and buttons when LSD is changed
        self._update_opinion_warning()

        # Link selected day, revision to plots
        for plot in self._plot:
            plot.lsd = self.lsd
            plot.revision = self.revision

    def _choose_lsd(self):
        if self.sort_lsds:
            day = self.param["lsd"].objects[0]
        else:
            selected_day = getattr(self, "lsd", None)

            days = self._data.days(self.revision)
            if self.current_user is None:
                return days[-1]
            day = opinion.get_day_without_opinion(
                selected_day, days, self.revision, self.current_user
            )
        logger.debug(f"Chose new LSD to display: {day}.")

        return day

    def _update_opinion_warning(self):
        self._opinion_warning.alert_type = "primary"
        if self.current_user is None:
            self._opinion_warning.object = """
            Log in to give your opinion
            """
            self._opinion_warning.height = 80
        elif opinion.get(self.lsd, self.revision, self.current_user):
            self._opinion_warning.object = """
            **You already voted on the data quality of this day.** Choose an option to overwrite it..
            """
            self._opinion_warning.height = 110
        else:
            self._opinion_warning.object = "You didn't give your opinion yet."
            self._opinion_warning.height = 80

        # Also update day stats here
        if self.lsd is not None:
            num_opinions_rev, num_opinions_rest = opinion.get_opinions_for_day(
                self.lsd, self.revision
            )
            num_opinions_rev.update({"total": sum(num_opinions_rev.values())})
            num_opinions_rest.update({"total": sum(num_opinions_rest.values())})
            keys = list(set(num_opinions_rev.keys()) | set(num_opinions_rest.keys()))
            self._day_stats[0] = hv.Table(
                (
                    keys,
                    [num_opinions_rev[key] for key in keys],
                    [num_opinions_rest[key] for key in keys],
                ),
                ["Decision", f"{self.revision}"],
                "All other revisions",
                label="Number of opinions on this day",
            ).opts(sortable=False, index_position=None)
        opinions_by_user = opinion.get_user_stats(zero=False)
        opinions_by_user = [
            (k, opinions_by_user[k])
            for k in sorted(opinions_by_user, key=opinions_by_user.get, reverse=True)
        ]
        self._day_stats[2] = hv.Table(
            opinions_by_user,
            "User",
            "Number of opinions",
            label="Highscore",
        )
        notes_by_rev = opinion.get_notes_for_day(self.lsd)

        # Pre-fill notes field with what user previously entered
        try:
            self._opinion_notes.value = notes_by_rev[self.revision][self.current_user][
                1
            ]
        except KeyError:
            self._opinion_notes.value = None

        # Print all notes found for this day/revision
        text = """
            <span style="color:black;font-family:Arial;font-style:bold;font-weight:bold;font-size:12pt">
            Notes
            </span><div style="text-align: left">
            """

        def render_notes(revision, notes_by_user):
            """Generate HTML of notes for one revision."""
            text = f"<hr><pre>  {revision}</pre><br>"
            for user, entry in notes_by_user.items():
                text = f"{text}<b>{user}:</b> (<i>{entry[0]}</i>) {entry[1]}<br>"
            return text

        # Show notes for current revision first
        try:
            notes_cur_rev = notes_by_rev.pop(self.revision)
        except KeyError as k:
            logger.debug(f"No notes for this day (self.lsd) current revision ({k}).")
        else:
            text = f"{text}{render_notes(self.revision, notes_cur_rev)}"

        # Show notes for other revisions
        for revision, notes_by_user in notes_by_rev.items():
            text = f"{text}{render_notes(revision, notes_by_user)}"

        text = f"{text}</div>"
        self._day_stats[1] = pn.pane.HTML(
            text,
        )

    @pn.depends(pn.state.param.busy)
    def _indicator(self, busy=False):
        # TODO: Replace with this when available: https://github.com/holoviz/panel/pull/1730
        return pn.indicators.LoadingSpinner(value=busy, width=20, height=20)

    def populate_template(self, template):
        # Checkbox to show only days w/o opinion
        template.add_panel("day_filter_opinion_checkbox", self.param["filter_lsd"])
        # Checkbox to sort days by number of opinions
        template.add_panel("day_sort_checkbox", self.param["sort_lsds"])

        # Fill the template with components
        template.add_panel("data_description", self.data_description)
        template.add_panel("data_description1", self.data_description)
        template.add_panel("data_description2", self.data_description)
        template.add_panel(
            "day_selector",
            pn.Param(
                self.param["lsd"],
                widgets={"lsd": {"width": self._width_drawer_widgets}},
            ),
        )
        template.add_panel(
            "rev_selector",
            pn.Param(
                self.param["revision"],
                widgets={"revision": {"width": self._width_drawer_widgets}},
            ),
        )

        # Loading spinner
        template.add_panel("busy_indicator", pn.Column(self._indicator))

        # Opinion buttons
        template.add_panel("opinion_header", self._opinion_header)
        template.add_panel("opinion_notes", self._opinion_notes)
        template.add_panel("opinion_warning", self._opinion_warning)
        self._opinion_buttons["good"] = pn.widgets.Button(
            name="Mark day as good",
            button_type="success",
            width=self._width_drawer_widgets,
            disabled=self.current_user is None,
        )
        self._opinion_buttons["bad"] = pn.widgets.Button(
            name="Mark day as bad",
            button_type="danger",
            width=self._width_drawer_widgets,
            disabled=self.current_user is None,
        )
        self._opinion_buttons["unsure"] = pn.widgets.Button(
            name="I don't know",
            button_type="default",
            width=self._width_drawer_widgets,
            disabled=self.current_user is None,
        )

        for decision in options_decision:
            # Add functionality to opinion button
            self._opinion_buttons[decision].param.watch(
                lambda event, d=decision: self._click_opinion(event, d), "clicks"
            )

            # Add button to the template
            template.add_panel(f"opinion_{decision}", self._opinion_buttons[decision])

        template.add_panel("day_stats", self._day_stats)

        # Trigger opinion UI callbacks once now
        self.param.trigger("lsd")

        self._plot = [
            DelaySpectrumPlot(self._data, self._config_plots.get("delayspectrum", {})),
            DelaySpectrumPlotHPF(
                self._data, self._config_plots.get("delayspectrum_hpf", {})
            ),
            SensitivityPlot(self._data, self._config_plots.get("sensitivity", {})),
            RingMapPlot(self._data, self._config_plots.get("ringmap", {})),
        ]

        for plot in self._plot:
            plot.revision = self.revision
            plot.lsd = self.lsd

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

        return template

    def _click_opinion(self, event, decision):
        lsd = self.lsd
        if lsd is None:
            self._opinion_warning.alert_type = "danger"
            self._opinion_warning.object = "No data selected."
            return
        if self._opinion_notes.value is None and decision == "bad":
            self._opinion_warning.alert_type = "danger"
            self._opinion_warning.object = (
                "Marking data as 'bad' requires inserting a comment above."
            )
            return
        try:
            opinion.insert(
                self.current_user,
                lsd,
                self.revision,
                decision,
                self._opinion_notes.value,
            )
        except BaseException as err:
            logger.error(
                f"Failure inserting opinion for user {self.current_user}, revision {self.revision}, "
                f"LSD {lsd}: {decision} ({err})"
            )
            self._opinion_warning.alert_type = "danger"
            self._opinion_warning.object = (
                f"Error adding opinion for LSD {lsd.lsd}. Please report this problem."
            )
            self._opinion_warning.height = 110
        else:
            self._opinion_warning.alert_type = "success"
            self._opinion_warning.object = f"Opinion added for LSD {lsd.lsd}"
            if self.sort_lsds or self.filter_lsd:
                self.update_days()
            self.lsd = self._choose_lsd()

    @property
    def current_user(self):
        return pn.state.user

    def render(self):
        template = pn.Template(self._template)

        template.add_variable("subtitle", "CHIME Daily Validation")
        template.add_variable("app_title", "BONDIA")
        template.add_variable("username", self.current_user)
        template.add_variable("num_unvalidated", 19)
        template.add_variable("root_url", self._root_url)

        return self.populate_template(template)
