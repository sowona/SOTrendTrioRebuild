#!/usr/bin/env python3
r"""slingshot_port - ChrisMoody "CM Sling Shot System": only the trend EMAs (fast 38, slow 62, close) and the state
fast > slow. Source page not read (TradingView editor source not exposed by the fetch tool); the EMA pair and defaults are
those of the published script (`emaSlow = ema(close, 62)`, `emaFast = ema(close, 38)`; its trend test is `emaFast >= emaSlow`
as recalled). The request says fast > slow, so `state` is strict (>) and `state_ge` is the >= form; they differ only on
exact equality.
ema seeded with the first close (pine_common). Standalone: numpy + pine_common.
"""
import numpy as np

import pine_common as pc

FAST, SLOW = 38, 62


def slingshot(close, fast=FAST, slow=SLOW):
    c = pc.arr(close)
    f, s = pc.ema(c, fast), pc.ema(c, slow)
    with np.errstate(invalid="ignore"):
        return {"ema_fast": f, "ema_slow": s, "state": f > s, "state_ge": f >= s}
