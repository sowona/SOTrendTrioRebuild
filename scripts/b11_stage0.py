#!/usr/bin/env python3
"""B11 stage 0: data checks, 2m / 4m build counts, literal-Pine port checks (SuperTrend, AlphaTrend), signal counts BEFORE outcomes,
entry-minute-mod-N test, truncation-invariance (3 cuts) of signals and of the trade list.
Bar source: exported US100.cash Minute / Minute5 / Minute15 / Hour parquet; 2m / 4m built from Minute by the OWNER'S ONE-OFF RULING of
08/11/2026 (SPEC_B11.md). Inputs read only; sha256 manifest written to OUT\\manifest.json. No parquet written.
Run: python b11_stage0.py   (log: OUT\\stage0.txt)
"""
import os, sys, json, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b11_common import *

LOG = open(os.path.join(OUT, "stage0.txt"), "w", encoding="utf8")


def P(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


# ------------------------------------------------------------------ literal Pine scalars (written from SPEC_B11.md, independent of the ports)
def na(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def nz(x, r=0.0):
    return r if na(x) else x


def st_literal(H, L, C, P_, M, changeATR):
    n = len(C)
    tr = [None] * n
    for i in range(n):
        if i == 0:
            tr[i] = (H[0] - L[0]) if changeATR else None            # ta.atr: tr(true); ta.sma(ta.tr): variable, na on bar 0
        else:
            tr[i] = max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1]))
    atr = [None] * n
    if changeATR:                                                    # rma: SMA seed, alpha 1/P
        prev = None
        for i in range(n):
            if i == P_ - 1:
                prev = sum(tr[:P_]) / P_
                atr[i] = prev
            elif i >= P_:
                prev = (tr[i] + (P_ - 1) * prev) / P_
                atr[i] = prev
    else:
        for i in range(n):
            w = tr[max(0, i - P_ + 1):i + 1]
            if i >= P_ - 1 and len(w) == P_ and all(not na(x) for x in w):
                atr[i] = sum(w) / P_
    up = [None] * n
    dn = [None] * n
    trend = [None] * n
    buy = [False] * n
    for i in range(n):
        src = (H[i] + L[i]) / 2.0
        u = None if na(atr[i]) else src - M * atr[i]
        d = None if na(atr[i]) else src + M * atr[i]
        up1 = u if (i == 0 or na(up[i - 1])) else up[i - 1]
        dn1 = d if (i == 0 or na(dn[i - 1])) else dn[i - 1]
        if i > 0 and not na(up1) and C[i - 1] > up1:
            u = max(u, up1)
        if i > 0 and not na(dn1) and C[i - 1] < dn1:
            d = min(d, dn1)
        up[i], dn[i] = u, d
        t = 1 if i == 0 else trend[i - 1]
        if t == -1 and not na(dn1) and C[i] > dn1:
            t = 1
        elif t == 1 and not na(up1) and C[i] < up1:
            t = -1
        trend[i] = t
        buy[i] = (i > 0 and trend[i] == 1 and trend[i - 1] == -1)
    return up, dn, trend, buy


