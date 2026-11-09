#!/usr/bin/env python3
"""test_slingshot_port - plain python (no pytest): python test_slingshot_port.py"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pine_common as pc
import slingshot_port as ss


def test_hand():
    c = [100 + 5 * math.sin(i * 0.7) + 0.3 * i for i in range(40)]
    fast, slow = 5, 9
    af, as_ = 2 / (fast + 1), 2 / (slow + 1)
    ef, es = [c[0]], [c[0]]
    for i in range(1, len(c)):
        ef.append(af * c[i] + (1 - af) * ef[-1])
        es.append(as_ * c[i] + (1 - as_) * es[-1])
    r = ss.slingshot(c, fast, slow)
    for i in range(len(c)):
        assert abs(r["ema_fast"][i] - ef[i]) < 1e-12 and abs(r["ema_slow"][i] - es[i]) < 1e-12
        assert bool(r["state"][i]) == (ef[i] > es[i])
    # first two bars by hand: ema[1] = alpha*c1 + (1-alpha)*c0
    assert abs(r["ema_fast"][1] - (af * c[1] + (1 - af) * c[0])) < 1e-12
    print("hand check: ok, flips of state =", int(sum(r["state"][i] != r["state"][i - 1] for i in range(1, len(c)))))


def test_truncation(n_bars=300):
    d = pc.load_us100_m5_tail(n_bars)
    pc.assert_truncation_invariant(lambda m: ss.slingshot(d["close"][:m]), n_bars, atol=1e-9)
    print("truncation invariance: ok (3 cuts)")


def test_real():
    d = pc.load_us100_m5_tail(2000)
    r = ss.slingshot(d["close"])
    st = r["state"].astype(int)
    flips = int((st[1:] != st[:-1]).sum())
    print(f"US100 M5 last 2000 bars: flips={flips} last fast={r['ema_fast'][-1]:.2f} slow={r['ema_slow'][-1]:.2f} state={st[-1]}")


if __name__ == "__main__":
    test_hand()
    test_truncation()
    test_real()
    print("ALL OK")
