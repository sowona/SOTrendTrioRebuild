#!/usr/bin/env python3
r"""ultimate_ma_port - ChrisMoody "CM_Ultimate_MA_MTF" (V2 source READ from the MQL5 mirror
https://c.mql5.com/21/297/CM_Ultimate_MA_MTF_V2.txt ; TradingView pages tradingview.com/script/8KVcQiJM-CM-Ultimate-MA-MTF-V2 and
.../bkvQ5hNF-CM-Ultimate-MA-MTF-V4 are not readable through the fetch tool; V4 offers the same eight averages).

Ported (first moving average only; call twice for the optional 2nd MA with its own length / type):
    avg = atype==1 sma | 2 ema | 3 wma | 4 hullma | 5 vwma | 6 rma | 7 tema | 8 Tilson T3        (src = close)
    hullma = wma(2*wma(src, len/2) - wma(src, len), round(sqrt(len)))
    tema   = 3*(ema1 - ema2) + ema3
    T3     : f = factorT3 * 0.10;  gd(x) = ema(x,len)*(1+f) - ema(ema(x,len),len)*f;  t3 = gd(gd(gd(src)))   (the script's own
             formula, NOT the Tillson/Brown 6-EMA form)
    vwma   = sma(src*volume, len) / sma(volume, len)
    ma_up = out >= out[smoothe];  ma_down = out < out[smoothe]      (default smoothe 2; col = cc ? up lime : down red : aqua)
Colour state: +1 (lime, rising), -1 (red, falling), 0 (aqua = na on the first `smoothe` bars, or change_color False).
`turn_up` / `turn_down`: state flips -1 -> +1 / +1 -> -1 against the previous bar (neutral bars never signal).
Not ported: security() MTF (the caller passes the HTF bars and projects the result), bar-cross highlights, 2nd-MA cross dots.
Pine details: len/2 truncated to int, round() = floor(x + 0.5); ema seeded with the first source value, rma with an SMA seed
(pine_common). `volume` only needed for atype 5 (pass TickVolume, tick-weighted).
Script bugs of the 2nd MA only (its TEMA uses the 1st MA's ema1..3, its T3 first stage uses the 1st MA's length) are not reproduced.
Standalone: numpy + pine_common.
"""
import math

import numpy as np

import pine_common as pc

LEN, ATYPE, FACTOR_T3, SMOOTHE, CC = 20, 1, 7, 2, True
TYPES = {1: "SMA", 2: "EMA", 3: "WMA", 4: "HullMA", 5: "VWMA", 6: "RMA", 7: "TEMA", 8: "TilsonT3"}


def hull(src, length):
    return pc.wma(2 * pc.wma(src, int(length / 2)) - pc.wma(src, length), pc.pine_round(math.sqrt(length)))


def tema(src, length):
    e1 = pc.ema(src, length)
    e2 = pc.ema(e1, length)
    e3 = pc.ema(e2, length)
    return 3 * (e1 - e2) + e3


def tilson_t3(src, length, factor_t3=FACTOR_T3):
    f = factor_t3 * 0.10

    def gd(x):
        e = pc.ema(x, length)
        return e * (1 + f) - pc.ema(e, length) * f

    return gd(gd(gd(src)))


def vwma(src, volume, length):
    return pc.sma(pc.arr(src) * pc.arr(volume), length) / pc.sma(volume, length)


def ma_value(src, length=LEN, atype=ATYPE, factor_t3=FACTOR_T3, volume=None):
    src = pc.arr(src)
    if atype == 1:
        return pc.sma(src, length)
    if atype == 2:
        return pc.ema(src, length)
    if atype == 3:
        return pc.wma(src, length)
    if atype == 4:
        return hull(src, length)
    if atype == 5:
        if volume is None:
            raise ValueError("atype 5 (VWMA) needs the volume series (TickVolume, tick-weighted)")
        return vwma(src, volume, length)
    if atype == 6:
        return pc.rma(src, length)
    if atype == 7:
        return tema(src, length)
    if atype == 8:
        return tilson_t3(src, length, factor_t3)
    raise ValueError("atype must be 1..8")


def ultimate_ma(close, length=LEN, atype=ATYPE, factor_t3=FACTOR_T3, smoothe=SMOOTHE, change_color=CC, volume=None):
    """Returns dict: ma, state (+1 lime / -1 red / 0 aqua), turn_up, turn_down (bool)."""
    out = ma_value(close, length, atype, factor_t3, volume)
    prev = pc.shift(out, smoothe)
    with np.errstate(invalid="ignore"):
        up = out >= prev
        dn = out < prev
    state = np.where(up, 1, np.where(dn, -1, 0)) if change_color else np.zeros(len(out), int)
    ps = np.concatenate([[0], state[:-1]]) if len(state) else state
    return {"ma": out, "state": state.astype(int), "turn_up": (state == 1) & (ps == -1),
            "turn_down": (state == -1) & (ps == 1)}
