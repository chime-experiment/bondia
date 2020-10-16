import logging
import panel as pn

from tornado.web import decode_signed_value

from .plot.delayspectrum import DelaySpectrumPlot
from .plot.ringmap import RingMapPlot
from .plot.sensitivity import SensitivityPlot


logger = logging.getLogger(__name__)


class BondiaGui:
    def __init__(
        self, template, width_drawer_widgets, data_loader, config_plots, cookie_secret
    ):
        self._width_drawer_widgets = width_drawer_widgets
        self._template = template
        self._plot = {}
        self._toggle_plot = {}
        self._data = data_loader
        self.cookie_secret = cookie_secret
        self._config_plots = config_plots

    def populate_template(self, template):
        self._plot = {
            DelaySpectrumPlot(self._data, self._config_plots.get("delayspectrum", {})),
            RingMapPlot(self._data, self._config_plots.get("ringmap", {})),
            SensitivityPlot(self._data, self._config_plots.get("sensitivity", {})),
        }

        # Load revision, lsd selectors and set initial values
        rev_selector = pn.widgets.Select(
            options=list(self._data.revisions),
            width=self._width_drawer_widgets,
            name="Select Data Revision",
            value=self._data.latest_revision,
        )
        day_selector = pn.widgets.Select(
            options=list(self._data.days(rev_selector.value)),
            width=self._width_drawer_widgets,
            name="Select Sidereal Day",
            value=self._data.days(rev_selector.value)[-1],
        )

        def update_days(day_selector, event):
            """Update days depending on selected revision."""
            old_selected_day = day_selector.value
            day_selector.options = list(self._data.days(event.new))
            new_selected_day = old_selected_day.closest_after(day_selector.options)
            day_selector.value = new_selected_day

        # Add a title over the plots showing the selected day and rev (and keep it updated)
        data_description = pn.pane.Markdown(
            f"<h4>LSD {day_selector.value} - {rev_selector.value}</h4>", width=800
        )

        def update_data_description_day(data_description, event):
            data_description.object = f"<h4>LSD {event.new} - {rev_selector.value}</h4>"

        # It's enough to link the day selector to the description, since the revision selector
        # already is linked to the day selector in update_days.
        day_selector.link(
            data_description, callbacks={"value": update_data_description_day}
        )

        # Fill the template with components
        template.add_panel("data_description", data_description)
        template.add_panel("data_description1", data_description)
        template.add_panel("data_description2", data_description)
        template.add_panel("day_selector", day_selector)
        template.add_panel("rev_selector", rev_selector)

        for plot in self._plot:
            plot.revision = rev_selector.value
            plot.lsd = day_selector.value

            # Link selected day, revision to plots
            rev_selector.link(plot, value="revision")
            day_selector.link(plot, value="lsd")

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

        rev_selector.link(day_selector, callbacks={"value": update_days})
        return template

    @property
    def current_user(self):
        if self.cookie_secret is None:
            return "-"
        # Try to find cookies. I think this will start working in panel==0.10.
        # TODO: clean up when it works
        secure_cookie = None
        try:
            secure_cookie = pn.state.curdoc.session_context.request.cookies["user"]
        except AttributeError as err:
            logger.error(err)
            try:
                secure_cookie = pn.state.cookies["user"]
            except AttributeError as err:
                logger.error(err)
                return "FAILURE"
            except KeyError:
                logger.warning("User cookie not found.")
                return "-"
        except KeyError:
            logger.warning("User cookie not found.")
            return "-"
        user = decode_signed_value(self.cookie_secret, "user", secure_cookie).decode(
            "utf-8"
        )
        return user

    def render(self):
        template = pn.Template(self._template)

        template.add_variable("subtitle", "CHIME Daily Validation")
        template.add_variable("app_title", "BON DIA")
        template.add_variable("username", self.current_user)
        template.add_variable("num_unvalidated", 19)

        return self.populate_template(template)
