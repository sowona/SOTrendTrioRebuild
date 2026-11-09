#!/usr/bin/env python3
"""test_supertrend_port - plain python (no pytest): python test_supertrend_port.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pine_common as pc
import supertrend_port as sp


def synth(n=40):
    c = [100 + 15 * math.sin(i * 0.5) + 0.3 * i for i in range(n)]
    h = [c[i] + 1 + 0.2 * (i % 3) for i in range(n)]
    l = [c[i] - 1 - 0.1 * (i % 4) for i in range(n)]
    return h, l, c


def ref(h, l, c, per, mult, change_atr):
    """Scalar bar-by-bar Pine v4 SuperTrend (None = na)."""
    n = len(c)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    atr = [None] * n
    for i in range(per - 1, n):
        if change_atr:
            atr[i] = sum(tr[:per]) / per if i == per - 1 else (atr[i - 1] * (per - 1) + tr[i]) / per
        else:
            atr[i] = sum(tr[i - per + 1:i + 1]) / per
    up, dn, tre = [None] * n, [None] * n, [1] * n
    for i in range(n):
        src = (h[i] + l[i]) / 2
        u = None if atr[i] is None else src - mult * atr[i]
        d = None if atr[i] is None else src + mult * atr[i]
        u1 = u if (i == 0 or up[i - 1] is None) else up[i - 1]
        d1 = d if (i == 0 or dn[i - 1] is None) else dn[i - 1]
        if i > 0 and u1 is not None and c[i - 1] > u1:
            u = max(u, u1)
        if i > 0 and d1 is not None and c[i - 1] < d1:
            d = min(d, d1)
        up[i], dn[i] = u, d
        t = tre[i - 1] if i else 1
        if t == -1 and d1 is not None and c[i] > d1:
            t = 1
        elif t == 1 and u1 is not None and c[i] < u1:
            t = -1
        tre[i] = t
    return atr, up, dn, tre


def test_hand():
    h, l, c = synth()
    for change_atr in (True, False):
        r = sp.supertrend(h, l, c, 5, 1.0, change_atr=change_atr)
        atr, up, dn, tre = ref(h, l, c, 5, 1.0, change_atr)
        for name, a, b in (("atr", r["atr"], atr), ("up", r["up"], up), ("dn", r["dn"], dn)):
            for i, (x, y) in enumerate(zip(a, b)):
                assert (y is None and math.isnan(x)) or (y is not None and abs(x - y) < 1e-9), (change_atr, name, i, x, y)
        assert list(r["trend"]) == tre, (change_atr, list(r["trend"]), tre)
        flips = sum(1 for i in range(1, len(tre)) if tre[i] != tre[i - 1])
        assert int(r["buy"].sum() + r["sell"].sum()) == flips
        print(f"hand check change_atr={change_atr}: ok, flips on synthetic = {flips}")
    # direct numeric anchor: bar 9 ATR = mean of the first 10 true ranges
    tr9 = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, 10)]
    r = sp.supertrend(h, l, c)
    assert abs(r["atr"][9] - sum(tr9) / 10) < 1e-12 and math.isnan(r["atr"][8])


def test_truncation(n_bars=300):
    d = pc.load_us100_m5_tail(n_bars)

    def fn(m):
        r = sp.supertrend(d["high"][:m], d["low"][:m], d["close"][:m])
        return {k: r[k] for k in ("atr", "up", "dn", "trend", "buy", "sell")}

    pc.assert_truncation_invariant(fn, n_bars)
    print("truncation invariance: ok (3 cuts)")


def test_real():
    d = pc.load_us100_m5_tail(2000)
    r = sp.supertrend(d["high"], d["low"], d["close"])
    flips = int(r["buy"].sum() + r["sell"].sum())
    print(f"US100 M5 last 2000 bars: buys={int(r['buy'].sum())} sells={int(r['sell'].sum())} flips={flips}")
    print("  last 3: trend", r["trend"][-3:], "up", np.round(r["up"][-3:], 2), "dn", np.round(r["dn"][-3:], 2))
    assert flips > 0


if __name__ == "__main__":
    test_hand()
    test_truncation()
    test_real()
    print("ALL OK")