def at_literal(H, L, C, V, AP, coeff, rsi_path):
    n = len(C)
    tr = [None] + [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(1, n)]
    atr = [None] * n
    for i in range(AP, n):
        atr[i] = sum(tr[i - AP + 1:i + 1]) / AP
    cond = [False] * n
    if rsi_path:
        gains = [None] + [max(C[i] - C[i - 1], 0) for i in range(1, n)]
        loss = [None] + [max(C[i - 1] - C[i], 0) for i in range(1, n)]
        ru = rd = None
        for i in range(AP, n):
            ru = sum(gains[1:AP + 1]) / AP if i == AP else (gains[i] + (AP - 1) * ru) / AP
            rd = sum(loss[1:AP + 1]) / AP if i == AP else (loss[i] + (AP - 1) * rd) / AP
            r = 100.0 if rd == 0 else (0.0 if ru == 0 else 100 - 100 / (1 + ru / rd))
            cond[i] = r >= 50
    else:
        tp = [(H[i] + L[i] + C[i]) / 3 for i in range(n)]
        for i in range(AP - 1, n):
            up_s = lo_s = 0.0
            for j in range(i - AP + 1, i + 1):
                ch = None if j == 0 else tp[j] - tp[j - 1]
                up_s += V[j] * (0 if (ch is not None and ch <= 0) else tp[j])
                lo_s += V[j] * (0 if (ch is not None and ch >= 0) else tp[j])
            if lo_s == 0:
                cond[i] = up_s != 0
            else:
                cond[i] = (100 - 100 / (1 + up_s / lo_s)) >= 50
    at = [None] * n
    for i in range(n):
        upT = None if na(atr[i]) else L[i] - atr[i] * coeff
        dnT = None if na(atr[i]) else H[i] + atr[i] * coeff
        p = nz(at[i - 1]) if i > 0 else 0.0
        if cond[i]:
            at[i] = p if (upT is not None and upT < p) else upT
        else:
            at[i] = p if (dnT is not None and dnT > p) else dnT
    buyK = [False] * n
    sellK = [False] * n
    # crossover(a, b) = a > b and a[1] <= b[1], with b = AT[2]
    for i in range(3, n):
        a0, a1, b0, b1 = at[i], at[i - 1], at[i - 2], at[i - 3]
        if any(na(x) for x in (a0, a1, b0, b1)):
            continue
        buyK[i] = a0 > b0 and a1 <= b1
        sellK[i] = a0 < b0 and a1 >= b1

    def barssince(flags, i):
        for j in range(i, -1, -1):
            if flags[j]:
                return i - j
        return None
    buy = [False] * n
    sell = [False] * n
    for i in range(n):
        K1, K2 = barssince(buyK, i), barssince(sellK, i)
        O1 = barssince(buyK, i - 1) if i >= 1 else None
        O2 = barssince(sellK, i - 1) if i >= 1 else None
        buy[i] = buyK[i] and (O1 is not None and K2 is not None and O1 > K2)
        sell[i] = sellK[i] and (O2 is not None and K1 is not None and O2 > K1)
    return at, buy, sell


def cmp_arr(a, b, name, tol=1e-9):
    a = np.array([np.nan if na(x) else x for x in a], float)
    b = np.asarray(b, float)
    ok = np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[~np.isnan(a)], b[~np.isnan(b)], rtol=0, atol=tol)
    P(f"   {name}: {'MATCH' if ok else 'DIFF'}" + ("" if ok else f" (max abs {np.nanmax(np.abs(a - b)):.3g})"))
    return ok


def port_checks(ctx):
    P("\n== PORT CHECKS: ports vs literal Pine scalars written from SPEC_B11.md (real US100.cash slices) ==")
    allok = True
    b = ctx.bars["M5"]
    sl = slice(60000, 63500)
    H, L, C = b.h[sl].tolist(), b.l[sl].tolist(), b.c[sl].tolist()
    for mult in (2.0, 3.0):
        for chg in (True, False):
            up, dn, tr_, buy = st_literal(H, L, C, 10, mult, chg)
            r = stp.supertrend(np.array(H), np.array(L), np.array(C), 10, mult, change_atr=chg, tr_first_bar_na=True)
            P(f" SuperTrend M5 slice, mult {mult}, changeATR {chg}")
            allok &= cmp_arr(up, r["up"], "up")
            allok &= cmp_arr(dn, r["dn"], "dn")
            allok &= cmp_arr(tr_, r["trend"], "trend")
            allok &= bool(np.array_equal(np.array(buy), r["buy"]))
            P(f"   buy flags: {'MATCH' if np.array_equal(np.array(buy), r['buy']) else 'DIFF'} ({int(sum(buy))} buys)")
    for tf, sl, n in (("H1", slice(20000, 21500), "H1"), ("M5", slice(100000, 101500), "M5")):
        b = ctx.bars[tf]
        H, L, C, V = b.h[sl].tolist(), b.l[sl].tolist(), b.c[sl].tolist(), b.tv[sl].tolist()
        for rsi_path in (False, True):
            at, buy, sell = at_literal(H, L, C, V, 14, 1.0, rsi_path)
            r = atp.alphatrend(np.array(H), np.array(L), np.array(C), np.array(V), 1.0, 14, rsi_path, tr_first_bar_na=True)
            P(f" AlphaTrend {tf} slice, {'RSI' if rsi_path else 'MFI(TickVolume)'} path")
            allok &= cmp_arr(at, r["alphatrend"], "AlphaTrend")
            okb = np.array_equal(np.array(buy), r["buy"])
            oks = np.array_equal(np.array(sell), r["sell"])
            P(f"   BUY: {'MATCH' if okb else 'DIFF'} ({int(sum(buy))}), SELL: {'MATCH' if oks else 'DIFF'} ({int(sum(sell))})")
            allok &= okb and oks
    P(f" PORT CHECK RESULT: {'all match, no port fix needed' if allok else 'DIFFERENCES FOUND'}")
    return allok


