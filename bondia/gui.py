import logging
import panel as pn

from tornado.web import decode_signed_value

from .plot.delayspectrum import DelaySpectrumPlot
from .plot.ringmap import RingMapPlot


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
        delay = DelaySpectrumPlot(
            self._data, self._config_plots.get("delayspectrum", {})
        )
        ringmap = RingMapPlot(self._data, self._config_plots.get("ringmap", {}))
        self._plot[delay.id] = delay
        self._plot[ringmap.id] = ringmap

        # Load revision, lsd selectors and set initial values
        rev_selector = pn.widgets.Select(
            options=list(self._data.revisions),
            width=self._width_drawer_widgets,
            name="Select Data Revision",
            value=self._data.latest_revision,
        )
        delay.revision = rev_selector.value
        ringmap.revision = rev_selector.value
        day_selector = pn.widgets.Select(
            options=list(self._data.days(rev_selector.value)),
            width=self._width_drawer_widgets,
            name="Select Sidereal Day",
            value=self._data.days(rev_selector.value)[-1],
        )
        delay.lsd = day_selector.value
        ringmap.lsd = day_selector.value

        def update_days(day_selector, event):
            """Update days depending on selected revision."""
            old_selected_day = day_selector.value
            day_selector.options = list(self._data.days(event.new))
            new_selected_day = old_selected_day.closest_after(day_selector.options)
            day_selector.value = new_selected_day

        # Link selected day, revision to plots
        rev_selector.link(delay, value="revision")
        rev_selector.link(ringmap, value="revision")
        rev_selector.link(day_selector, callbacks={"value": update_days})
        day_selector.link(delay, value="lsd")
        day_selector.link(ringmap, value="lsd")

        # Add a title over the plots showing the selected day and rev (and keep it updated)
        data_description = pn.pane.Markdown(
            f"<h1>LSD {day_selector.value} - {rev_selector.value}</h1>", width=600
        )

        def update_data_description_day(data_description, event):
            data_description.object = f"<h1>LSD {event.new} - {rev_selector.value}</h1>"

        # It's enough to link the day selector to the description, since the revision selector
        # already is linked to the day selector in update_days.
        day_selector.link(
            data_description, callbacks={"value": update_data_description_day}
        )

        # Fill the template with components
        components = [
            ("data_description", data_description),
            ("day_selector", day_selector),
            ("rev_selector", rev_selector),
        ]

        # Fill in the plot selection toggle buttons
        for p in self._plot.values():
            self._toggle_plot[p.id] = pn.widgets.Toggle(
                name=f"Deactivate {p.name_}",
                button_type="success",
                value=True,
                width=self._width_drawer_widgets,
            )
            self._toggle_plot[p.id].param.watch(
                lambda event: self.toggle_plot(event, p.id, p.name_), "value"
            )
            self._toggle_plot[p.id].param.trigger("value")

            components.append((f"toggle_{p.id}", self._toggle_plot[p.id]))
            components.append((f"plot_{p.id}", p.panel_row))

        for name, c in components:
            template.add_panel(name, c)
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

    def toggle_plot(self, event, id, name):
        toggle = self._toggle_plot[id]
        if event.new:
            self._plot[id].panel_row = True
            toggle.button_type = "success"
            toggle.name = f"Deactivate {name}"
        else:
            self._plot[id].panel_row = False
            toggle.button_type = "danger"
            toggle.name = f"Activate {name}"
