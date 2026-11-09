#!/usr/bin/env python3
r"""alphatrend_port - "AlphaTrend" by KivancOzbilgic (tradingview.com/script/o50NYLAZ-AlphaTrend/, Pine v5). The page does not
expose the source through the fetch tool; reproduced from memory plus search fragments (PineConnector copy:
`novolumedata ? rsi(src,14) >= 50 : mfi(hlc3,14) >= 50`, `buySignalk = crossover(AlphaTrend, AlphaTrend[2])`). Pine as ported:

    ATR = ta.sma(ta.tr, AP)               (NOTE: SMA of true range, not Wilder; ta.tr variable)
    upT = low - ATR*coeff;  downT = high + ATR*coeff
    AlphaTrend := (novolumedata ? rsi(src, AP) >= 50 : mfi(hlc3, AP) >= 50) ?
                      (upT < nz(AlphaTrend[1]) ? nz(AlphaTrend[1]) : upT) :
                      (downT > nz(AlphaTrend[1]) ? nz(AlphaTrend[1]) : downT)
    buySignalk = crossover(AlphaTrend, AlphaTrend[2]);  sellSignalk = crossunder(AlphaTrend, AlphaTrend[2])
    K1 = barssince(buySignalk); K2 = barssince(sellSignalk); O1 = barssince(buySignalk[1]); O2 = barssince(sellSignalk[1])
    buy  = buySignalk  and O1 > K2        (plotted at AlphaTrend[2]*0.9999; alertcondition(buySignalk and O1 > K2))
    sell = sellSignalk and O2 > K1
UNCERTAIN: the O1 / O2 / K1 / K2 filter (alternate buys and sells) is recalled from memory, not read; both the raw crossovers
(`buy_raw`, `sell_raw`) and the filtered signals (`buy`, `sell`) are returned. Pine na rule kept: `na > x` is False, so the
filter suppresses a signal until a previous opposite and same-side signal both exist.
Quirks kept: nz(AlphaTrend[1]) = 0 on the first valid bar (a first valid bar on the downT side gives AlphaTrend = 0 until the
MFI >= 50 branch fires) - give the caller a warm-up. mfi / rsi condition NaN -> False (downT branch).
`volume` = TickVolume (tick-weighted) for the MFI path. tr: ta.tr variable (v5), bar 0 na unless `tr_first_bar_na=False`.
Standalone: numpy + pine_common.
"""
import math

import numpy as np

import pine_common as pc

COEFF, AP, NO_VOLUME_DATA = 1.0, 14, False


def barssince(flag):
    """ta.barssince: bars since the condition was last true (0 on the bar itself), NaN before the first true."""
    out = np.full(len(flag), np.nan)
    last = None
    for i, f in enumerate(flag):
        if f:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def alphatrend(high, low, close, volume=None, coeff=COEFF, ap=AP, no_volume_data=NO_VOLUME_DATA, source=None,
               tr_first_bar_na=True):
    """source default close (RSI path only). volume required unless no_volume_data."""
    h, l, c = pc.arr(high), pc.arr(low), pc.arr(close)
    n = len(c)
    src = c if source is None else pc.arr(source)
    atr = pc.sma(pc.tr(h, l, c, not tr_first_bar_na), ap)
    up_t, dn_t = l - atr * coeff, h + atr * coeff
    if no_volume_data:
        cond = pc.rsi(src, ap) >= 50
    else:
        if volume is None:
            raise ValueError("MFI path needs the volume series (TickVolume, tick-weighted)")
        cond = pc.mfi((h + l + c) / 3.0, volume, ap) >= 50
    at = np.full(n, np.nan)
    for i in range(n):
        prev = 0.0 if i == 0 or math.isnan(at[i - 1]) else at[i - 1]
        if cond[i]:
            at[i] = prev if up_t[i] < prev else up_t[i]
        else:
            at[i] = prev if dn_t[i] > prev else dn_t[i]
    at2 = pc.shift(at, 2)
    buy_raw, sell_raw = pc.crossover(at, at2), pc.crossunder(at, at2)
    k1, k2 = barssince(buy_raw), barssince(sell_raw)
    o1 = barssince(np.concatenate([[False], buy_raw[:-1]]))
    o2 = barssince(np.concatenate([[False], sell_raw[:-1]]))
    with np.errstate(invalid="ignore"):
        buy = buy_raw & (o1 > k2)
        sell = sell_raw & (o2 > k1)
    return {"atr": atr, "alphatrend": at, "alphatrend_2": at2, "buy_raw": buy_raw, "sell_raw": sell_raw,
            "buy": buy, "sell": sell}
