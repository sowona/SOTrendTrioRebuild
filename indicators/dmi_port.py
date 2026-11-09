#!/usr/bin/env python3
r"""dmi_port - TradingView built-in ta.dmi(diLength, adxSmoothing) (Pine v5 reference implementation):

    up = ta.change(high);  down = -ta.change(low)
    plusDM  = na(up)   ? na : (up > down and up > 0     ? up   : 0)
    minusDM = na(down) ? na : (down > up and down > 0   ? down : 0)
    trur  = ta.rma(ta.tr, diLength)                         (tr bar 0 = high - low, as in ta.atr)
    plus  = fixnan(100 * ta.rma(plusDM, diLength)  / trur)
    minus = fixnan(100 * ta.rma(minusDM, diLength) / trur)
    sum = plus + minus;  adx = 100 * ta.rma(abs(plus - minus) / (sum == 0 ? 1 : sum), adxSmoothing)
Returns plus (DI+), minus (DI-), adx. fixnan = last non-na value carried forward (leading na stays na).
Recalled from the Pine reference, not fetched. tr bar 0 = high - low by default; `tr_first_bar_na=True` makes it na (the rma
seed then starts one bar later) - only the first ~2n bars differ.
Standalone: numpy + pine_common.
"""
import numpy as np

import pine_common as pc

DI_LEN, ADX_SMOOTH = 14, 14


def _fixnan(x):
    x = pc.arr(x).copy()
    for i in range(1, len(x)):
        if np.isnan(x[i]):
            x[i] = x[i - 1]
    return x


def dmi(high, low, close, di_length=DI_LEN, adx_smoothing=ADX_SMOOTH, tr_first_bar_na=False):
    h, l, c = pc.arr(high), pc.arr(low), pc.arr(close)
    up = pc.change(h)
    down = -pc.change(l)
    with np.errstate(invalid="ignore"):
        plus_dm = np.where(np.isnan(up), np.nan, np.where((up > down) & (up > 0), up, 0.0))
        minus_dm = np.where(np.isnan(down), np.nan, np.where((down > up) & (down > 0), down, 0.0))
    trur = pc.rma(pc.tr(h, l, c, not tr_first_bar_na), di_length)
    with np.errstate(invalid="ignore", divide="ignore"):
        plus = _fixnan(100 * pc.rma(plus_dm, di_length) / trur)
        minus = _fixnan(100 * pc.rma(minus_dm, di_length) / trur)
        s = plus + minus
        adx = 100 * pc.rma(np.abs(plus - minus) / np.where(s == 0, 1.0, s), adx_smoothing)
    return {"plus": plus, "minus": minus, "adx": adx}
