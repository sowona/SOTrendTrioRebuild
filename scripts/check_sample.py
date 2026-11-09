#!/usr/bin/env python3
"""Check the sample run.

1. Runs scripts/run_sample.py into a temporary folder and compares its trade list and summary with results/sample/
   (the expected output shipped with the repo). Text columns and times must be equal; numbers within 1e-5.
2. Compares results/sample/ with the full-period trade list results/full/trades/trades_causal.csv restricted to the same
   entry window: the sample must reproduce the full run's September 2025 trades and summary.
Prints PASS / FAIL for each part, with the first difference. Exit code 0 only if both pass.

Run: python scripts/check_sample.py
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
from run_sample import SCORE_FROM, SCORE_TO, sample_env  # noqa: E402

TAG = f"{SCORE_FROM}_{SCORE_TO}"
EXPECTED = os.path.join(REPO, "results", "sample")
FULL = os.path.join(REPO, "results", "full", "trades", "trades_causal.csv")
ATOL = 1e-5


def first_diff(a, b, what):
    """None if equal, else a text naming the first difference."""
    if list(a.columns) != list(b.columns):
        return f"{what}: columns differ {list(a.columns)} vs {list(b.columns)}"
    if len(a) != len(b):
        return f"{what}: {len(a)} rows vs {len(b)} rows"
    for c in a.columns:
        x, y = a[c].to_numpy(), b[c].to_numpy()
        if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
            x, y = x.astype(float), y.astype(float)
            bad = ~((np.isnan(x) & np.isnan(y)) | (np.abs(x - y) <= ATOL))
        else:
            bad = x.astype(str) != y.astype(str)
        if bad.any():
            i = int(np.flatnonzero(bad)[0])
            return f"{what}: row {i}, column {c}: {x[i]} vs {y[i]}\n  row: {a.iloc[i].to_dict()}"
    return None


def report(name, diffs):
    diffs = [d for d in diffs if d]
    print(f"{name}: {'PASS' if not diffs else 'FAIL'}")
    for d in diffs[:1]:
        print("  first difference -> " + d)
    return not diffs


def main():
    exp_tr = pd.read_csv(os.path.join(EXPECTED, f"trades_{TAG}.csv"))
    exp_sm = pd.read_csv(os.path.join(EXPECTED, f"summary_{TAG}.csv"))
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, os.path.join(REPO, "scripts", "run_sample.py"), "--out", tmp], check=True, stdout=subprocess.DEVNULL)
        new_tr = pd.read_csv(os.path.join(tmp, f"trades_{TAG}.csv"))
        new_sm = pd.read_csv(os.path.join(tmp, f"summary_{TAG}.csv"))
    ok1 = report(f"[1] fresh sample run vs results/sample ({len(new_tr)} trade rows)",
                 [first_diff(new_tr, exp_tr, "trades"), first_diff(new_sm, exp_sm, "summary")])

    full = pd.read_csv(FULL)
    t = pd.to_datetime(full.t_in)
    full = full[(t >= pd.Timestamp(SCORE_FROM)) & (t < pd.Timestamp(SCORE_TO))].reset_index(drop=True)
    # same summary function as the sample run, applied to the full run's rows (export_trades imports b11_common, which reads
    # the config keys at import: point them at the sample, nothing is loaded)
    with tempfile.TemporaryDirectory() as work:
        os.environ.update(sample_env(work))
        import export_trades as ex
        full_sm = ex.summary(full, [(exp_sm.period.iloc[0], np.ones(len(full), bool))]).round(6)
    ok2 = report(f"[2] results/sample vs full-run trades entered {SCORE_FROM} to {SCORE_TO} (excl.) ({len(full)} trade rows)",
                 [first_diff(exp_tr, full, "trades"), first_diff(exp_sm, full_sm, "summary")])
    sys.exit(0 if ok1 and ok2 else 1)


if __name__ == "__main__":
    main()
