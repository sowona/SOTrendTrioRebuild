#!/usr/bin/env python3
r"""supertrend_port - TradingView "SuperTrend" by KivancOzbilgic (open source, tradingview.com/script/r6dAP7yi-SuperTrend/).
The script page could not be read through the fetch tool (source behind the editor link); the code below is the well-known
published Pine (v4/v5 identical logic), reproduced from memory and checked against the page description (ATR period 10,
multiplier 3.0, src hl2, changeATR true -> atr(), false -> sma(tr)):

    atr2 = sma(tr, Periods);  atr = changeATR ? atr(Periods) : atr2
    up  = src - Multiplier*atr;  up1 = nz(up[1], up);  up := close[1] > up1 ? max(up, up1) : up
    dn  = src + Multiplier*atr;  dn1 = nz(dn[1], dn);  dn := close[1] < dn1 ? min(dn, dn1) : dn
    trend = 1;  trend := nz(trend[1], trend)
    trend := trend == -1 and close > dn1 ? 1 : trend == 1 and close < up1 ? -1 : trend
    buySignal = trend == 1 and trend[1] == -1;  sellSignal = trend == -1 and trend[1] == 1

Notes: up1 / dn1 are the previous bar's FINAL (ratcheted) values. Warm-up: up/dn are na until the ATR exists, trend stays 1
(na comparisons are false). atr() = rma(tr, n) with tr bar 0 = high - low; sma(tr): `tr_first_bar_na` False = v4 `tr`
(bar 0 = high - low), True = v5 `ta.tr` variable (bar 0 na, SMA starts one bar later) - only the first n bars differ.
The up line is drawn while trend == 1, the down line while trend == -1 (outputs `up_line` / `dn_line` mask that).
Standalone: numpy + pine_common.
"""
import math

import numpy as np

import pine_common as pc

PERIODS, MULT, CHANGE_ATR = 10, 3.0, True


def supertrend(high, low, close, periods=PERIODS, multiplier=MULT, source=None, change_atr=CHANGE_ATR,
               tr_first_bar_na=False):
    """source: series for `src` (default hl2). Returns dict: atr, up, dn (final ratcheted), trend (+1/-1), up_line,
    dn_line (NaN when not the active side), buy, sell (bool)."""
    h, l, c = pc.arr(high), pc.arr(low), pc.arr(close)
    n = len(c)
    src = (h + l) / 2.0 if source is None else pc.arr(source)
    if change_atr:
        atr = pc.rma(pc.tr(h, l, c, True), periods)
    else:
        atr = pc.sma(pc.tr(h, l, c, not tr_first_bar_na), periods)
    up = np.full(n, np.nan)
    dn = np.full(n, np.nan)
    trend = np.ones(n)
    for i in range(n):
        u = src[i] - multiplier * atr[i]
        d = src[i] + multiplier * atr[i]
        u1 = u if i == 0 or math.isnan(up[i - 1]) else up[i - 1]
        d1 = d if i == 0 or math.isnan(dn[i - 1]) else dn[i - 1]
        cp = c[i - 1] if i > 0 else np.nan
        if cp > u1:
            u = max(u, u1)
        if cp < d1:
            d = min(d, d1)
        up[i], dn[i] = u, d
        t = trend[i - 1] if i > 0 else 1.0
        if t == -1 and c[i] > d1:
            t = 1.0
        elif t == 1 and c[i] < u1:
            t = -1.0
        trend[i] = t
    pt = pc.shift(trend, 1)
    buy = (trend == 1) & (pt == -1)
    sell = (trend == -1) & (pt == 1)
    return {"atr": atr, "up": up, "dn": dn, "trend": trend,
            "up_line": np.where(trend == 1, up, np.nan), "dn_line": np.where(trend == -1, dn, np.nan),
            "buy": buy, "sell": sell}
