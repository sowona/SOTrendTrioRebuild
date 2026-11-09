# Method

How the "Trend Trio" system was rebuilt and tested. Code: `scripts/b11_common.py` (data, indicators, signals, simulator,
statistics), `scripts/b11_stage0.py` (checks), `scripts/b11_run.py` (stages 1-4). Results: `results/full/`.

## The system as shown in the video

Four setups on NQ 1-minute charts, entries at the open of the 1-minute bar after the signal bar closes. Times are New York
time (daylight saving aware).

| Setup | Signal (timeframe) | Filter | Entry window (NY) | Exit | Side |
|---|---|---|---|---|---|
| S1 | SuperTrend flips up (5m) | SuperTrend up on 15m | 09:30-15:30 | SuperTrend flips down (5m); stop 2 x ATR(5m); flat at 16:00 | long |
| S2 | Ultimate MA turns up (4m) | Sling Shot fast EMA above slow EMA (15m) | any hour | Chandelier Exit turns down (4m); no stop; no 16:00 flat | long |
| S3 | AlphaTrend buy / sell (2m) | ADX(14) >= 20 (2m) | 09:30-11:30 | opposite AlphaTrend signal; flat at 16:00 | long and short |
| S4 | AlphaTrend buy / sell (1h) | close above / below EMA 200 (1h) | 10:00-15:00 | opposite AlphaTrend signal; stop 2 x ATR(1h); flat at 16:00 | long and short |

Portfolio: one position at a time; the first setup to signal takes it and owns its exit. Same-minute ties: S2, S1, S3, S4.

## Settings

| Item | Value | Source |
|---|---|---|
| SuperTrend | ATR 10, multiplier 2.0, ATR = Wilder (changeATR true) | shown (multiplier); changeATR = Pine default |
| ADX | 14, threshold 20 | shown |
| Sling Shot | EMA 38 / 62 on close, state fast > slow | shown |
| EMA filter | 200 on 1h close | shown |
| Stops | 2 x ATR on the signal bar (5m for S1, 1h for S4), ATR length 14 | multiple shown; length 14 = default (10 tested) |
| Ultimate MA V2 | length 20, type SMA, colour smoothing 2 | not shown -> Pine defaults |
| Chandelier Exit | ATR 22, x 3.0, use close | not shown -> Pine defaults |
| AlphaTrend | coefficient 1, period 14, MFI path on tick volume | not shown -> Pine defaults (RSI path tested) |

Indicator logic is ported from the published Pine scripts (`indicators/`); SuperTrend and AlphaTrend were checked line by
line and numerically against a literal scalar version of the Pine logic written separately (`b11_stage0.py`, port checks).
No comparison against TradingView chart values exists.

## Bars

- 1m, 5m, 15m and 1h bars are the cTrader exports (bid prices), never rebuilt from 1m.
- 2m and 4m bars: no export exists, so (one-off decision for this study) they are built from the 1m bars on clock-minute
  boundaries from 00:00 UTC (2m = minutes 00-01, 02-03, ...; 4m = 00-03, ...): open = first, high = max, low = min,
  close = last, tick volume = sum, stamped at the bar open. A bar with missing minutes is built from the minutes present
  (counted in stage 0). The same builder reproduces the exported 5m bars exactly (100 % of 416,082 bars).
- Warm-up: no signal before 04/01/2021 (data starts 02/12/2020).

## Execution and costs

- Causal: every higher-timeframe value (signal and filter) is read from the last closed bar of its timeframe; a signal on
  a bar closing at t enters at the 1m open at t.
- 1m bars are bid: longs fill at bid + spread, shorts at bid; long stops trigger on the bid low, short stops on the ask
  (bid high + spread); stop fills at the stop price, or at the open when the bar gaps through it. Signal exits and the
  16:00 flat fill at the next 1m open.
- Entry windows are start-inclusive, end-exclusive (09:30-15:30 = entry minutes 09:30 to 15:29).
- Cost layers: gross (bid prices, no spread); real spread; spread + 1 tick (0.25 pt) slippage per fill; NET = real spread
  + swap on nights held. Swap: one broker snapshot (25/10/2026), long -6.9243 / short +0.034 points a night, Friday x3,
  rollover 17:00 NY. The video's commission ($4.28 per NQ round trip = 0.214 pt) is used in the replication only.
- Units: index points per trade; NQ dollars = points x 20 (US100.cash and NQ move point for point; basis ignored).

## Stages

0. Data checks (holes, gaps, 2m / 4m build counts, NY clock check), port checks, signal counts per setup and year before
   any outcome, entry-minute test (causal entries must fall on minute 0 mod N), truncation invariance at 3 cuts (signals
   and trade lists before each cut must equal the full run).
1. Replication against the video's own numbers with its cost model (gross prices, $4.28 fee, no spread, no slippage), in
   its TradingView window 15/11/2023-05/11/2026, its last 12 months, and per year.
2. Look-ahead probe (not causal, labelled): (a) signals and filters from the forming higher-timeframe bar; (b) signals on
   closed bars, only the cross-timeframe filters from the forming bar.
3. Screen: causal, real spread, + 1 tick variant, + swap; per setup and the system, per era (E1 2020-23, E2 2024-26, by
   entry date): n, mean points per trade with a 95 % bootstrap CI (1,000 resamples of New York entry days), win rate,
   profit factor, mean hold, maximum drawdown. Controls: (i) random entry (500 draws; same side, window and permuted holding
   times; day-matched and unconditional versions), (ii) always-long drift for the long-only S1 / S2, (iii) leave one setup
   out. Concentration (best trade, top 1 %), S2 overnight vs intraday profit.
4. Sensitivity, one change at a time, reported not selected: SuperTrend multiplier 3.0, stop ATR length 10, AlphaTrend RSI
   path, AlphaTrend close-and-reverse, random tie order.

## PASS rule

An item passes when, causal and net of real spread + swap, its mean CI is above 0 in both eras AND it beats control (i) in
both eras. n < 300 in an era is flagged THIN.
