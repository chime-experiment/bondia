from panel import Row, Param
import param
import holoviews as hv
import numpy as np

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


def hv_image_with_gaps(x, y, z, gap_scale=0.1, opts=None, *args, **kwargs):
    """Produce an overlay with images accounting for gaps in the data.

    Parameters
    ----------
    x, y : np.ndarray[:]
        Location of pixel centres in each direction
    z : np.ndarray[:, :]
        Pixel (z-)values
    gap_scale : float, optional
        If there is an extra gap between pixels of this amount times the nominal
        separation, consider this a gap in the data.
    opts : dict


    Returns
    -------
    overlay : list
        holoviews Overlay with an Image for each uninterruptedly sampled section.
    """

    def _find_splits(ax):
        d = np.diff(ax)
        md = np.median(d)

        ranges = []

        last_cut = 0
        for ii, di in enumerate(d):
            if np.abs(di - md) > np.abs(gap_scale * md):
                ranges.append((last_cut, ii + 1))
                last_cut = ii + 1

        ranges.append((last_cut, len(ax)))
        return ranges

    if opts is None:
        opts = {}
    overlay = None
    x_splits = _find_splits(x)
    y_splits = _find_splits(y)
    for xs, xe in x_splits:
        for ys, ye in y_splits:
            xa = x[xs:xe]
            ya = y[ys:ye]
            ca = z[ys:ye, xs:xe]

            img = hv.Image(
                (xa, ya, ca),
                datatype=["image", "grid"],
                *args,
                **kwargs,
            ).opts(**opts)

            # Create overlay
            if overlay is None:
                overlay = img
            else:
                overlay *= img

    return overlay