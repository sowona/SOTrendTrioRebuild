#!/usr/bin/env python3
"""test_ultimate_ma_port - plain python (no pytest): python test_ultimate_ma_port.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pine_common as pc
import ultimate_ma_port as um


def synth(n=40):
    c = [100 + 5 * math.sin(i * 0.7) + 0.3 * i for i in range(n)]
    v = [100 + 10 * (i % 5) for i in range(n)]
    return c, v


# ---- scalar references (lists, plain loops) ----
def r_sma(x, n):
    return [None if i < n - 1 else sum(x[i - n + 1:i + 1]) / n for i in range(len(x))]


def r_ema(x, n):
    a, out = 2 / (n + 1), []
    for i, v in enumerate(x):
        out.append(v if i == 0 else a * v + (1 - a) * out[-1])
    return out


def r_wma(x, n):
    out = []
    for i in range(len(x)):
        if i < n - 1 or any(v is None for v in x[i - n + 1:i + 1]):
            out.append(None)
        else:
            out.append(sum(x[i - n + 1 + k] * (k + 1) for k in range(n)) / (n * (n + 1) / 2))
    return out


def r_rma(x, n):
    out = [None] * len(x)
    for i in range(n - 1, len(x)):
        out[i] = sum(x[:n]) / n if i == n - 1 else (x[i] + (n - 1) * out[i - 1]) / n
    return out


def r_avg(c, v, n, atype, f):
    if atype == 1:
        return r_sma(c, n)
    if atype == 2:
        return r_ema(c, n)
    if atype == 3:
        return r_wma(c, n)
    if atype == 4:
        a, b = r_wma(c, n // 2), r_wma(c, n)
        diff = [None if a[i] is None or b[i] is None else 2 * a[i] - b[i] for i in range(len(c))]
        return r_wma(diff, int(math.floor(math.sqrt(n) + 0.5)))
    if atype == 5:
        pv = [c[i] * v[i] for i in range(len(c))]
        a, b = r_sma(pv, n), r_sma(v, n)
        return [None if a[i] is None else a[i] / b[i] for i in range(len(c))]
    if atype == 6:
        return r_rma(c, n)
    if atype == 7:
        e1 = r_ema(c, n)
        e2 = r_ema(e1, n)
        e3 = r_ema(e2, n)
        return [3 * (e1[i] - e2[i]) + e3[i] for i in range(len(c))]
    ff = f * 0.1
    x = c
    for _ in range(3):
        e = r_ema(x, n)
        ee = r_ema(e, n)
        x = [e[i] * (1 + ff) - ee[i] * ff for i in range(len(c))]
    return x


def test_hand():
    c, v = synth()
    for atype in range(1, 9):
        n = 6
        got = um.ultimate_ma(c, n, atype, 7, 2, True, volume=v)
        exp = r_avg(c, v, n, atype, 7)
        for i, (x, y) in enumerate(zip(got["ma"], exp)):
            assert (y is None and math.isnan(x)) or (y is not None and abs(x - y) < 1e-9), (atype, i, x, y)
        # colour rule: rising / falling against out[smoothe]
        for i in range(len(c)):
            if exp[i] is None or i < 2 or exp[i - 2] is None:
                assert got["state"][i] == 0
            else:
                assert got["state"][i] == (1 if exp[i] >= exp[i - 2] else -1), (atype, i)
        print(f"hand check {um.TYPES[atype]}: ok, turns up={int(got['turn_up'].sum())} down={int(got['turn_down'].sum())}")
    # smoothe=1 on a tiny monotone-then-falling series: SMA(2) of 1,2,3,2,1
    r = um.ultimate_ma([1, 2, 3, 2, 1], 2, 1, smoothe=1)
    assert [round(x, 6) for x in r["ma"][1:]] == [1.5, 2.5, 2.5, 1.5]
    assert list(r["state"]) == [0, 0, 1, 1, -1] and list(r["turn_down"]) == [False] * 4 + [True]


def test_truncation(n_bars=300):
    d = pc.load_us100_m5_tail(n_bars)
    for atype in range(1, 9):
        def fn(m):
            r = um.ultimate_ma(d["close"][:m], 20, atype, 7, 2, True, volume=d["tickvolume"][:m])
            return {k: r[k] for k in ("ma", "state", "turn_up", "turn_down")}
        pc.assert_truncation_invariant(fn, n_bars, atol=1e-9)
    print("truncation invariance: ok (3 cuts x 8 types)")


def test_real():
    d = pc.load_us100_m5_tail(2000)
    for atype in range(1, 9):
        r = um.ultimate_ma(d["close"], 20, atype, volume=d["tickvolume"])
        print(f"US100 M5 2000 bars {um.TYPES[atype]:9s}: turns up={int(r['turn_up'].sum())} down={int(r['turn_down'].sum())} "
              f"last ma={r['ma'][-1]:.2f} state={r['state'][-1]}")


if __name__ == "__main__":
    test_hand()
    test_truncation()
    test_real()
    print("ALL OK")
