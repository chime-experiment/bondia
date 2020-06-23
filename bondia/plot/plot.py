from panel import Column, Row


class BondiaPlot:
    def __init__(self, name: str, activated: bool = True):
        self._name = name
        self._id = name.lower().replace(" ", "_")
        self._panel_col_active = activated
        self._panel_col = None

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
        if self._panel_col is None:
            if self._panel_col_active:

                self._panel_col = Column(
                    self.title, Row(self.view, self.param), width_policy="max"
                )
            else:
                self._panel_col = Column(None, Row())
        return self._panel_col

    @panel_row.setter
    def panel_row(self, value: bool):
        self._panel_col_active = value
        if self._panel_col:
            if value:
                self._panel_col[0] = self.title
                self._panel_col[1][0] = self.view
                self._panel_col[1][1] = self.param
            else:
                self._panel_col[0] = None
                self._panel_col[1][0] = None
                self._panel_col[1][1] = None