def data_checks(ctx, spr, flag, rep):
    P("== DATA CHECKS ==")
    for tf in ("Minute", "Minute5", "Minute15", "Hour"):
        d = pd.read_parquet(os.path.join(DATA, f"{SYM}_{tf}.parquet"), columns=["Date"])
        h = find_holes(pd.DatetimeIndex(d.Date), 72)
        P(f" {tf}: {len(d)} bars {d.Date.min():%d/%m/%Y %H:%M} - {d.Date.max():%d/%m/%Y %H:%M}; find_holes(72h): {h if h else 'none'}; dup dates {int(d.Date.duplicated().sum())}")
    g = np.diff(ctx.t).astype("timedelta64[m]").astype(int)
    idx = np.flatnonzero(g > 10)
    rows = pd.DataFrame({"a": ctx.t[idx], "b": ctx.t[idx + 1], "m": g[idx]})
    brk = rows.a.dt.hour.isin([16, 17, 18, 19, 20, 21, 22]) & rows.b.dt.hour.isin([17, 18, 19, 20, 21, 22, 23])
    odd = rows[~brk]
    P(f" m1 gaps > 10 min: {len(rows)}; not session break (start 16-22 UTC, end 17-23 UTC): {len(odd)}")
    for _, r in odd.iterrows():
        P(f"   {pd.Timestamp(r.a):%d/%m/%Y %H:%M} -> {pd.Timestamp(r.b):%d/%m/%Y %H:%M} ({r.m} min)")
    g2 = ((g > 1) & (g <= 10)).sum()
    P(f" m1 gaps of 2..10 min (missing minutes inside a session): {int(g2)}")
    for day in ("2026-08-10", "2026-08-11"):
        k = (ctx.t >= np.datetime64(day)) & (ctx.t < np.datetime64(day) + np.timedelta64(1, "D"))
        m5 = ctx.bars["M5"]
        k5 = (m5.open_t >= np.datetime64(day)) & (m5.open_t < np.datetime64(day) + np.timedelta64(1, "D"))
        P(f" known cTrader-server hole 10-11/08/2026: {day} m1 bars {int(k.sum())}, M5 bars {int(k5.sum())} (a full day is 1365 / 273): "
          + ("NO hole in the US100.cash exports" if k.sum() >= 1300 else "HOLE"))
    P(f" 2m bars: {len(ctx.bars['M2'])}, with missing minutes {ctx.miss[2]} ({ctx.miss[2] / len(ctx.bars['M2']) * 100:.2f} %); "
      f"4m bars: {len(ctx.bars['M4'])}, with missing minutes {ctx.miss[4]} ({ctx.miss[4] / len(ctx.bars['M4']) * 100:.2f} %)")
    # validate the builder against the exported M5
    b5, miss5 = build_n_min(ctx.m1, 5)
    e5 = ctx.bars["M5"]
    common_t, i1, i2 = np.intersect1d(b5.open_t, e5.open_t, return_indices=True)
    eq = (np.isclose(b5.o[i1], e5.o[i2]) & np.isclose(b5.h[i1], e5.h[i2]) & np.isclose(b5.l[i1], e5.l[i2]) & np.isclose(b5.c[i1], e5.c[i2]))
    P(f" builder validation: m1-built 5m vs exported Minute5: {len(common_t)} common bars, OHLC identical on {eq.mean() * 100:.3f} %; "
      f"bars only in built {len(b5) - len(common_t)}, only in exported {len(e5) - len(common_t)}")
    P(f" spread: {rep}")
    yr = pd.DatetimeIndex(ctx.t).year
    P(" spread flag by year (0 real, 1 substituted, 2 estimate): " + "; ".join(
        f"{y}: {(flag[yr == y] == 0).mean() * 100:.0f}/{(flag[yr == y] == 1).mean() * 100:.0f}/{(flag[yr == y] == 2).mean() * 100:.0f} %" for y in sorted(set(yr))))
    P(f" spread median points by year: " + "; ".join(f"{y}: {np.median(spr[yr == y]):.2f}" for y in sorted(set(yr))))
    P(f" swap snapshot: long {load_swap()[0]} short {load_swap()[1]} points per night (Friday x3), one date 25/10/2026")


