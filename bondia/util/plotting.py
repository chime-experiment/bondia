"""Utilities for plotting."""

import holoviews as hv
import numpy as np


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
