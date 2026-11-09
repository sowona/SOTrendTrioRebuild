#!/usr/bin/env python3
"""Run the B11 pipeline on the shipped sample (data/sample) and write the September 2025 trades and their summary.

The sample holds US100.cash bars from SAMPLE_START to SAMPLE_END (see data/sample/SAMPLE.md): the months before September
2025 are indicator and portfolio warm-up, trades are scored when their entry is in September 2025, and the days after
30/09 let the last September trades close. The pipeline is the same code as the full run (b11_common via
export_trades.py: causal signals, gross and net layers, swap), only the input paths differ: this script sets DATA_DIR,
SPREAD1M_PATH and SWAP_PATH to data/sample and OUT_DIR (indicator cache) to a fresh temporary folder, whatever
config.toml says.

Run: python scripts/run_sample.py                -> results/sample/trades_2025-09-01_2025-10-01.csv + summary_...csv
     python scripts/run_sample.py --out DIR      -> the same files in DIR (used by check_sample.py)
"""
import argparse
import os
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(REPO, "data", "sample")
SCORE_FROM, SCORE_TO = "2025-09-01", "2025-10-01"          # entries scored: [01/09/2025, 01/10/2025) UTC


def sample_env(out_dir):
    env = dict(os.environ)
    env["TT_DATA_DIR"] = SAMPLE
    env["TT_SPREAD1M_PATH"] = os.path.join(SAMPLE, "US100.cash_spread1m.parquet")
    env["TT_SWAP_PATH"] = os.path.join(SAMPLE, "swap_snapshot_US100.cash_25-10-2026.json")
    env["TT_OUT_DIR"] = out_dir
    return env


def run(out):
    with tempfile.TemporaryDirectory() as work:
        t0 = time.time()
        subprocess.run([sys.executable, os.path.join(REPO, "scripts", "export_trades.py"), "--out", out, "--from", SCORE_FROM, "--to", SCORE_TO],
                       env=sample_env(work), check=True)
        print(f"sample run: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "results", "sample"))
    run(ap.parse_args().out)