def counts_report(sig, mode):
    c = pd.DataFrame(sig.counts, columns=["setup", "stage", "year", "n"])
    t = c.pivot_table(index=["setup", "stage"], columns="year", values="n", aggfunc="sum", fill_value=0)
    t["all"] = t.sum(1)
    t = t.reset_index()
    t["setup"] = t.setup.map(lambda s: SETUP_NAMES[s])
    t["stage"] = pd.Categorical(t.stage, ["raw", "filter", "window"])
    t = t.sort_values(["setup", "stage"])
    P(f"\n== SIGNAL COUNTS BEFORE OUTCOMES ({mode}); raw = HTF signal bars after warm-up, filter = after the filter series, window = at the m1 entry minute ==")
    P(md(t, "{:.0f}"))
    return t


def mod_test(ctx, sig, mode):
    P(f"\n== ENTRY-MINUTE TEST ({mode}): clock minute (UTC) of the entry m1 bar mod N; causal expects 0, look-ahead expects 1 ==")
    mm = ctx.t.astype("datetime64[m]").astype(np.int64)
    for s, N in ((0, 5), (1, 4), (2, 2), (3, 60)):
        di = np.flatnonzero(sig.en_dir[s] != 0)
        r = mm[di] % N
        want = 0 if mode == "causal" else 1
        P(f" {SETUP_NAMES[s]}: entries {len(di)}, minute mod {N} == {want}: {np.mean(r == want) * 100:.2f} %"
          + ("" if np.mean(r == want) == 1 else f" (others: {dict(zip(*np.unique(r[r != want], return_counts=True)))} - gap-delayed entries)"))


