#!/usr/bin/env python3
"""Trade lists of the causal B11 pipeline, written as CSV (added for the public repo: b11_run.py writes tables, not trade lists).

Same calls as b11_run.py stage 3 (`layers`, without the slippage layer): Ctx -> load_spread -> compute_ind(Cfg()) ->
build_signals(causal) -> run(), for each setup alone and the system, in two cost layers:
  gross = bid prices, no spread (run with a zero spread), swap added in `net`;
  net   = real spread (longs fill at bid + spread, shorts exit at ask) + swap  -> the NET layer of the screen.
Paths come from config.py (DATA_DIR, SPREAD1M_PATH, SWAP_PATH, OUT_DIR; OUT_DIR only holds the indicator cache).

Run: python scripts/export_trades.py --out results/full/trades                       (whole period, summary per era)
     python scripts/export_trades.py --out DIR --from 2025-09-01 --to 2025-10-01      (entries in [from, to), UTC)
Columns: item, layer, setup, dir (+1 long / -1 short), t_in / t_out (UTC, m1 bar open), epx / xpx (fill prices), rsn (1 signal,
2 flat 16:00 NY, 3 stop, 9 end of data), pts (price points net of spread), swap_pts, net = pts + swap_pts, nights, hold_min, era.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b11_common import *  # noqa: E402,F403

ITEMS = [("S1 SuperTrend 5m", (1, 0, 0, 0)), ("S2 UltimateMA 4m", (0, 1, 0, 0)), ("S3 AlphaTrend 2m", (0, 0, 1, 0)),
         ("S4 AlphaTrend 1h", (0, 0, 0, 1)), ("system", (1, 1, 1, 1))]
COLS = ["item", "layer", "setup", "dir", "t_in", "t_out", "epx", "xpx", "rsn", "pts", "swap_pts", "net", "nights", "hold_min", "era"]


def all_trades():
    ctx = Ctx()
    spr_real, _, _ = load_spread(ctx)
    swap = load_swap()
    cfg = Cfg()
    sg = build_signals(ctx, compute_ind(ctx, cfg), "causal", cfg)
    out = []
    for name, en in ITEMS:
        for layer, spr in (("gross", np.zeros(ctx.n)), ("net", spr_real)):
            d = run(ctx, sg, spr, enabled=en, swap=swap)
            d["item"] = name
            d["layer"] = layer
            d["setup"] = d.setup.map(lambda s: SETUP_NAMES[s])
            out.append(d[COLS])
    return pd.concat(out, ignore_index=True)


def summary(tr, groups):
    """groups: list of (label, boolean mask over tr). Per item, layer and group: n, mean / sum of pts and net, win % and PF on net."""
    rows = []
    for name, _ in ITEMS:
        for layer in ("gross", "net"):
            base = (tr["item"] == name) & (tr["layer"] == layer)
            for lab, m in groups:
                x = tr[base & m]
                pf, wr = pf_win(x.net.to_numpy())
                rows.append({"item": name, "layer": layer, "period": lab, "n": len(x), "pts_sum": x.pts.sum(), "pts_mean": x.pts.mean() if len(x) else np.nan,
                             "net_sum": x.net.sum(), "net_mean": x.net.mean() if len(x) else np.nan, "win_pct_net": wr * 100 if wr == wr else np.nan, "pf_net": pf})
    return pd.DataFrame(rows)


def write(tr, sm, out_dir, tag):
    os.makedirs(out_dir, exist_ok=True)
    tr = tr.copy()
    for c in ("t_in", "t_out"):
        tr[c] = pd.to_datetime(tr[c]).dt.strftime("%Y-%m-%d %H:%M")
    tr.to_csv(os.path.join(out_dir, f"trades_{tag}.csv"), index=False, float_format="%.6f")
    sm.to_csv(os.path.join(out_dir, f"summary_{tag}.csv"), index=False, float_format="%.6f")


def window(tr, t_from, t_to):
    t = pd.to_datetime(tr.t_in)
    return tr[(t >= pd.Timestamp(t_from)) & (t < pd.Timestamp(t_to))].reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--from", dest="t_from", help="keep trades entered at or after this UTC date (YYYY-MM-DD)")
    ap.add_argument("--to", dest="t_to", help="keep trades entered before this UTC date (YYYY-MM-DD)")
    a = ap.parse_args()
    tr = all_trades()
    if a.t_from or a.t_to:
        if not (a.t_from and a.t_to):
            sys.exit("--from and --to go together")
        tr = window(tr, a.t_from, a.t_to)
        tag = f"{a.t_from}_{a.t_to}"
        sm = summary(tr, [(f"entries {a.t_from} to {a.t_to} (excl.)", np.ones(len(tr), bool))])
    else:
        tag = "causal"
        sm = summary(tr, [("E1 2020-23", tr.era.to_numpy() == 1), ("E2 2024-26", tr.era.to_numpy() == 2), ("all", np.ones(len(tr), bool))])
    write(tr, sm, a.out, tag)
    print(f"{len(tr)} trades -> {os.path.join(a.out, f'trades_{tag}.csv')}")
    print(sm.to_string(index=False))
