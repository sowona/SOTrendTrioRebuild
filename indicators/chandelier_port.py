#!/usr/bin/env python3
r"""chandelier_port - "Chandelier Exit" by Alex Orekhov (everget), Pine v4, GPL-3.0. Source READ in full from the MQL5 mirror
https://c.mql5.com/21/402/CE.txt (original: everget's "Chandelier Exit" on TradingView). Ported exactly:

    atr = mult * atr(length)                                   (atr() = rma(tr, length), tr bar 0 = high - low)
    longStop  = (useClose ? highest(close, length) : highest(length)) - atr     (highest(length) = highest of high)
    longStopPrev = nz(longStop[1], longStop);  longStop := close[1] > longStopPrev ? max(longStop, longStopPrev) : longStop
    shortStop = (useClose ? lowest(close, length) : lowest(length)) + atr       (lowest(length) = lowest of low)
    shortStopPrev = nz(shortStop[1], shortStop);  shortStop := close[1] < shortStopPrev ? min(shortStop, shortStopPrev) : shortStop
    var int dir = 1;  dir := close > shortStopPrev ? 1 : close < longStopPrev ? -1 : dir
    buySignal = dir == 1 and dir[1] == -1;  sellSignal = dir == -1 and dir[1] == 1

[1] of a reassigned variable is the previous bar's FINAL (ratcheted) value; both Prev values are therefore the previous finals.
Standalone: numpy + pine_common.
"""
import math

import numpy as np

import pine_common as pc

LENGTH, MULT, USE_CLOSE = 22, 3.0, True


def chandelier(high, low, close, length=LENGTH, mult=MULT, use_close=USE_CLOSE):
    """Returns dict: long_stop, short_stop (final ratcheted values), dir (+1/-1), long_line / short_line (plotted side only),
    buy, sell (bool)."""
    h, l, c = pc.arr(high), pc.arr(low), pc.arr(close)
    n = len(c)
    atr = mult * pc.rma(pc.tr(h, l, c, True), length)
    hh = pc.highest(c if use_close else h, length)
    ll = pc.lowest(c if use_close else l, length)
    ls_raw, ss_raw = hh - atr, ll + atr
    ls = np.full(n, np.nan)
    ss = np.full(n, np.nan)
    d = np.ones(n)
    cur = 1.0
    for i in range(n):
        lsp = ls_raw[i] if i == 0 or math.isnan(ls[i - 1]) else ls[i - 1]
        ssp = ss_raw[i] if i == 0 or math.isnan(ss[i - 1]) else ss[i - 1]
        cp = c[i - 1] if i > 0 else np.nan
        v = ls_raw[i]
        if cp > lsp:
            v = max(v, lsp)
        ls[i] = v
        w = ss_raw[i]
        if cp < ssp:
            w = min(w, ssp)
        ss[i] = w
        if c[i] > ssp:
            cur = 1.0
        elif c[i] < lsp:
            cur = -1.0
        d[i] = cur
    pd_ = pc.shift(d, 1)
    return {"long_stop": ls, "short_stop": ss, "dir": d,
            "long_line": np.where(d == 1, ls, np.nan), "short_line": np.where(d == 1, np.nan, ss),
            "buy": (d == 1) & (pd_ == -1), "sell": (d == -1) & (pd_ == 1)}
