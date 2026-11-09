#!/usr/bin/env python3
r"""pine_common — TradingView Pine built-ins used by the Pine ports (supertrend_port, ultimate_ma_port, slingshot_port,
chandelier_port, alphatrend_port, dmi_port). Numpy only; every function takes and returns float arrays, NaN = Pine `na`.

Pine semantics reproduced (v4/v5):
  * comparisons with na are False (numpy NaN comparisons are too); `nz(x)` = 0 for na.
  * ta.tr(handle_na=True)  (= v4 `tr`, and what ta.atr / ta.dmi use): first bar = high - low.
    ta.tr variable / handle_na=False: first bar na (ta.sma(ta.tr, n) in v5 scripts).
  * ta.sma: NaN until n valid values. ta.rma: first output = SMA of the first n valid values, then
    (src + (n-1) * prev) / n (alpha = 1/n); a leading NaN run shifts the seed (first output at first_valid + n - 1).
  * ta.ema: alpha = 2/(n+1), seeded with the first valid source value (NOT an SMA seed), as the Pine reference code
    `sum := na(sum[1]) ? src : alpha*src + (1-alpha)*nz(sum[1])`.
  * ta.wma: weights n..1, latest bar weight n, divided by n(n+1)/2.
  * ta.rsi: rma(max(change,0)) / rma(-min(change,0)); 100 when the down part is 0, 0 when the up part is 0.
  * ta.mfi(src, n): upper = sum(volume * (change(src) <= 0 ? 0 : src), n), lower = sum(volume * (change(src) >= 0 ? 0 : src), n),
    100 - 100 / (1 + upper / lower). On bar 0 change is na, so both conditions are false and the bar adds volume*src to both.
  * ta.crossover(a, b) = a > b and a[1] <= b[1];  ta.crossunder = a < b and a[1] >= b[1].
Standalone: numpy only (pandas lazily in load_us100_m5_tail).
"""
import math

import numpy as np

DEFAULT_PARQUET = None   # -> <DATA_DIR>/US100.cash_Minute5.parquet via config.py, resolved in load_us100_m5_tail


def arr(x):
    return np.asarray(x, dtype=float)


def nz(x, repl=0.0):
    x = arr(x).copy()
    x[np.isnan(x)] = repl
    return x


def shift(x, k=1):
    """x[k] in Pine (k bars back); NaN for the first k bars."""
    x = arr(x)
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[:len(x) - k]
    return out


def change(x):
    return arr(x) - shift(x, 1)


def tr(high, low, close, handle_na=True):
    """True range. handle_na=True: bar 0 = high - low (v4 `tr`, ta.atr / ta.dmi); False: bar 0 = NaN (v5 ta.tr variable)."""
    h, l, c = arr(high), arr(low), arr(close)
    pc = shift(c, 1)
    with np.errstate(invalid="ignore"):
        out = np.fmax(np.fmax(h - l, np.abs(h - pc)), np.abs(l - pc))
    out = np.where(np.isnan(pc), (h - l) if handle_na else np.nan, out)
    return out


def sma(x, n):
    x = arr(x)
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        out[i] = np.nan if np.isnan(w).any() else w.sum() / n
    return out


def rma(x, n):
    x = arr(x)
    out = np.full(len(x), np.nan)
    prev = np.nan
    for i in range(len(x)):
        if math.isnan(prev):
            if i >= n - 1:
                w = x[i - n + 1:i + 1]
                if not np.isnan(w).any():
                    prev = w.sum() / n
                    out[i] = prev
        else:
            prev = (x[i] + (n - 1) * prev) / n if not math.isnan(x[i]) else np.nan
            out[i] = prev
    return out


def ema(x, n):
    x = arr(x)
    a = 2.0 / (n + 1)
    out = np.full(len(x), np.nan)
    prev = np.nan
    for i in range(len(x)):
        if math.isnan(x[i]):
            prev = np.nan if math.isnan(prev) else prev
            out[i] = np.nan
            continue
        prev = x[i] if math.isnan(prev) else a * x[i] + (1 - a) * prev
        out[i] = prev
    return out