def truncation(cfg, full_ctx, full_sig, full_tr):
    P("\n== TRUNCATION INVARIANCE (3 cuts): world truncated at the cut; signals on [0, n_cut) must equal the full run; closed trades must equal "
      "the full run's trades exiting before the cut (gross layer; spread substitution medians are a cost estimate, not a signal) ==")
    cuts = ["2022-06-01T13:00", "2023-09-15T09:00", "2025-03-03T20:00"]
    allok = True
    for k, cs in enumerate(cuts):
        cut = np.datetime64(cs, "ns")
        t0 = time.time()
        cx = Ctx(cut=cut)
        I = compute_ind(cx, cfg, label=f"cut{k}")
        sg = build_signals(cx, I, "causal", cfg)
        nc = cx.n
        ok_sig = all(np.array_equal(getattr(sg, a)[:, :nc], getattr(full_sig, a)[:, :nc]) for a in ("en_dir", "en_stop", "ex_flag"))
        tr = run(cx, sg, np.zeros(nc))
        ft = full_tr[full_tr.xi < nc]
        cols = ["setup", "dir", "ei", "xi", "epx", "xpx", "rsn"]
        tcl = tr[tr.rsn != 9][cols].reset_index(drop=True)
        ok_tr = tcl.equals(ft[cols].reset_index(drop=True))
        open_tr = tr[tr.rsn == 9]
        fopen = full_tr[(full_tr.ei < nc) & (full_tr.xi >= nc)]
        ok_open = (len(open_tr) == len(fopen)) and (len(open_tr) == 0 or (open_tr.ei.iloc[0] == fopen.ei.iloc[0] and open_tr.setup.iloc[0] == fopen.setup.iloc[0]))
        # standalone setups too
        ok_alone = True
        for s in range(4):
            en = [1 if q == s else 0 for q in range(4)]
            a = run(cx, sg, np.zeros(nc), enabled=en)
            f = run(full_ctx, full_sig, np.zeros(full_ctx.n), enabled=en)
            a = a[a.rsn != 9][cols].reset_index(drop=True)
            f = f[f.xi < nc][cols].reset_index(drop=True)
            ok_alone &= a.equals(f)
        P(f" cut {cs} UTC (m1 bars {nc}): signals identical {ok_sig}; system trades before cut identical {ok_tr} (n={len(tcl)}); "
          f"open-at-cut trade matches {ok_open}; each setup alone identical {ok_alone}  [{time.time() - t0:.0f} s]")
        allok &= ok_sig and ok_tr and ok_open and ok_alone
    P(f" TRUNCATION RESULT: {'PASS' if allok else 'FAIL'}")
    return allok


if __name__ == "__main__":
    t0 = time.time()
    man = {}
    for tf in ("Minute", "Minute5", "Minute15", "Hour"):
        p = os.path.join(DATA, f"{SYM}_{tf}.parquet")
        man[p] = {"bytes": os.path.getsize(p), "sha256": sha256(p)}
    for p in (SPR_PATH, SWAP_PATH):
        man[p] = {"bytes": os.path.getsize(p), "sha256": sha256(p)}
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    P("input manifest written:", {os.path.basename(k): v["sha256"][:12] for k, v in man.items()})
    ctx = Ctx()
    spr, flag, rep = load_spread(ctx)
    data_checks(ctx, spr, flag, rep)
    # NY clock check: tick-volume peak at the cash open in both DST regimes
    mo = pd.DatetimeIndex(ctx.t).month
    for lab, w in (("winter (Dec-Feb)", np.isin(mo, [12, 1, 2])), ("summer (Jun-Aug)", np.isin(mo, [6, 7, 8]))):
        g = pd.Series(ctx.m1.tv[w]).groupby(ctx.tod[w]).mean()
        P(f" NY clock check {lab}: tick-volume peak minute {g.idxmax() // 60:02d}:{g.idxmax() % 60:02d} NY; 09:30 / 09:29 ratio {g[570] / g[569]:.2f}; 16:00 / 15:59 ratio {g[960] / g[959]:.2f}")
    port_checks(ctx)
    cfg = Cfg()
    I = compute_ind(ctx, cfg)
    for mode in ("causal", "lookahead"):
        sg = build_signals(ctx, I, mode, cfg)
        counts_report(sg, mode).to_csv(os.path.join(OUT, f"signal_counts_{mode}.csv"), index=False)
        mod_test(ctx, sg, mode)
    sig = build_signals(ctx, I, "causal", cfg)
    full_tr = run(ctx, sig, np.zeros(ctx.n))
    P(f"\nfull-run gross system trades (for the truncation reference): {len(full_tr)}")
    truncation(cfg, ctx, sig, full_tr)
    P(f"\nstage 0 done in {time.time() - t0:.0f} s")
