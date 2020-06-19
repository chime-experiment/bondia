from panel import Row


class BondiaPlot:
    def __init__(self, name: str, activated: bool = True):
        self._name = name
        self._id = name.lower().replace(" ", "_")
        self._panel_row_active = activated
        self._panel_row = None

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def title(self):
        return f"## {self._name}"

    @property
    def panel_row(self):
        if self._panel_row is None:
            if self._panel_row_active:
                self._panel_row = Row(self.panel(), self.param)
            else:
                self._panel_row = Row()
        return self._panel_row

    @panel_row.setter
    def panel_row(self, value: bool):
        self._panel_row_active = value
        if self._panel_row:
            if value:
                self._panel_row[0] = self.panel()
                self._panel_row[1] = self.param
            else:
                self._panel_row[0] = None
                self._panel_row[1] = None
