#!/usr/bin/env python3
"""test_dmi_port - plain python (no pytest): python test_dmi_port.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dmi_port as dp
import pine_common as pc


def synth(n=60):
    c = [100 + 6 * math.sin(i * 0.4) + 0.2 * i for i in range(n)]
    h = [c[i] + 1 + 0.3 * (i % 3) for i in range(n)]
    l = [c[i] - 1 - 0.2 * (i % 4) for i in range(n)]
    return h, l, c


def r_rma(x, n):
    """x: list with None; SMA seed over the first n valid values."""
    out = [None] * len(x)
    f = next(i for i, v in enumerate(x) if v is not None)
    for i in range(f + n - 1, len(x)):
        out[i] = sum(x[f:f + n]) / n if i == f + n - 1 else (x[i] + (n - 1) * out[i - 1]) / n
    return out


def ref(h, l, c, di, sm):
    n = len(c)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    pdm, mdm = [None], [None]
    for i in range(1, n):
        up, down = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm.append(up if (up > down and up > 0) else 0.0)
        mdm.append(down if (down > up and down > 0) else 0.0)
    trur, rp, rm = r_rma(tr, di), r_rma(pdm, di), r_rma(mdm, di)
    plus, minus = [None] * n, [None] * n
    for i in range(n):
        if trur[i] is not None and rp[i] is not None:
            plus[i], minus[i] = 100 * rp[i] / trur[i], 100 * rm[i] / trur[i]
    dx = [None if plus[i] is None else abs(plus[i] - minus[i]) / (1 if plus[i] + minus[i] == 0 else plus[i] + minus[i])
          for i in range(n)]
    adx = [None if v is None else 100 * v for v in r_rma(dx, sm)]
    return plus, minus, adx


def test_hand():
    h, l, c = synth()
    r = dp.dmi(h, l, c, 7, 5)
    plus, minus, adx = ref(h, l, c, 7, 5)
    for i in range(len(c)):
        for name, x, y in (("plus", r["plus"][i], plus[i]), ("minus", r["minus"][i], minus[i]), ("adx", r["adx"][i], adx[i])):
            assert (y is None and math.isnan(x)) or (y is not None and abs(x - y) < 1e-9), (name, i, x, y)
    # anchor: first DI value at bar 7 (rma seeded over the 7 DM values of bars 1..7 and the 7 TRs of bars 0..6 -> bar 6 trur, bar 7 dm)
    first = next(i for i, v in enumerate(plus) if v is not None)
    assert first == 7 and not math.isnan(r["plus"][7]) and math.isnan(r["plus"][6])
    print("hand check: ok, first DI bar =", first, "first ADX bar =", next(i for i, v in enumerate(adx) if v is not None))


def test_truncation(n_bars=300):
    d = pc.load_us100_m5_tail(n_bars)
    pc.assert_truncation_invariant(lambda m: dp.dmi(d["high"][:m], d["low"][:m], d["close"][:m]), n_bars, atol=1e-9)
    print("truncation invariance: ok (3 cuts)")


def test_real():
    d = pc.load_us100_m5_tail(2000)
    r = dp.dmi(d["high"], d["low"], d["close"])
    x = r["plus"] > r["minus"]
    flips = int((x[1:] != x[:-1]).sum())
    print(f"US100 M5 last 2000 bars: DI+/DI- crossings={flips} last DI+={r['plus'][-1]:.2f} DI-={r['minus'][-1]:.2f} ADX={r['adx'][-1]:.2f}")


if __name__ == "__main__":
    test_hand()
    test_truncation()
    test_real()
    print("ALL OK")
