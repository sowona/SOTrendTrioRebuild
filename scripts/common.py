"""find_holes: the one helper b11_stage0.py imports (`from common import find_holes`).

Copied unchanged from the author's shared research helpers (SOMultiMAsPullbackRider/Research/scripts/common.py, see
indicators/PROVENANCE.md); the rest of that module (its own paths and loaders) is not used by B11 and is not included.
"""
import numpy as np
import pandas as pd


def find_holes(idx, max_h=72):
    """Holes = consecutive bar opens whose gap, minus the Saturday/Sunday (UTC) time it contains, exceeds max_h hours
    (holiday weekends of ~3 calendar days are not holes). Returns [(last open before, first open after, days)]."""
    t = idx.to_numpy("datetime64[ns]")
    out = []
    for k in np.flatnonzero(np.diff(t) > np.timedelta64(max_h, "h")):
        a, b = pd.Timestamp(t[k]), pd.Timestamp(t[k + 1])
        wk = pd.Timedelta(0)
        d = a.normalize()
        while d < b:
            if d.dayofweek >= 5:
                wk += min(b, d + pd.Timedelta(days=1)) - max(a, d)
            d += pd.Timedelta(days=1)
        if (b - a - wk) > pd.Timedelta(hours=max_h):
            out.append((a, b, (b - a - wk) / pd.Timedelta(days=1)))
    return out
