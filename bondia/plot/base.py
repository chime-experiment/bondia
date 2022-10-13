from panel import Row, Param
import param


class BondiaPlot(param.Parameterized):
    def __init__(self, name: str, activated: bool = True):
        self._name = name
        self._id = name.lower().replace(" ", "_")
        self._panel_row_active = activated
        self._panel_row = None

    height = param.Integer(500, bounds=(0, 10000))

    @property
    def id(self):
        return self._id

    @property
    def name_(self):
        return self._name

    @property
    def title(self):
        return f"## {self._name}"

    @property
    def param_control(self):
        return Param(
            self.param,
            # Stop param from showing the expand button of the datashading function
            # selector. It would be nice to show it, but there are options that can make
            # the whole server crash.
            expand_button=False,
        )

    @property
    def panel_row(self):
        if self._panel_row is None:
            if self._panel_row_active:
                self._panel_row = Row(self.view, self.param_control)
            else:
                self._panel_row = Row()
        return self._panel_row

    @panel_row.setter
    def panel_row(self, value: bool):
        self._panel_row_active = value
        if self._panel_row:
            if value:
                self._panel_row[0] = self.view
                self._panel_row[1] = self.param_control
            else:
                self._panel_row[0] = None
                self._panel_row[1] = None