def wma(x, n):
    x = arr(x)
    out = np.full(len(x), np.nan)
    w = np.arange(1, n + 1, dtype=float)
    den = n * (n + 1) / 2.0
    for i in range(n - 1, len(x)):
        seg = x[i - n + 1:i + 1]
        out[i] = np.nan if np.isnan(seg).any() else float((seg * w).sum() / den)
    return out


def highest(x, n):
    x = arr(x)
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        out[i] = np.nan if np.isnan(w).any() else w.max()
    return out


def lowest(x, n):
    x = arr(x)
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        out[i] = np.nan if np.isnan(w).any() else w.min()
    return out


def rsi(x, n):
    ch = change(x)
    up = rma(np.where(np.isnan(ch), np.nan, np.maximum(ch, 0.0)), n)
    dn = rma(np.where(np.isnan(ch), np.nan, -np.minimum(ch, 0.0)), n)
    out = np.full(len(ch), np.nan)
    for i in range(len(ch)):
        u, d = up[i], dn[i]
        if math.isnan(u) or math.isnan(d):
            continue
        out[i] = 100.0 if d == 0 else (0.0 if u == 0 else 100.0 - 100.0 / (1.0 + u / d))
    return out


def mfi(src, volume, n):
    src, vol = arr(src), arr(volume)
    ch = change(src)
    up_t = np.where(ch <= 0, 0.0, src) * vol          # na change -> comparison false -> src
    dn_t = np.where(ch >= 0, 0.0, src) * vol
    upper, lower = sma(up_t, n) * n, sma(dn_t, n) * n
    out = np.full(len(src), np.nan)
    for i in range(len(src)):
        u, l = upper[i], lower[i]
        if math.isnan(u) or math.isnan(l):
            continue
        if l == 0:
            out[i] = np.nan if u == 0 else 100.0      # x/0 -> inf -> 100; 0/0 -> na
        else:
            out[i] = 100.0 - 100.0 / (1.0 + u / l)
    return out


def crossover(a, b):
    a, b = arr(a), arr(b)
    pa, pb = shift(a), shift(b)
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def crossunder(a, b):
    a, b = arr(a), arr(b)
    pa, pb = shift(a), shift(b)
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)


def pine_round(x):
    """Pine round(): half away from zero for x >= 0 (floor(x + 0.5))."""
    return int(math.floor(x + 0.5))


def load_us100_m5_tail(n=2000, path=DEFAULT_PARQUET):
    """Test helper: last n bars of the exported US100.cash M5 parquet -> dict of float arrays (read only).
    Default file: <DATA_DIR>/US100.cash_Minute5.parquet from the repo's config.py (config.toml or env TT_DATA_DIR)."""
    import pandas as pd
    if path is None:
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import config
        path = os.path.join(config.get("DATA_DIR"), "US100.cash_Minute5.parquet")
    d = pd.read_parquet(path).tail(n).reset_index(drop=True)
    out = {k.lower(): d[k].to_numpy(float) for k in ("Open", "High", "Low", "Close", "TickVolume")}
    out["date"] = d["Date"].to_numpy()
    return out


def assert_truncation_invariant(fn, n_bars, cuts=(None, None, None), keys=None, atol=0.0):
    """fn(m) -> dict name -> array computed on the first m bars. Checks bar i == full-run bar i for cuts at 3 points."""
    full = fn(n_bars)
    for m in (n_bars // 3, n_bars // 2, (4 * n_bars) // 5):
        part = fn(m)
        for k in (keys or part.keys()):
            a, b = np.asarray(part[k], float), np.asarray(full[k], float)[:m]
            ok = np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], rtol=0, atol=atol)
            assert ok, f"look-ahead in '{k}' with cut at {m}"
    return True
