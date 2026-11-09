#!/usr/bin/env python3
"""test_chandelier_port - plain python (no pytest): python test_chandelier_port.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chandelier_port as ce
import pine_common as pc


def synth(n=60):
    c = [100 + 8 * math.sin(i * 0.45) + 0.1 * i for i in range(n)]
    h = [c[i] + 1 + 0.2 * (i % 3) for i in range(n)]
    l = [c[i] - 1 - 0.1 * (i % 4) for i in range(n)]
    return h, l, c


def ref(h, l, c, length, mult, use_close):
    n = len(c)
    tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    atr = [None] * n
    for i in range(length - 1, n):
        atr[i] = sum(tr[:length]) / length if i == length - 1 else (atr[i - 1] * (length - 1) + tr[i]) / length
    ls, ss, d = [None] * n, [None] * n, [1] * n
    for i in range(n):
        if i < length - 1:
            continue
        hh = max((c if use_close else h)[i - length + 1:i + 1])
        ll = min((c if use_close else l)[i - length + 1:i + 1])
        lraw, sraw = hh - mult * atr[i], ll + mult * atr[i]
        lp = lraw if ls[i - 1] is None else ls[i - 1]
        sp = sraw if ss[i - 1] is None else ss[i - 1]
        ls[i] = max(lraw, lp) if c[i - 1] > lp else lraw
        ss[i] = min(sraw, sp) if c[i - 1] < sp else sraw
        d[i] = 1 if c[i] > sp else (-1 if c[i] < lp else d[i - 1])
    return ls, ss, d


def test_hand():
    h, l, c = synth()
    for use_close in (True, False):
        r = ce.chandelier(h, l, c, 8, 2.0, use_close)
        ls, ss, d = ref(h, l, c, 8, 2.0, use_close)
        for i in range(len(c)):
            for name, a, b in (("long", r["long_stop"][i], ls[i]), ("short", r["short_stop"][i], ss[i])):
                assert (b is None and math.isnan(a)) or (b is not None and abs(a - b) < 1e-9), (use_close, name, i, a, b)
            assert r["dir"][i] == d[i], (use_close, i)
        flips = sum(1 for i in range(1, len(d)) if d[i] != d[i - 1])
        assert int(r["buy"].sum() + r["sell"].sum()) == flips
        print(f"hand check use_close={use_close}: ok, flips on synthetic = {flips}")
    # ratchet: while dir is long and price rises, long stop never decreases
    r = ce.chandelier(h, l, c, 8, 2.0, True)
    for i in range(9, len(c)):
        if r["dir"][i] == 1 and r["dir"][i - 1] == 1 and c[i - 1] > r["long_stop"][i - 1]:
            assert r["long_stop"][i] >= r["long_stop"][i - 1] - 1e-12


def test_truncation(n_bars=300):
    d = pc.load_us100_m5_tail(n_bars)

    def fn(m):
        r = ce.chandelier(d["high"][:m], d["low"][:m], d["close"][:m])
        return {k: r[k] for k in ("long_stop", "short_stop", "dir", "buy", "sell")}

    pc.assert_truncation_invariant(fn, n_bars)
    print("truncation invariance: ok (3 cuts)")


def test_real():
    d = pc.load_us100_m5_tail(2000)
    r = ce.chandelier(d["high"], d["low"], d["close"])
    print(f"US100 M5 last 2000 bars: buys={int(r['buy'].sum())} sells={int(r['sell'].sum())}")
    print("  last 3: dir", r["dir"][-3:], "long", np.round(r["long_stop"][-3:], 2), "short", np.round(r["short_stop"][-3:], 2))
    assert r["buy"].sum() + r["sell"].sum() > 0


if __name__ == "__main__":
    test_hand()
    test_truncation()
    test_real()
    print("ALL OK")
