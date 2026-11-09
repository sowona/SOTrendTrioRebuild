# Trend Trio rebuild: SuperTrend + Ultimate MA + AlphaTrend on US100

An independent rebuild, in python, of the four-setup trend system presented in the YouTube video
"Best TradingView Strategy? 3 Free Trend Indicators Combined" by the channel Technical Trading
(https://www.youtube.com/watch?v=7gx3OPJYazQ), tested on US100.cash CFD data from a cTrader broker account (1-minute bid
bars, December 2020 to November 2026).

The aim is to let anyone check two things: whether the video's headline numbers can be reproduced from its rules, and
whether the system has an edge after realistic costs. Short answer: on this data, no and no. Details and every number
below are in `results/full/`.

- Credit for the strategy and its presentation goes to the video's author. The indicators are the work of their TradingView
  authors: SuperTrend and AlphaTrend (KivancOzbilgic), Ultimate MA and Sling Shot (ChrisMoody), Chandelier Exit (everget),
  plus TradingView's built-in DMI / ADX. The python ports in `indicators/` are independent re-implementations of the
  published logic (see `NOTICE` for the licences of the originals; this repository's code is Apache-2.0, `LICENSE`).
- Not affiliated with the video's author, TradingView or any broker. Not financial advice. Research code, provided as is.
- Contact: questions, corrections or a different result on your own data - please open an issue on this repository.

## 1. The system (as we read it from the video)

| Setup | Signal (timeframe) | Filter | Entry window (New York) | Exit | Side |
|---|---|---|---|---|---|
| S1 | SuperTrend turns up (5m) | SuperTrend up on 15m | 09:30-15:30 | SuperTrend turns down, stop 2 x ATR(5m), flat 16:00 | long |
| S2 | Ultimate MA turns up (4m) | Sling Shot fast EMA above slow (15m) | any hour | Chandelier Exit turns down (4m); no stop, held overnight | long |
| S3 | AlphaTrend buy / sell (2m) | ADX(14) >= 20 (2m) | 09:30-11:30 | opposite AlphaTrend signal, flat 16:00 | both |
| S4 | AlphaTrend buy / sell (1h) | close vs EMA 200 (1h) | 10:00-15:00 | opposite AlphaTrend signal, stop 2 x ATR(1h), flat 16:00 | both |

One position at a time; the first setup to signal owns the trade. Settings not shown in the video use the Pine defaults.
Full rules, settings, execution and cost model: `METHOD.md`. Inputs: `DATA.md`.

## 2. Results (full period)

Units: index points per trade; "NQ $" = points x 20 (US100 and NQ move point for point). E1 = 2021-2023 (signals start
04/01/2021 after indicator warm-up), E2 = 2024 to 06/11/2026. Causal = every higher-timeframe value read from its last
closed bar.

### 2.1 Replication with the video's own cost model

Causal, gross prices, $4.28 commission per round trip, no spread, no slippage, fresh start at the window start.

| Window | Set | Our trades | Our net $ | Our win % | Our PF | Our max DD $ (closed trades) | Video trades | Video net $ | Video win % | Video PF | Video max DD $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15/11/2023-05/11/2026 | system | 3,012 | 154,213 | 40.7 | 1.10 | 61,425 | 2,200 | 356,309 | 39.4 | 1.34 | 27,426 |
| 15/11/2023-05/11/2026 | S1 alone | 466 | 70,709 | 39.9 | 1.29 | 16,669 | 438 | 120,870 | 43.8 | 1.56 | 16,513 |
| 06/11/2025-05/11/2026 | system | 974 | -4,006 | 40.2 | 0.99 | - | 712 | 123,258 | 39 | - | - |
| 06/11/2025-05/11/2026 | S1 alone | 152 | 13,248 | 39.5 | 1.13 | - | 141 | 34,715 | 43 | - | - |

Per year, system, same cost model (NQ $ thousands):

| Year | Our trades | Our $K | Our win % | Video $K |
|---|---|---|---|---|
| 2020 | no data (starts 12/2020) | - | - | 53 |
| 2021 | 1,078 | -8.3 | 37.9 | 22 |
| 2022 | 921 | 52.0 | 39.5 | 102 |
| 2023 | 1,061 | 46.5 | 39.0 | 45 |
| 2024 | 1,017 | 97.7 | 40.2 | 107 |
| 2025 | 1,036 | 45.5 | 40.9 | 138 |
| 2026 (to 05/11) | 830 | 4.9 | 40.8 | 98 |

The win rate is close to the video's; profit, profit factor and drawdown are not. 2023 and 2024 land near the video's bars;
2025 and 2026, its best years, are the rebuild's weakest. Setup 1 alone is the closest match.

### 2.2 Look-ahead probe (not causal, for diagnosis only)

Two variants: "full" = signals and filters read from the still-forming higher-timeframe bar (its final value, known one
minute after it opens); "filters only" = signals on closed bars, only the 15m filters of S1 and S2 from the forming bar.
Whole period, each set alone, video cost model:

| Set | Mode | Trades | NQ $K | Win % | PF | Points / trade |
|---|---|---|---|---|---|---|
| S1 | causal | 909 | 106 | 39.5 | 1.25 | 5.8 |
| S1 | filters only | 1,154 | 240 | 41.8 | 1.45 | 10.4 |
| S1 | full look-ahead | 1,143 | 1,180 | 71.2 | 8.79 | 51.6 |
| system | causal | 5,943 | 238 | 39.7 | 1.09 | 2.0 |
| system | filters only | 6,012 | 326 | 40.0 | 1.12 | 2.7 |
| system | full look-ahead | 5,985 | 2,344 | 56.4 | 2.41 | 19.6 |

In the video's window: system causal $154k, filters only $207k, full look-ahead $1.36M (win rate 57.4 %); S1 alone $70.7k /
$135.3k / $678k (win rate 39.9 / 42.0 / 70.3 %).

Reading: full look-ahead overshoots the video's numbers several times over and its win rate (56-71 %) is far from the
video's (37-44 %), so the video's signals are not forming-bar signals. Reading the 15m filters from the forming bar brings
setup 1 into the video's range (586 trades, $135k, 42.0 %, PF 1.45 in its window, against 438 / $120.9k / 43.8 % / 1.56), and
that kind of look-ahead cannot be seen in trade timestamps. It is a candidate for part of the gap; it does not explain the
system's 2025-26 numbers, and it is not proven.

### 2.3 Screen with realistic costs

Causal, real broker spread + overnight swap (NET). Mean points per trade with a 95 % bootstrap confidence interval
(1,000 resamples of trading days). THIN = fewer than 300 trades in the era.

| Item | Era | n | NET mean | 95 % CI | Win % | PF | Mean hold h |
|---|---|---|---|---|---|---|---|
| S1 SuperTrend 5m | E1 | 464 | 3.93 | [-1.95, 10.83] | 39.4 | 1.19 | 1.4 |
| S1 | E2 | 447 | 5.34 | [-3.72, 16.79] | 37.6 | 1.19 | 1.7 |
| S2 Ultimate MA 4m | E1 | 2,418 | -0.39 | [-2.71, 1.97] | 36.1 | 0.98 | 4.0 |
| S2 | E2 | 2,306 | -0.43 | [-4.15, 3.23] | 38.6 | 0.98 | 4.2 |
| S3 AlphaTrend 2m | E1 | 606 | -4.70 | [-10.56, 1.53] | 36.0 | 0.84 | 1.2 |
| S3 | E2 | 566 | 0.36 | [-7.92, 8.68] | 41.7 | 1.01 | 1.5 |
| S4 AlphaTrend 1h | E1 | 118 THIN | 21.76 | [3.86, 39.47] | 56.8 | 1.74 | 3.6 |
| S4 | E2 | 97 THIN | 12.47 | [-9.85, 36.62] | 56.7 | 1.33 | 3.8 |
| System | E1 | 3,062 | -0.09 | [-2.35, 1.90] | 36.7 | 1.00 | 3.2 |
| System | E2 | 2,887 | 0.32 | [-2.76, 3.61] | 39.0 | 1.01 | 3.5 |

Pass rule: CI above 0 in both eras and better than a random-entry control in both eras. Nothing passes. Before costs the
system makes +1.69 / +2.67 points a trade (E1 / E2); real spread and swap take it to -0.09 / +0.32. Only S4 in E1 has a CI
above 0, on 118 trades, and it fails E2 and the day-matched random control. Sensitivity (SuperTrend multiplier 3.0, stop
ATR 10, AlphaTrend RSI path, close-and-reverse, random tie order) changes no verdict.

### 2.4 Findings

- **Setup 2's profit is overnight holding.** S2 (no stop, any hour) trades held over a weekday rollover: 459 trades,
  +23.9 points each after swap (+10,955 in total); over a weekend: 115 trades, +16.0 each (+1,838). Its 882 trades closed
  inside the same cash session lose -14.4 each (-12,710) and its 3,268 same-night trades lose -0.6 each (-2,018). About 12 %
  of its trades hold all the profit: long exposure to a rising index, not a timing edge.
- **Profit is concentrated.** Whole period, NET: the system's total is +639 points; its top 1 % of trades (59) make +22,332,
  so the other 99 % lose -21,693. S1's single best trade (1,761 points) is 74 % of its E2 total.
- **Unshown settings matter.** Our S2 alone makes 2,415 trades in the video's window, more than the video's whole system
  (2,200). The Ultimate MA / Chandelier settings in the video are therefore not the Pine defaults we had to use.
- **A forming-bar filter is the one look-ahead candidate** (2.2): it lifts S1 to the video's level and the system by 34 %
  in the video's window, and cannot be seen in timestamps.
- **S4 is the only item with a positive CI** (E1 only), and it is THIN: 118 and 97 trades.
- System NET by year (NQ $K): 2021 -33.3, 2022 +24.2, 2023 +3.6, 2024 +51.2, 2025 +3.5, 2026 -36.5 (to 06/11).

## 3. Caveats

- CFD, not futures: US100.cash is a cash-index CFD (bid prices, about 23 h a day, broker tick volume), not CME NQ futures.
  Setups 3 and 4 use money-flow on tick volume, which differs between feeds.
- Real spread exists only from 01/12/2021; earlier months (all of 2020 and most of 2021) and 26/10-06/11/2026 use an
  estimated spread profile. An E1 version restricted to real-spread months is in `results/full/tables.md` and tells the
  same story.
- Swap comes from one broker snapshot (25/10/2026: -6.92 points a night long) applied to every night since 2020; it
  overstates the cost in the near-zero-rate years.
- SuperTrend and AlphaTrend are ported from the Pine logic and checked against an independent literal version of it, not
  against TradingView output; the AlphaTrend buy / sell alternation rule is recalled, not read from the source.
- Settings the video does not show use the Pine defaults (`METHOD.md`); the trade counts say at least the S2 settings differ.
- The video's numbers come from TradingView on futures data, in a window and state we cannot freeze.

## 4. Reproduce

Requirements: Python 3.11+ (developed on 3.14), packages in `requirements.txt` (`pip install -r requirements.txt`).

Sample (shipped, about 2 MB: US100.cash 01/08/2025-02/10/2025, see `data/sample/SAMPLE.md`):

```
cp config.example.toml config.toml        # the example already points at data/sample
python scripts/run_sample.py              # writes results/sample/ (trades entered in September 2025 + summary)
python scripts/check_sample.py            # PASS / FAIL with the first difference
```

`check_sample.py` reruns the sample and checks that (1) the output equals the shipped `results/sample/`, and (2) the
September 2025 trades and summary equal those of the full-period run in `results/full/trades/trades_causal.csv` (all 396
trade rows: 93 system trades and the setups alone, gross and net). August 2025 is warm-up; one month is enough for an exact
match. Run time: a few seconds (plus numba compilation on the first run).

Port tests (plain python): `python indicators/test_supertrend_port.py` and the five other `indicators/test_*.py`
(they read the last 2,000 5m bars of `DATA_DIR`; the sample is enough).

Full period:

1. Export US100.cash (or your symbol) Minute, Minute5, Minute15 and Hour bars, a per-minute spread file and a swap
   value as described in `DATA.md`; set `DATA_DIR`, `SPREAD1M_PATH`, `SWAP_PATH` and `OUT_DIR` in `config.toml`
   (`OUT_DIR` must not be shared with a run on other data: it holds an indicator cache keyed by settings only).
2. `python scripts/b11_stage0.py` (data checks, port checks, signal counts, truncation test -> `OUT_DIR/stage0.txt`).
   Its port-check slices and truncation cuts assume the full 2020-2026 history.
3. `python scripts/b11_run.py` (stages 1-4 -> `OUT_DIR/tables.md` and the stage CSVs).
4. `python scripts/export_trades.py --out <folder>` (trade lists and per-era summary).

Measured on the author's machine (2.08 M one-minute bars): stage 0 about 1 min, run about 2-3 min, export about 40 s. With the
same input files (sha256 in `results/full/manifest.json`) the outputs equal `results/full/` apart from run times.

## 5. Layout

```
README.md, METHOD.md, DATA.md, LICENSE (Apache-2.0), NOTICE, requirements.txt
config.example.toml, config.py   paths (DATA_DIR, OUT_DIR, SPREAD1M_PATH, SWAP_PATH); env TT_<KEY> overrides; no defaults
indicators/      Pine ports used (pine_common, supertrend, ultimate_ma, slingshot, chandelier, alphatrend, dmi), their
                 tests, PROVENANCE.md
scripts/         b11_common.py (data, indicators, signals, simulator, stats), b11_stage0.py, b11_run.py,
                 export_trades.py, run_sample.py, check_sample.py, common.py (find_holes)
data/sample/     two-month input sample + SAMPLE.md
results/full/    full-period outputs: tables.md (all generated tables), stage*.csv, signal_counts_*.csv, stage0.txt,
                 run_log.txt, manifest.json (input sha256), RESULTS_B11.md (the research write-up),
                 trades/trades_causal.csv + summary_causal.csv (every trade, each setup alone and the system, gross and net)
results/sample/  expected output of the sample run
```
