#!/usr/bin/env python3
"""test_alphatrend_port - plain python (no pytest): python test_alphatrend_port.py"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alphatrend_port as at
import pine_common as pc


def synth(n=60):
    c = [100 + 6 * math.sin(i * 0.5) + 0.05 * i for i in range(n)]
    h = [c[i] + 1 + 0.2 * (i % 3) for i in range(n)]
    l = [c[i] - 1 - 0.1 * (i % 4) for i in range(n)]
    v = [100 + 10 * (i % 5) + 3 * (i % 7) for i in range(n)]
    return h, l, c, v


def ref(h, l, c, v, coeff, ap, novol):
    n = len(c)
    tr = [None] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]   # ta.tr variable: na on bar 0
    atr = [None] * n
    for i in range(ap, n):
        atr[i] = sum(tr[i - ap + 1:i + 1]) / ap
    cond = [False] * n
    if novol:
        gains = [None] + [max(c[i] - c[i - 1], 0) for i in range(1, n)]
        losses = [None] + [max(c[i - 1] - c[i], 0) for i in range(1, n)]
        ru = rd = None
        for i in range(ap, n):
            ru = sum(gains[1:ap + 1]) / ap if i == ap else (gains[i] + (ap - 1) * ru) / ap
            rd = sum(losses[1:ap + 1]) / ap if i == ap else (losses[i] + (ap - 1) * rd) / ap
            rsi = 100.0 if rd == 0 else (0.0 if ru == 0 else 100 - 100 / (1 + ru / rd))
            cond[i] = rsi >= 50
    else:
        tp = [(h[i] + l[i] + c[i]) / 3 for i in range(n)]
        up_t, dn_t = [], []
        for i in range(n):
            chg = None if i == 0 else tp[i] - tp[i - 1]
            up_t.append(v[i] * (0 if (chg is not None and chg <= 0) else tp[i]))
            dn_t.append(v[i] * (0 if (chg is not None and chg >= 0) else tp[i]))
        for i in range(ap - 1, n):
            u, lo = sum(up_t[i - ap + 1:i + 1]), sum(dn_t[i - ap + 1:i + 1])
            if lo == 0:
                cond[i] = u != 0
            else:
                cond[i] = 100 - 100 / (1 + u / lo) >= 50
    a = [None] * n
    for i in range(n):
        if atr[i] is None:
            continue
        prev = 0.0 if i == 0 or a[i - 1] is None else a[i - 1]
        upT, dnT = l[i] - atr[i] * coeff, h[i] + atr[i] * coeff
        a[i] = (prev if upT < prev else upT) if cond[i] else (prev if dnT > prev else dnT)
    buy_raw = [i >= 3 and a[i] is not None and a[i - 2] is not None and a[i - 1] is not None and a[i - 3] is not None
               and a[i] > a[i - 2] and a[i - 1] <= a[i - 3] for i in range(n)]
    sell_raw = [i >= 3 and a[i] is not None and a[i - 2] is not None and a[i - 1] is not None and a[i - 3] is not None
                and a[i] < a[i - 2] and a[i - 1] >= a[i - 3] for i in range(n)]

    def bs(flags, i):                       # barssince at bar i (None if never)
        for k in range(i, -1, -1):
            if flags[k]:
                return i - k
        return None

    buy, sell = [], []
    for i in range(n):
        k1, k2 = bs(buy_raw, i), bs(sell_raw, i)
        o1 = None
        for k in range(i - 1, -1, -1):
            if buy_raw[k]:
                o1 = i - (k + 1)
                break
        o2 = None
        for k in range(i - 1, -1, -1):
            if sell_raw[k]:
                o2 = i - (k + 1)
                break
        buy.append(bool(buy_raw[i] and o1 is not None and k2 is not None and o1 > k2))
        sell.append(bool(sell_raw[i] and o2 is not None and k1 is not None and o2 > k1))
    return atr, a, buy_raw, sell_raw, buy, sell


def test_hand():
    h, l, c, v = synth()
    for novol in (False, True):
        r = at.alphatrend(h, l, c, v, 1.0, 5, novol)
        atr, a, br, sr, b, s = ref(h, l, c, v, 1.0, 5, novol)
        for i in range(len(c)):
            for name, x, y in (("atr", r["atr"][i], atr[i]), ("at", r["alphatrend"][i], a[i])):
                assert (y is None and math.isnan(x)) or (y is not None and abs(x - y) < 1e-9), (novol, name, i, x, y)
        assert list(r["buy_raw"]) == br and list(r["sell_raw"]) == sr, novol
        assert list(r["buy"]) == b and list(r["sell"]) == s, novol
        print(f"hand check novol={novol}: ok, raw buys={sum(br)} sells={sum(sr)}, filtered buys={sum(b)} sells={sum(s)}")
    # tiny anchor: ap=2 on 4 bars, ATR = mean of two true ranges (bar 0 na)
    r = at.alphatrend([10, 11, 12, 13], [9, 10, 11, 12], [9.5, 10.5, 11.5, 12.5], [1, 1, 1, 1], 1.0, 2, True)
    assert math.isnan(r["atr"][1])
    assert abs(r["atr"][2] - (1.5 + 1.5) / 2) < 1e-12   # tr1 = max(1, |11-9.5|, |10-9.5|) = 1.5 ; tr2 = max(1, 1.5, 0.5) = 1.5


def test_truncation(n_bars=300):
    d = pc.load_us100_m5_tail(n_bars)
    for novol in (False, True):
        def fn(m):
            r = at.alphatrend(d["high"][:m], d["low"][:m], d["close"][:m], d["tickvolume"][:m], no_volume_data=novol)
            return {k: r[k] for k in ("atr", "alphatrend", "buy_raw", "sell_raw", "buy", "sell")}
        pc.assert_truncation_invariant(fn, n_bars, atol=1e-9)
    print("truncation invariance: ok (3 cuts x MFI/RSI)")


def test_real():
    d = pc.load_us100_m5_tail(2000)
    for novol in (False, True):
        r = at.alphatrend(d["high"], d["low"], d["close"], d["tickvolume"], no_volume_data=novol)
        print(f"US100 M5 2000 bars {'RSI' if novol else 'MFI(tick)'}: raw buys={int(r['buy_raw'].sum())} sells={int(r['sell_raw'].sum())} "
              f"filtered buys={int(r['buy'].sum())} sells={int(r['sell'].sum())} last AT={r['alphatrend'][-1]:.2f} AT[2]={r['alphatrend_2'][-1]:.2f}")


if __name__ == "__main__":
    test_hand()
    test_truncation()
    test_real()
    print("ALL OK")
