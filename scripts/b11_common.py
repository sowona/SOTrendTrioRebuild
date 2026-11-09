#!/usr/bin/env python3
"""B11 common module: TT1 "Trend Trio" rebuilt on US100.cash. Spec: ../SPEC_B11.md.

BAR SOURCE: Minute, Minute5, Minute15, Hour come from the exported <DATA_DIR>/US100.cash_<TF>.parquet (bid).
OWNER RULING 08/11/2026 (SPEC_B11.md, one-off, B11 only): no US100.cash Minute2 / Minute4 export exists, so 2m and 4m bars are built
from US100.cash_Minute.parquet on clock-minute boundaries from 00:00 UTC (open = first, high = max, low = min, close = last,
TickVolume = sum), stamped at the bar open; a bar with missing minutes is built from the minutes present (counted). Nothing else is
ever resampled (no 5m / 15m / 1h from m1).
Spread: spread1m parquet (real, from 01/12/2021 to 25/10/2026); 0 / absent = missing -> same-month hour-of-week median (counted);
months with no real spread at all (12/2020-11/2021, 26/10-06/11/2026) take the nearest real month's profile = ESTIMATE, flagged.
Swap: E1_SWAP.json US100.cash snapshot of 25/10/2026 (one date), fixed points per night, Friday x3, NY 17:00 rollover.
No parquet is written (only small npz caches). Input sha256 manifest: written by b11_stage0.py.
Conventions: bar Date = open time UTC; bar closes at open + length. Causal availability = open + length; look-ahead probe
availability = open + 1 minute (forming HTF bar, final values). Entry at the m1 open at / after the availability time.
"""
import os, sys, json, math, hashlib
import numpy as np
import pandas as pd
from numba import njit

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTS = os.path.join(_REPO, "indicators")
sys.path.insert(0, PORTS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # scripts/common.py (find_holes)
sys.path.insert(0, _REPO)                                           # config.py
import config  # noqa: E402
import pine_common as pc  # noqa: E402
import supertrend_port as stp  # noqa: E402
import ultimate_ma_port as uma  # noqa: E402
import slingshot_port as ssp  # noqa: E402
import chandelier_port as chp  # noqa: E402
import alphatrend_port as atp  # noqa: E402
import dmi_port as dmp  # noqa: E402
from common import find_holes  # noqa: E402

SYM = "US100.cash"
DATA = config.get("DATA_DIR")
SPR_PATH = config.get("SPREAD1M_PATH")
SWAP_PATH = config.get("SWAP_PATH")
OUT = config.get("OUT_DIR")
CACHE = os.path.join(OUT, "cache")
os.makedirs(CACHE, exist_ok=True)

GLOBAL_START = np.datetime64("2021-01-04T00:00:00", "ns")   # all indicators converged (>= 3 x longest length on every TF); data starts 02/12/2020
ERA_CUT = np.datetime64("2024-01-01T00:00:00", "ns")
TV_START = np.datetime64("2023-11-15T00:00:00", "ns")        # his TradingView 1-minute window start (first listed trade 15/11/2023)
USD_PER_PT = 20.0
FEE_PTS = 4.28 / 20.0                                         # his $4.28 per NQ round trip
TICK = 0.25

SETUP_NAMES = ["S1 SuperTrend 5m", "S2 UltimateMA 4m", "S3 AlphaTrend 2m", "S4 AlphaTrend 1h"]
TIE_ORDER = np.array([1, 0, 2, 3], dtype=np.int64)            # setup 2, 1, 3, 4
WIN_TOD = {0: (570, 930), 2: (570, 690), 3: (600, 900)}      # NY minutes of day, [start, end); S2 any hour
FLAT_TOD = 960                                                # 16:00 NY
FLAT_FLAG = np.array([True, False, True, True])


# ------------------------------------------------------------------------------------------------ config
class Cfg:
    def __init__(self, st_mult=2.0, st_len=10, stop_atr_len=14, stop_mult=2.0, at_rsi=False, adx_min=20.0, at_coeff=1.0, at_ap=14,
                 sling=(38, 62), uma_len=20, ch_len=22, ch_mult=3.0, ema_len=200):
        self.st_mult, self.st_len, self.stop_atr_len, self.stop_mult = st_mult, st_len, stop_atr_len, stop_mult
        self.at_rsi, self.adx_min, self.at_coeff, self.at_ap = at_rsi, adx_min, at_coeff, at_ap
        self.sling, self.uma_len, self.ch_len, self.ch_mult, self.ema_len = sling, uma_len, ch_len, ch_mult, ema_len

    def ind_key(self):
        return f"st{self.st_mult}_{self.st_len}_atr{self.stop_atr_len}_rsi{int(self.at_rsi)}_c{self.at_coeff}_ap{self.at_ap}"


# ------------------------------------------------------------------------------------------------ bars
class Bars:
    def __init__(self, open_t, o, h, l, c, tv, minutes):
        self.open_t, self.o, self.h, self.l, self.c, self.tv, self.minutes = open_t, o, h, l, c, tv, minutes

    def __len__(self):
        return len(self.o)

    def avail(self, mode):
        add = self.minutes if mode == "causal" else 1
        return self.open_t + np.timedelta64(add, "m")

    def close_t(self):
        return self.open_t + np.timedelta64(self.minutes, "m")


def load_export(tf, minutes, cut=None):
    d = pd.read_parquet(os.path.join(DATA, f"{SYM}_{tf}.parquet"), columns=["Date", "Open", "High", "Low", "Close", "TickVolume"])
    d = d.drop_duplicates("Date").sort_values("Date").reset_index(drop=True)
    t = d["Date"].to_numpy("datetime64[ns]")
    keep = np.ones(len(t), bool) if cut is None else (t + np.timedelta64(minutes, "m") <= cut)
    return Bars(t[keep], d.Open.to_numpy(float)[keep], d.High.to_numpy(float)[keep], d.Low.to_numpy(float)[keep],
                d.Close.to_numpy(float)[keep], d.TickVolume.to_numpy(float)[keep], minutes)


def build_n_min(m1, n, cut=None):
    """OWNER RULING (SPEC_B11): n-minute bars from m1 on clock boundaries from 00:00 UTC. Returns (Bars, n_bars_with_missing_minutes)."""
    tmin = m1.open_t.astype("datetime64[m]").astype(np.int64)
    grp = tmin // n
    starts = np.r_[0, np.flatnonzero(np.diff(grp)) + 1]
    cnt = np.diff(np.r_[starts, len(grp)])
    open_t = (grp[starts] * n).astype("datetime64[m]").astype("datetime64[ns]")
    b = Bars(open_t, m1.o[starts], np.maximum.reduceat(m1.h, starts), np.minimum.reduceat(m1.l, starts),
             m1.c[np.r_[starts[1:] - 1, len(grp) - 1]], np.add.reduceat(m1.tv, starts), n)
    miss = int((cnt < n).sum())
    if cut is not None:
        keep = open_t + np.timedelta64(n, "m") <= cut
        b = Bars(b.open_t[keep], b.o[keep], b.h[keep], b.l[keep], b.c[keep], b.tv[keep], n)
    return b, miss


class Ctx:
    """m1 arrays + NY clock + all bar sets. cut: truncate the world at this UTC time (truncation-invariance tests)."""
    def __init__(self, cut=None):
        d = pd.read_parquet(os.path.join(DATA, f"{SYM}_Minute.parquet"), columns=["Date", "Open", "High", "Low", "Close", "TickVolume"])
        d = d.drop_duplicates("Date").sort_values("Date").reset_index(drop=True)
        if cut is not None:
            d = d[d.Date < pd.Timestamp(cut)].reset_index(drop=True)
        self.t = d.Date.to_numpy("datetime64[ns]")
        self.n = len(self.t)
        self.o, self.h, self.l, self.c = (d[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
        self.m1 = Bars(self.t, self.o, self.h, self.l, self.c, d.TickVolume.to_numpy(float), 1)
        self.bars = {"M1": self.m1}
        self.miss = {}
        for n in (2, 4):
            self.bars[f"M{n}"], self.miss[n] = build_n_min(self.m1, n, cut)
        self.bars["M5"] = load_export("Minute5", 5, cut)
        self.bars["M15"] = load_export("Minute15", 15, cut)
        self.bars["H1"] = load_export("Hour", 60, cut)
        # NY clock
        loc = pd.DatetimeIndex(self.t).tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        self.tod = (loc.hour * 60 + loc.minute).to_numpy(np.int64)
        epoch = np.datetime64("1970-01-01")
        self.nyd = ((loc.normalize().to_numpy("datetime64[ns]") - np.datetime64("1970-01-01T00:00:00", "ns")) // np.timedelta64(1, "D")).astype(np.int64)
        self.dow = loc.dayofweek.to_numpy(np.int64)
        self.key = self.nyd * 1440 + self.tod
        self.era = np.where(self.t < ERA_CUT, 1, 2).astype(np.int8)
        self.cumw = self._cum_swap_weights()

    def _cum_swap_weights(self):
        d0, d1 = int(self.nyd.min()) - 1, int(self.nyd.max()) + 1
        days = np.arange(d0, d1 + 1)
        wall = pd.DatetimeIndex(days.astype("datetime64[D]").astype("datetime64[ns]")) + pd.Timedelta(hours=17)
        r_utc = wall.tz_localize("America/New_York").tz_convert("UTC").tz_localize(None).to_numpy("datetime64[ns]")
        dw = pd.DatetimeIndex(days.astype("datetime64[D]").astype("datetime64[ns]")).dayofweek.to_numpy()
        w = np.where(dw <= 3, 1, np.where(dw == 4, 3, 0)).astype(np.int64)
        cw = np.cumsum(w)
        pos = np.searchsorted(r_utc, self.t, side="right")          # number of rollovers <= t
        return np.where(pos > 0, cw[np.maximum(pos - 1, 0)], 0).astype(np.int64)


# ------------------------------------------------------------------------------------------------ spread / swap
def load_spread(ctx):
    """Per-m1 spread (points). Returns (spr array aligned to ctx.t, flag array: 0 real, 1 substituted in real span, 2 estimate outside span, report dict)."""
    s = pd.read_parquet(SPR_PATH)
    ser = s.drop_duplicates("Date").set_index("Date")["spread"]
    v = ser.reindex(pd.DatetimeIndex(ctx.t)).to_numpy(float)
    t = pd.DatetimeIndex(ctx.t)
    first_real, last_real = ser.index.min(), ser.index.max()
    in_span = (t >= first_real) & (t <= last_real)
    bad = np.isnan(v) | (v <= 0)
    ym = (t.year * 12 + t.month - 1).to_numpy()
    how = (t.dayofweek * 24 + t.hour).to_numpy()
    good = ~bad
    df = pd.DataFrame({"ym": ym, "how": how, "v": np.where(good, v, np.nan)})
    med_ym_how = df.groupby(["ym", "how"])["v"].transform("median").to_numpy()
    med_ym_h = df.assign(h=how % 24).groupby(["ym", "h"])["v"].transform("median").to_numpy()
    med_ym = df.groupby("ym")["v"].transform("median").to_numpy()
    sub = np.where(~np.isnan(med_ym_how), med_ym_how, np.where(~np.isnan(med_ym_h), med_ym_h, med_ym))
    out = np.where(good, v, sub)
    flag = np.where(good, 0, 1).astype(np.int8)
    # months with no real spread: nearest real month profile
    ym_with = np.unique(ym[good])
    miss_m = np.isnan(out)
    if miss_m.any():
        prof_lo = df[df.ym == ym_with.min()].groupby("how")["v"].median()
        prof_hi = df[df.ym == ym_with.max()].groupby("how")["v"].median()
        use_lo = ym < ym_with.min()
        ref = np.where(use_lo, prof_lo.reindex(how).to_numpy(), prof_hi.reindex(how).to_numpy())
        out = np.where(miss_m, ref, out)
        flag = np.where(miss_m, 2, flag).astype(np.int8)
    # a month inside the span but with a thin profile can still be NaN: fall back to global month median
    out = np.where(np.isnan(out), np.nanmedian(v[good]), out)
    rep = {"first_real": str(first_real), "last_real": str(last_real), "minutes": int(len(v)), "real": int((flag == 0).sum()),
           "substituted_in_span": int(((flag == 1) & in_span).sum()), "substituted_other": int((flag == 1).sum() - ((flag == 1) & in_span).sum()),
           "estimate_outside_span": int((flag == 2).sum()), "median_real": float(np.nanmedian(v[good]))}
    return out.astype(float), flag, rep


def load_swap():
    d = json.load(open(SWAP_PATH))["symbols"]["US100.cash"]
    return float(d["swap_long"]), float(d["swap_short"])


# ------------------------------------------------------------------------------------------------ indicators
def compute_ind(ctx, cfg, label="full"):
    """Vectorised-per-TF indicator computation (ports). Cached as npz per (label, cfg) in OUT\\cache."""
    path = os.path.join(CACHE, f"ind_{label}_{cfg.ind_key()}.npz")
    if label != "full" or not os.path.exists(path):
        I = _compute_ind(ctx, cfg)
        if label == "full":
            np.savez(path, **{f"{k}__{kk}": vv for k, v in I.items() for kk, vv in v.items()})
        return I
    z = np.load(path)
    I = {}
    for name in z.files:
        k, kk = name.split("__")
        I.setdefault(k, {})[kk] = z[name]
    return I


def _compute_ind(ctx, cfg):
    I = {}
    b = ctx.bars["M5"]
    s = stp.supertrend(b.h, b.l, b.c, cfg.st_len, cfg.st_mult)
    I["M5"] = {"buy": s["buy"], "sell": s["sell"], "atr": pc.rma(pc.tr(b.h, b.l, b.c, True), cfg.stop_atr_len)}
    b = ctx.bars["M15"]
    s = stp.supertrend(b.h, b.l, b.c, cfg.st_len, cfg.st_mult)
    sl = ssp.slingshot(b.c, *cfg.sling)
    I["M15"] = {"trend": s["trend"], "sling": sl["state"]}
    b = ctx.bars["M4"]
    u = uma.ultimate_ma(b.c, cfg.uma_len, 1, 7, 2, True)
    ch = chp.chandelier(b.h, b.l, b.c, cfg.ch_len, cfg.ch_mult, True)
    I["M4"] = {"turn_up": u["turn_up"], "ch_sell": ch["sell"]}
    b = ctx.bars["M2"]
    a = atp.alphatrend(b.h, b.l, b.c, b.tv, cfg.at_coeff, cfg.at_ap, cfg.at_rsi)
    dm = dmp.dmi(b.h, b.l, b.c, 14, 14)
    I["M2"] = {"buy": a["buy"], "sell": a["sell"], "adx": dm["adx"]}
    b = ctx.bars["H1"]
    a = atp.alphatrend(b.h, b.l, b.c, b.tv, cfg.at_coeff, cfg.at_ap, cfg.at_rsi)
    I["H1"] = {"buy": a["buy"], "sell": a["sell"], "ema": pc.ema(b.c, cfg.ema_len), "atr": pc.rma(pc.tr(b.h, b.l, b.c, True), cfg.stop_atr_len)}
    return I


# ------------------------------------------------------------------------------------------------ signals
class Signals:
    def __init__(self, n):
        self.en_dir = np.zeros((4, n), np.int8)
        self.en_stop = np.zeros((4, n), np.float64)
        self.ex_flag = np.zeros((4, n), np.int8)        # bit1: buy-type signal (exits shorts), bit2: sell-type (exits longs)
        self.counts = []                                  # rows: setup, stage, year, n


def _to_idx(ctx, av):
    return np.searchsorted(ctx.t, av, side="left")


def _count(sig, setup, stage, times):
    if len(times) == 0:
        return
    yrs = times.astype("datetime64[Y]").astype(int) + 1970
    u, c = np.unique(yrs, return_counts=True)
    for y, k in zip(u, c):
        sig.counts.append((setup, stage, int(y), int(k)))


def build_signals(ctx, I, mode, cfg):
    """Entry / exit signal tables at m1 resolution for the 4 setups. All HTF values read at availability time (closed bar if causal,
    forming-bar final value if look-ahead). Counts per stage and year are collected for printing before outcomes."""
    n = ctx.n
    sig = Signals(n)
    B = ctx.bars

    # modes: causal; lookahead (signals AND filters from the forming HTF bar); lookahead_filters (signals causal, cross-TF filters forming)
    sm = "causal" if mode in ("causal", "lookahead_filters") else "lookahead"
    fm = "lookahead" if mode in ("lookahead", "lookahead_filters") else "causal"

    def avail(tf):
        return B[tf].avail(sm)

    def fil(tf, av_sig):
        return np.searchsorted(B[tf].avail(fm), av_sig, side="right") - 1

    # S1: SuperTrend 5m buy flip, 15m SuperTrend green, 09:30-15:30, stop 2 x ATR(5m)
    av5 = avail("M5")
    ev = np.flatnonzero(I["M5"]["buy"] & (av5 >= GLOBAL_START))
    _count(sig, 0, "raw", av5[ev])
    fb = fil("M15", av5[ev])
    ok = (fb >= 0)
    ok[ok] = I["M15"]["trend"][fb[ok]] == 1
    ev = ev[ok]
    _count(sig, 0, "filter", av5[ev])
    di = _to_idx(ctx, av5[ev])
    k = di < n
    ev, di = ev[k], di[k]
    k = (ctx.tod[di] >= WIN_TOD[0][0]) & (ctx.tod[di] < WIN_TOD[0][1]) & np.isfinite(I["M5"]["atr"][ev])
    ev, di = ev[k], di[k]
    _count(sig, 0, "window", ctx.t[di])
    sig.en_dir[0, di] = 1
    sig.en_stop[0, di] = cfg.stop_mult * I["M5"]["atr"][ev]
    dx = _to_idx(ctx, av5[np.flatnonzero(I["M5"]["sell"] & (av5 >= GLOBAL_START))])
    dx = dx[dx < n]
    sig.ex_flag[0, dx] |= 2

    # S2: Ultimate MA 4m turns green, Sling Shot 15m fast > slow, any hour; exit 4m Chandelier turns down
    av4 = avail("M4")
    ev = np.flatnonzero(I["M4"]["turn_up"] & (av4 >= GLOBAL_START))
    _count(sig, 1, "raw", av4[ev])
    fb = fil("M15", av4[ev])
    ok = (fb >= 0)
    ok[ok] = I["M15"]["sling"][fb[ok]]
    ev = ev[ok]
    _count(sig, 1, "filter", av4[ev])
    di = _to_idx(ctx, av4[ev])
    di = di[di < n]
    _count(sig, 1, "window", ctx.t[di])
    sig.en_dir[1, di] = 1
    dx = _to_idx(ctx, av4[np.flatnonzero(I["M4"]["ch_sell"] & (av4 >= GLOBAL_START))])
    dx = dx[dx < n]
    sig.ex_flag[1, dx] |= 2

    # S3: AlphaTrend 2m, ADX(14) >= 20 on 2m, 09:30-11:30, long + short; exit opposite signal (unfiltered)
    av2 = avail("M2")
    adx = I["M2"]["adx"]
    for side, name, d in ((1, "buy", 1), (-1, "sell", -1)):
        ev = np.flatnonzero(I["M2"][name] & (av2 >= GLOBAL_START))
        _count(sig, 2, "raw", av2[ev])
        fb = fil("M2", av2[ev])
        ok = (fb >= 0)
        ok[ok] = adx[fb[ok]] >= cfg.adx_min
        ev = ev[ok]
        _count(sig, 2, "filter", av2[ev])
        di = _to_idx(ctx, av2[ev])
        di = di[di < n]
        di = di[(ctx.tod[di] >= WIN_TOD[2][0]) & (ctx.tod[di] < WIN_TOD[2][1])]
        _count(sig, 2, "window", ctx.t[di])
        sig.en_dir[2, di] = d
        dx = _to_idx(ctx, av2[np.flatnonzero(I["M2"][name] & (av2 >= GLOBAL_START))])
        dx = dx[dx < n]
        sig.ex_flag[2, dx] |= (1 if d == 1 else 2)

    # S4: AlphaTrend 1h, long above / short below EMA200(1h), 10:00-15:00, stop 2 x ATR(1h), long + short; exit opposite signal
    avh = avail("H1")
    hc, he, ha = B["H1"].c, I["H1"]["ema"], I["H1"]["atr"]
    for name, d in (("buy", 1), ("sell", -1)):
        ev = np.flatnonzero(I["H1"][name] & (avh >= GLOBAL_START))
        _count(sig, 3, "raw", avh[ev])
        fb = fil("H1", avh[ev])
        ok = (fb >= 0)
        with np.errstate(invalid="ignore"):
            ok[ok] = (hc[fb[ok]] > he[fb[ok]]) if d == 1 else (hc[fb[ok]] < he[fb[ok]])
        ok &= np.isfinite(ha[ev])
        ev = ev[ok]
        _count(sig, 3, "filter", avh[ev])
        di = _to_idx(ctx, avh[ev])
        k = di < n
        ev, di = ev[k], di[k]
        k = (ctx.tod[di] >= WIN_TOD[3][0]) & (ctx.tod[di] < WIN_TOD[3][1])
        ev, di = ev[k], di[k]
        _count(sig, 3, "window", ctx.t[di])
        sig.en_dir[3, di] = d
        sig.en_stop[3, di] = cfg.stop_mult * ha[ev]
        dx = _to_idx(ctx, avh[np.flatnonzero(I["H1"][name] & (avh >= GLOBAL_START))])
        dx = dx[dx < n]
        sig.ex_flag[3, dx] |= (1 if d == 1 else 2)
    return sig


# ------------------------------------------------------------------------------------------------ simulator
@njit(cache=True)
def _rec(T_set, T_dir, T_ei, T_xi, T_epx, T_xpx, T_rsn, nt, s, d, ei, xi, epx, xpx, rsn):
    T_set[nt] = s
    T_dir[nt] = d
    T_ei[nt] = ei
    T_xi[nt] = xi
    T_epx[nt] = epx
    T_xpx[nt] = xpx
    T_rsn[nt] = rsn


@njit(cache=True)
def simulate(o, h, l, c, spr, key, nyd, en_dir, en_stop, ex_flag, flatflag, enabled, order, rnd, tie_random, reverse,
             slip, fee, i_start, i_end, flat_tod):
    n = len(o)
    maxt = 600000
    T_set = np.empty(maxt, np.int8)
    T_dir = np.empty(maxt, np.int8)
    T_ei = np.empty(maxt, np.int64)
    T_xi = np.empty(maxt, np.int64)
    T_epx = np.empty(maxt, np.float64)
    T_xpx = np.empty(maxt, np.float64)
    T_rsn = np.empty(maxt, np.int8)                  # 1 signal, 2 flat 16:00, 3 stop, 9 end of run
    nt = 0
    pos = 0
    ps = -1
    epx = 0.0
    stop = 0.0
    ei = 0
    flatkey = 0
    real = 0.0
    peak = 0.0
    maxdd = 0.0
    blk_s = -1
    blk_i = -1
    cand = np.empty(4, np.int64)
    for i in range(i_start, i_end):
        if pos != 0:
            xpx = 0.0
            rsn = 0
            if stop > 0.0:
                if pos > 0 and o[i] <= stop:
                    xpx = o[i] - slip
                    rsn = 3
                elif pos < 0 and o[i] + spr[i] >= stop:
                    xpx = o[i] + spr[i] + slip
                    rsn = 3
            if rsn == 0 and flatflag[ps] and key[i] >= flatkey:
                xpx = o[i] - slip if pos > 0 else o[i] + spr[i] + slip
                rsn = 2
            if rsn == 0:
                f = ex_flag[ps, i]
                if (pos > 0 and (f & 2) != 0) or (pos < 0 and (f & 1) != 0):
                    xpx = o[i] - slip if pos > 0 else o[i] + spr[i] + slip
                    rsn = 1
                    blk_s = ps
                    blk_i = i
            if rsn != 0:
                _rec(T_set, T_dir, T_ei, T_xi, T_epx, T_xpx, T_rsn, nt, ps, pos, ei, i, epx, xpx, rsn)
                nt += 1
                real += (xpx - epx) * pos - fee
                pos = 0
                stop = 0.0
        if pos == 0:
            k = 0
            for q in range(4):
                s = order[q]
                if enabled[s] and en_dir[s, i] != 0 and not (blk_i == i and blk_s == s and not reverse):
                    cand[k] = s
                    k += 1
            if k > 0:
                pick = 0
                if tie_random and k > 1:
                    pick = int(rnd[i] * k)
                    if pick >= k:
                        pick = k - 1
                s = cand[pick]
                d = en_dir[s, i]
                epx = o[i] + spr[i] + slip if d > 0 else o[i] - slip
                stop = (epx - en_stop[s, i] if d > 0 else epx + en_stop[s, i]) if en_stop[s, i] > 0.0 else 0.0
                pos = d
                ps = s
                ei = i
                flatkey = nyd[i] * 1440 + flat_tod
        if pos != 0 and stop > 0.0:
            if pos > 0 and l[i] <= stop:
                xpx = stop - slip
                _rec(T_set, T_dir, T_ei, T_xi, T_epx, T_xpx, T_rsn, nt, ps, pos, ei, i, epx, xpx, 3)
                nt += 1
                real += (xpx - epx) * pos - fee
                pos = 0
                stop = 0.0
            elif pos < 0 and h[i] + spr[i] >= stop:
                xpx = stop + slip
                _rec(T_set, T_dir, T_ei, T_xi, T_epx, T_xpx, T_rsn, nt, ps, pos, ei, i, epx, xpx, 3)
                nt += 1
                real += (xpx - epx) * pos - fee
                pos = 0
                stop = 0.0
        eq = real
        if pos > 0:
            eq += c[i] - epx
        elif pos < 0:
            eq += epx - (c[i] + spr[i])
        if eq > peak:
            peak = eq
        if peak - eq > maxdd:
            maxdd = peak - eq
    if pos != 0:
        if i_end < n:
            xi = i_end
            xpx = o[i_end] - slip if pos > 0 else o[i_end] + spr[i_end] + slip
        else:
            xi = n - 1
            xpx = c[n - 1] - slip if pos > 0 else c[n - 1] + spr[n - 1] + slip
        _rec(T_set, T_dir, T_ei, T_xi, T_epx, T_xpx, T_rsn, nt, ps, pos, ei, xi, epx, xpx, 9)
        nt += 1
        real += (xpx - epx) * pos - fee
    return (T_set[:nt].copy(), T_dir[:nt].copy(), T_ei[:nt].copy(), T_xi[:nt].copy(), T_epx[:nt].copy(), T_xpx[:nt].copy(),
            T_rsn[:nt].copy(), maxdd)


def run(ctx, sig, spr, enabled=(1, 1, 1, 1), slip=0.0, fee=0.0, i_start=0, i_end=None, reverse=False, tie_random=False, seed=1,
        swap=None):
    """Run the portfolio. Returns a DataFrame of trades. pts = price points net of spread / slip / fee; swap_pts added when swap given."""
    i_end = ctx.n if i_end is None else i_end
    rnd = np.random.default_rng(seed).random(ctx.n) if tie_random else np.zeros(1)
    r = simulate(ctx.o, ctx.h, ctx.l, ctx.c, spr, ctx.key, ctx.nyd, sig.en_dir, sig.en_stop, sig.ex_flag, FLAT_FLAG,
                 np.array(enabled, dtype=np.bool_), TIE_ORDER, rnd, tie_random, reverse, slip, fee, i_start, i_end, FLAT_TOD)
    s, d, ei, xi, epx, xpx, rsn, mdd = r
    df = pd.DataFrame({"setup": s.astype(int), "dir": d.astype(int), "ei": ei, "xi": xi, "epx": epx, "xpx": xpx, "rsn": rsn.astype(int)})
    df["pts"] = (df.xpx - df.epx) * df.dir - fee
    df["t_in"] = ctx.t[df.ei.to_numpy()]
    df["t_out"] = ctx.t[df.xi.to_numpy()]
    df["day"] = ctx.nyd[df.ei.to_numpy()]
    df["era"] = ctx.era[df.ei.to_numpy()]
    df["year"] = df.t_in.to_numpy().astype("datetime64[Y]").astype(int) + 1970
    df["hold_min"] = (df.t_out - df.t_in) / np.timedelta64(1, "m")
    df["bars_held"] = df.xi - df.ei
    nights = ctx.cumw[df.xi.to_numpy()] - ctx.cumw[df.ei.to_numpy()]
    df["nights"] = nights
    if swap is not None:
        sw_l, sw_s = swap
        df["swap_pts"] = np.where(df.dir > 0, nights * sw_l, nights * sw_s)
    else:
        df["swap_pts"] = 0.0
    df["net"] = df.pts + df.swap_pts
    df.attrs["maxdd_mtm"] = float(mdd)
    return df


# ------------------------------------------------------------------------------------------------ stats
def boot_day(x, day, nb=1000, seed=5):
    """(n, mean, lo, hi) with a 95 % bootstrap CI resampling trading days (all trades of one NY entry day move together)."""
    x = np.asarray(x, float)
    day = np.asarray(day)
    if len(x) < 8:
        return len(x), (float(x.mean()) if len(x) else np.nan), np.nan, np.nan
    u, inv = np.unique(day, return_inverse=True)
    S = np.bincount(inv, weights=x)
    C = np.bincount(inv).astype(float)
    g = np.random.default_rng(seed)
    idx = g.integers(0, len(u), (nb, len(u)))
    mm = S[idx].sum(1) / C[idx].sum(1)
    return len(x), float(x.mean()), float(np.percentile(mm, 2.5)), float(np.percentile(mm, 97.5))


def pf_win(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return np.nan, np.nan
    w, lo = x[x > 0].sum(), -x[x <= 0].sum()
    return (float(w / lo) if lo > 0 else np.nan), float((x > 0).mean())


def max_dd_closed(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return 0.0
    cum = np.cumsum(x)
    peak = np.maximum.accumulate(np.r_[0.0, cum])[1:]
    return float((peak - cum).max())


def summarize(df, col="net", nb=1000, seed=5):
    n, m, lo, hi = boot_day(df[col].to_numpy(), df.day.to_numpy(), nb, seed) if len(df) else (0, np.nan, np.nan, np.nan)
    pf, wr = pf_win(df[col].to_numpy())
    return {"n": n, "mean": m, "lo": lo, "hi": hi, "win": wr * 100 if wr == wr else np.nan, "pf": pf,
            "hold_h": float(df.hold_min.mean() / 60) if len(df) else np.nan, "dd": max_dd_closed(df.sort_values("t_out")[col].to_numpy()),
            "sum": float(df[col].sum())}


def md(df, floatfmt="{:.2f}"):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if v != v else floatfmt.format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def sha256(path, nmax=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
