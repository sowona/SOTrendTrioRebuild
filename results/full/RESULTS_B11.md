# RESULTS_B11: TT1 "Trend Trio" rebuilt on US100.cash (08/11/2026)

*(Copied from the author's research folder on 09/11/2026; only internal file paths were replaced. Not included in this repo: the spec `SPEC_B11.md` (summarised in `METHOD.md`) and the video review.)*

Spec: `SPEC_B11.md`. Video review: (not included). Scripts: `scripts/b11_common.py` (data, indicators, signals, numba portfolio simulator,
stats), `scripts/b11_stage0.py`, `scripts/b11_run.py`. Outputs and full generated tables: `results/full/`
(`stage0.txt`, `tables.md`, `stage*.csv`, `manifest.json` with input sha256, `run_log.txt`; no parquet written).
Units: index points per trade; NQ $ = points x 20 (basis ignored). Eras E1 2020-23 / E2 2024-26 (by entry date). Signals start 04/01/2021 (indicator warm-up),
so E1 is really 04/01/2021-2023. All times New York with DST. Data end: 06/11/2026 21:48 UTC (screen); replication windows end 05/11/2026 as his.

## Headline

1. The rebuild does NOT reproduce his result. Causal, his own cost model (gross prices, $4.28 a round trip, no slippage): the full system makes
   +$154k on 3,012 trades in his TradingView window (his +$356k on 2,200), PF 1.1 (his 1.34), closed-trade drawdown $61k (his $27k). In the last 12 months
   it is -$4k (his +$123k). Win rate is close (40.7 % vs his 39.4 %), PnL and PF are not.
2. Setup 1 alone is the closest match: 466 trades, +$70.7k, 39.9 %, PF 1.3 in his window (his 438, +$120.9k, 43.8 %, PF 1.56); 2021 alone -$6.3k (his
   shown red year 2021 -$6.2K); 152 trades / +$13k in 12 months (his 141 / +$34.7k).
3. Look-ahead: forming-bar signals would inflate PnL about 10 times (whole sample, alone) and push the win rate to 56-71 %. His win rates (37-44 %) and trade timestamps match closed
   bars, so the signals are not look-ahead. A look-ahead in the cross-timeframe FILTERS only (15m SuperTrend, 15m Sling Shot) is a different matter: it lifts
   setup 1 to his level (586 trades, +$135k, 42.0 %, PF 1.4 vs his 438 / +$120.9k / 43.8 % / 1.56) and the system by 34 % ($207k), and cannot be seen in any
   timestamp. It does not close the whole gap.
4. Under our protocol nothing passes. Causal, net of real spread and swap, the system earns -0.09 pt/trade (E1) and +0.32 (E2), CIs [-2.35, 1.90] and
   [-2.76, 3.61]. Gross it earns +1.7 / +2.7 pts a trade (about $34 / $53 per NQ contract); real spread takes about 1.0 / 1.5 pts and swap about 0.8 / 0.9 pts.
   Costs eat the edge. No setup beats the random-entry control in both eras.
5. Where the gross profit is: setup 2 (Ultimate MA, any hour, no stop). Its 574 trades held over a rollover (12 % of trades) make +12.8k pts net of swap;
   its 4,150 intraday / same-night trades lose -14.7k pts. That is long drift capture on a drifting index, not signal edge.

## Port fixes

None. SuperTrend and AlphaTrend were read line by line against the Pine in the spec and also checked numerically: a literal scalar re-implementation of the
spec text (written independently in `b11_stage0.py`) matches the ports exactly on real US100.cash slices: SuperTrend (3,500 M5 bars, mult 2.0 and 3.0, changeATR
true and false: up, dn, trend, buy flags all match); AlphaTrend (1,500 H1 and 1,500 M5 bars, MFI on TickVolume path and RSI path: AlphaTrend value, BUY, SELL
all match, including the `barssince` alternation filter and Pine na rules). The six existing port tests were rerun: all pass (3 tests each).
Residual risk: the ports and the spec are both recalled Pine, not read from the TradingView source; no TradingView capture comparison exists.

## Stage 0 findings

- Holes: `find_holes(72 h)` finds none in Minute, Minute5, Minute15, Hour. The known 10-11/08/2026 cTrader-server hole is NOT in the US100.cash exports
  (1,365 m1 / 273 M5 bars on both days, a full day). m1 gaps > 10 min outside the daily break: 15, all holidays or early closes (e.g. 02/04/2021, 07/04/2023,
  03/04/2026 Good Friday; 09/01/2025 market closure; 28/11/2025 thin session). 160 gaps of 2-10 min inside sessions. No trade is affected specially.
- 2m / 4m (owner ruling): 1,040,868 2m bars (1,718 = 0.17 % with missing minutes), 521,162 4m bars (3,126 = 0.60 %). Builder validated: the same code builds
  5m bars identical (OHLC, 100.000 % of 416,082) to the exported Minute5.
- NY clock check: tick-volume peak at 09:30 NY in winter and summer (09:30 / 09:29 ratio 1.5), so the DST conversion is right.
- Spread: real spread1m covers 01/12/2021-25/10/2026. In that span 9,237 zero / absent minutes were substituted (same-month hour-of-week median). Before
  01/12/2021 (all 2020 and 91 % of 2021) and 26/10-06/11/2026 (2 % of 2026) there is NO real spread: 357,140 minutes are ESTIMATES (nearest real month's hour-of-week
  profile; 0.60 pt in 2020-21). Median real spread: 0.6 pt (2021) rising to 1.4-1.6 (2023-26). Results for E1 are therefore partly estimated-cost;
  the "E1r 12/2021-2023 (real spread only)" row is reported beside it in `tables.md` / `stage3_screen.csv` and tells the same story.
- Swap: `E1_SWAP.json` US100.cash snapshot of 25/10/2026, one date: long -6.9243, short +0.034 points a night, Friday x3, NY 17:00 rollover. It overstates the
  cost for 2020-23 (rates near zero then) and applies only to nights held (mainly setup 2).
- Signal counts before outcomes (causal; raw HTF signals -> after filter -> at the m1 entry minute inside the window), whole sample 2021-26:
  S1 9,763 -> 3,685 -> 911; S2 18,922 -> 10,294 -> 10,294 (no window); S3 27,425 -> 14,494 -> 1,627; S4 894 -> 488 -> 215. Per-year counts in `stage0.txt`
  and `signal_counts_*.csv` (steady 2021-26, 2026 is 10 months). Look-ahead counts differ mainly for S1 (1,145 window entries, filter evaluated on the forming bar).
- Entry-minute test: causal entries fall on minute 0 mod N (5m 100 %, 2m 100 %, 1h 100 %, 4m 99.75 %; the 26 exceptions are entries delayed over the
  daily break); look-ahead entries fall on 1 mod N, as the review predicted for a forming bar.
- Truncation invariance (3 cuts: 01/06/2022 13:00, 15/09/2023 09:00, 03/03/2025 20:00 UTC): all signal tables (entries, stop distances, exits) on the pre-cut
  minutes identical, system trade list before the cut identical, the trade open at the cut matches, each setup alone identical. PASS. (Gross layer; the
  spread-substitution medians are a cost estimate, not a signal.)

## Stage 1: replication (causal; gross prices, $4.28 fee = 0.214 pt, no spread, no slippage; fresh start at the window start)

| Window | Set | Ours trades | Ours net $ | Win % | PF | Max DD closed $ / minute MTM $ | His trades | His net $ | His win % | His PF | His DD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TV 15/11/2023-05/11/2026 | system | 3,012 | 154,213 | 40.7 | 1.1 | 61,425 / 63,483 | 2,200 | 356,309 | 39.36 | 1.342 | 27,426 |
| TV 15/11/2023-05/11/2026 | S1 alone | 466 | 70,709 | 39.9 | 1.3 | 16,669 / 19,947 | 438 (partly loaded) | 120,870 | 43.8 | 1.564 | 16,513 |
| TV 15/11/2023-05/11/2026 | S2 alone | 2,415 | 110,791 | 40.5 | 1.1 | 56,038 / 56,852 | - | - | - | - | - |
| TV 15/11/2023-05/11/2026 | S3 alone | 589 | 6,761 | 41.4 | 1.0 | 71,120 / 73,716 | - | - | - | - | - |
| TV 15/11/2023-05/11/2026 | S4 alone | 100 | 30,234 | 57.0 | 1.4 | 14,621 / 17,913 | - | - | - | - | - |
| 12 m 06/11/2025-05/11/2026 | system | 974 | -4,006 | 40.2 | 1.0 | - | 712 | 123,258 | 39 | - | - |
| 12 m | S1 alone | 152 | 13,248 | 39.5 | 1.1 | - | 141 | 34,715 | 43 | - | - |
| 12 m | S1+S2 | 856 | 34,189 | 40.1 | 1.1 | - | - | 62,431 | - | - | - |
| 12 m | S2 / S3 / S4 alone | 786 / 186 / 40 | 40,174 / -49,395 / 12,908 | 40.7 / 40.9 / 55.0 | 1.1 / 0.7 / 1.4 | - | - | - | - | - | - |

Per year, system (gross + fee, NQ $K), ours vs his bars:

| Year | Ours trades | Ours $K | Ours win % | His $K |
|---|---|---|---|---|
| 2020 | n/a (data from 02/12/2020) | - | - | 53 |
| 2021 | 1,078 | -8.3 | 37.9 | 22 |
| 2022 | 921 | 52.0 | 39.5 | 102 |
| 2023 | 1,061 | 46.5 | 39.0 | 45 |
| 2024 | 1,017 | 97.7 | 40.2 | 107 |
| 2025 | 1,036 | 45.5 | 40.9 | 138 |
| 2026 to 05/11 | 830 | 4.9 | 40.8 | 98 |

Per year, setups alone (gross + fee, $K): S1 -6.3 / 17.1 / 29.7 / 6.3 / 40.5 / 18.9 (2021-26; trades 168 / 148 / 148 / 149 / 161 / 135, his 145 a year);
S2 17.8 / -1.8 / 59.9 / 70.1 / -11.9 / 44.7; S3 -16.7 / -24.1 / -9.8 / 44.1 / 26.0 / -55.1; S4 -4.5 / 48.0 / 9.2 / 5.5 / 11.9 / 9.3.

Reading: 2023 and 2024 land on his bars (46.5 vs 45, 97.7 vs 107). 2021 and 2022 are about half, and 2025-26 (his best years: 138 and 98) are 45.5 and 4.9. The system
is therefore far from his numbers where it matters most (the recent, unselected-looking years), which is the opposite of what a robust edge would show.
Likely causes, in order: (a) parameters not shown. Our setup 2 alone has 2,415 trades in his three-year window, more than his whole system (2,200, of which 438 are setup 1), so his Ultimate MA (type, length, colour rule) or his Chandelier cannot be the Pine defaults used here; setup 3 and 4 parameters likewise unknown ([Q1]);
(b) cross-timeframe filter alignment: forming-bar filters recover his setup 1 level (stage 2); (c) CFD vs CME futures data: US100.cash 23 h session with 17:00-18:00 NY
break vs NQ ETH, bid-price bars, different tick volume (setup 3 and 4 use MFI on TickVolume; the RSI variant is in stage 4); (d) his 12 m window and TV state are
not frozen ([Q9]).

## Stage 2: look-ahead probe (separate, labelled; NOT causal)

Two probes: `lookahead` = signals AND filters from the forming HTF bar (final value available from the bar's first minute; entry one minute later, so minute 1 mod N);
`lookahead_filters` = signals on closed bars, only the cross-timeframe filters read from the forming bar (S1: 15m SuperTrend; S2: 15m Sling Shot; S3 and S4 filters sit on
the signal bar's own timeframe, so unaffected). Whole sample, alone, gross + fee:

| Set | Mode | Trades | $K | Win % | PF | pts / trade |
|---|---|---|---|---|---|---|
| S1 | causal / filters-only / full look-ahead | 909 / 1,154 / 1,143 | 106 / 240 / 1,180 | 39.5 / 41.8 / 71.2 | 1.25 / 1.45 / 8.79 | 5.8 / 10.4 / 51.6 |
| S2 | causal / filters-only / full | 4,722 / 4,739 / 4,731 | 179 / 248 / 1,788 | 39.5 / 39.7 / 57.6 | 1.10 / 1.13 / 2.65 | 1.9 / 2.6 / 18.9 |
| S3 | causal / filters-only / full | 1,172 / 1,172 / 1,160 | -36 / -36 / 69 | 39.1 / 39.1 / 40.8 | 0.95 / 0.95 / 1.10 | -1.5 / -1.5 / 3.0 |
| S4 | causal / filters-only / full | 215 / 215 / 214 | 79 / 79 / 259 | 56.7 / 56.7 / 70.6 | 1.56 / 1.56 / 3.33 | 18.4 / 18.4 / 60.4 |
| system | causal / filters-only / full | 5,943 / 6,012 / 5,985 | 238 / 326 / 2,344 | 39.7 / 40.0 / 56.4 | 1.09 / 1.12 / 2.41 | 2.0 / 2.7 / 19.6 |

In his TV window: system causal $154k / filters-only $207k / full look-ahead $1.36M (win 57.4 %, PF 2.4, DD $21k); setup 1: $70.7k / $135.3k / $677.8k
(win 39.9 / 42.0 / 70.3 %, PF 1.3 / 1.4 / 8.9) against his $120.9k, 43.8 %, 1.56. Per year, system: full look-ahead $254k-505k a year, filters-only
-2.8 / 70.0 / 58.6 / 99.5 / 90.5 / 10.7 ($K 2021-26), causal -8.3 / 52.0 / 46.5 / 97.7 / 45.5 / 4.9, his 22 / 102 / 45 / 107 / 138 / 98.

What it says plainly: the full look-ahead overshoots his numbers by a factor of about 4-6 and its win rate (57-71 %) is not his (37-44 %), so his signals are not
forming-bar signals; the timestamp pattern in the video agrees. The filters-only probe sits between causal and his numbers for setup 1 (it is in his range on win rate, PF and PnL, with more trades: 586 vs 438) but for the system it still stays at 58 % of his TV-window PnL, and 2025-26 stay far below his bars. So a forming-bar
filter is a candidate explanation for part of setup 1's edge and cannot be excluded for the others, but it does not explain 2025-26. It is not proven and we cannot see his
`request.security` arguments.

## Stage 3: screen (causal, real spread, + swap), points per trade

NET = real spread + swap. 95 % CI by bootstrap over NY entry days (1,000). THIN = n < 300 in an era.

| Item | Era | n | NET mean | 95 % CI | Win % | PF | Hold h | Max DD (pts, closed) |
|---|---|---|---|---|---|---|---|---|
| S1 SuperTrend 5m | E1 | 464 | 3.93 | [-1.95, 10.83] | 39.4 | 1.19 | 1.4 | 1,030 |
| S1 | E2 | 447 | 5.34 | [-3.72, 16.79] | 37.6 | 1.19 | 1.7 | 864 |
| S2 Ultimate MA 4m | E1 | 2,418 | -0.39 | [-2.71, 1.97] | 36.1 | 0.98 | 4.0 | 2,921 |
| S2 | E2 | 2,306 | -0.43 | [-4.15, 3.23] | 38.6 | 0.98 | 4.2 | 4,149 |
| S3 AlphaTrend 2m | E1 | 606 | -4.70 | [-10.56, 1.53] | 36.0 | 0.84 | 1.2 | 2,846 |
| S3 | E2 | 566 | 0.36 | [-7.92, 8.68] | 41.7 | 1.01 | 1.5 | 3,704 |
| S4 AlphaTrend 1h | E1 | 118 THIN | 21.76 | [3.86, 39.47] | 56.8 | 1.74 | 3.6 | 496 |
| S4 | E2 | 97 THIN | 12.47 | [-9.85, 36.62] | 56.7 | 1.33 | 3.8 | 765 |
| System | E1 | 3,062 | -0.09 | [-2.35, 1.90] | 36.7 | 1.00 | 3.2 | 3,761 |
| System | E2 | 2,887 | 0.32 | [-2.76, 3.61] | 39.0 | 1.01 | 3.5 | 3,620 |

Cost layers, mean pts per trade (E1 / E2), gross -> spread -> spread + 1 tick -> NET (spread + swap) -> 1 tick + swap:
S1 4.58 / 7.03 -> 3.94 / 5.48 -> 2.77 / 5.08 -> 3.93 / 5.34 -> 2.76 / 4.94; S2 1.78 / 2.35 -> 0.76 / 0.78 -> 0.26 / 0.28 -> -0.39 / -0.43 -> -0.89 / -0.93;
S3 -3.96 / 1.54 -> -4.68 / 0.41 -> -5.18 / -0.09; S4 22.5 / 13.9 -> 21.8 / 12.5; system 1.69 / 2.67 -> 0.70 / 1.20 -> 0.20 / 0.71 -> -0.09 / 0.32 -> -0.59 / -0.18.
Full CIs for every layer: `tables.md`. Gross CIs already include 0 for S1, S2, S3 and the system in both eras; only S4 gross in E1 excludes 0.

System trades by owner (first signal wins): S2 4,414, S3 932, S1 479, S4 124. Exit reasons: 5,532 signal, 204 flat 16:00, 213 stop. Eight flat exits fell in early-close sessions
(filled at the next open). The system, as portfolio, is almost entirely setup 2: setup 1, 3 and 4 trades are only 26 % of the system trades, because setup 2 is in the market
most of the time and the others wait.

### Controls

(i) Random entry (500 draws): same side, same window of the owning setup, holds permuted within setup and era, same spread layer and swap, no stops in the control.
Day-matched (the spec: same count per NY day) and unconditional (same n drawn from all days of the era):

| Item | Era | Actual NET | Day-matched control mean [2.5 %, 97.5 %] | p | Unconditional control mean [2.5 %, 97.5 %] | p |
|---|---|---|---|---|---|---|
| S1 | E1 | 3.93 | 8.76 [4.10, 12.97] | 0.98 | 0.22 [-6.18, 5.70] | 0.10 |
| S1 | E2 | 5.34 | 9.78 [2.00, 16.96] | 0.88 | -0.92 [-8.88, 7.32] | 0.06 |
| S2 | E1 | -0.39 | 4.28 [1.48, 7.08] | 1.00 | -1.81 [-4.80, 1.37] | 0.19 |
| S2 | E2 | -0.43 | 5.51 [0.83, 9.94] | 1.00 | -1.96 [-6.89, 3.34] | 0.27 |
| S3 | E1 | -4.70 | 3.24 [-1.69, 7.88] | 1.00 | -0.64 [-5.78, 4.64] | 0.92 |
| S3 | E2 | 0.36 | 3.69 [-3.04, 10.35] | 0.81 | -0.97 [-9.94, 8.12] | 0.38 |
| S4 | E1 | 21.76 | 19.79 [8.28, 32.62] | 0.37 | -1.06 [-17.90, 14.90] | 0.002 |
| S4 | E2 | 12.47 | 35.64 [19.43, 54.24] | 0.99 | -1.63 [-29.57, 24.72] | 0.15 |
| System | E1 / E2 | -0.09 / 0.32 | 4.68 / 6.04 | 1.00 / 1.00 | -1.50 / -1.59 | 0.13 / 0.19 |

The day-matched control beats every setup, by a large margin. Reason: the days on which a setup signals are days on which the index already moved the setup's way, so random
entries on those days inherit that day's drift (setup 1: +8.8 pts a trade on signal days vs +0.2 on all days). A control built from the setup's own signal days therefore carries
information the entry could not have had; it is the harsher test and the one the spec asked for. The unconditional control is the fairer null, and only setup 4 in E1 beats it
(p 0.002, n = 118, THIN), not in E2. Both versions fail the PASS rule.

(ii) Always-long drift (gross; mean m1 bar drift in the setup's clock x bars held): setup 1 earns 4.58 / 7.03 pts a trade vs drift-implied 1.36 / -0.15 (excess +3.2 / +7.2 pts, before costs);
setup 2 earns 1.78 / 2.35 vs 0.95 / 1.46 (excess +0.84 / +0.89 pts, smaller than the spread). So setup 2's gross profit is mostly drift; setup 1 is the only item with a gross excess over drift
that exceeds costs, and its CI includes 0.

(iii) Leave-one-setup-out, system NET mean pts (E1 / E2): full -0.09 / 0.32; without S1 -0.69 / -0.48; without S2 +1.51 / +1.50 (CI [-2.79, 5.94] / [-4.86, 9.48]);
without S3 +0.63 / +0.92; without S4 -0.49 / +0.04. Removing the no-stop any-hour setup 2 or the losing setup 3 improves the system; removing setup 1 or 4 worsens it.

Concentration (NET, whole sample): system sum 639 pts, top 1 % of trades (59 trades) sum 22,332 pts, so excluding the top 1 % the system loses 21,693 pts. Setup 1: best single trade
1,761 pts (E2: 74 % of its E2 sum), top 1 % (9 trades) = 113 % of its sum. Setup 4: best trade 12.6 % of the sum, top 1 % 22 %. Setup 3 and 2: ex-top-1 % deeply negative.

Setup 2 by holding class (S2 alone, NET): inside the cash session same day 882 trades, -14.4 pts each (-12,710 total); same night outside cash hours 3,268 trades, -0.6 each (-2,018);
held over one weekday rollover 459 trades, +23.9 net after -6.9 swap (+10,955); held over a weekend 115 trades, +16.0 net after -20.8 swap (+1,838). 12 % of the trades hold all the profit.

System per year, NET spread + swap ($K, points x 20): 2021 -33.3, 2022 +24.2, 2023 +3.6, 2024 +51.2, 2025 +3.5, 2026 -36.5 (to 06/11). Gross, no fee: -3.7, 55.9, 51.1, 102.0, 50.0, 2.0.
Positive years are not "every year green": 2 of 6 negative net, 2 more near zero.

### PASS outcome

PASS = causal, net of real spread + swap, mean CI > 0 in both eras AND beats control (i) in both eras; n < 300 per era = THIN.
No item passes: S1 (CI includes 0 both eras), S2 (negative, CI includes 0), S3 (negative E1), S4 (E1 CI > 0 but E2 includes 0; THIN), system (CI includes 0 both eras).
Only S4 E1 has a CI above 0 (and E1r real-spread-only 35.0 [11.7, 58.8], n = 84), and it fails E2 and the day-matched control. FTMO figures are reserved for a passing item and not computed.

## Stage 4: sensitivity (one at a time, NET, system mean pts E1 / E2 [CI])

| Variant | E1 | E2 | Note |
|---|---|---|---|
| baseline | -0.09 [-2.35, 1.90] n 3,062 | 0.32 [-2.76, 3.61] n 2,887 | |
| SuperTrend multiplier 3.0 (Pine default) | -0.50 [-2.82, 1.80] | -0.05 [-3.24, 3.35] | worse; S1 alone in `tables.md` |
| stop ATR length 10 | -0.17 [-2.44, 1.83] | 0.28 [-2.76, 3.58] | no change |
| AlphaTrend RSI path | -0.21 [-2.27, 1.89] | 0.69 [-2.52, 4.20] | no change in sign |
| AlphaTrend close-and-reverse | -0.58 [-2.77, 1.41] | -0.67 [-3.74, 2.63] | worse |
| tie order random (3 seeds) | -0.12 to -0.14 | 0.29 to 0.30 | no effect |

No variant lifts either era's CI above 0. Reported, not selected.

## Coverage ledger

| Item | Status |
|---|---|
| Setup 1-4 rules as in the review table (signals, filters, windows, stops, exits, portfolio rule) | Implemented, with the defaults for parameters not shown |
| Replication vs his TV window, 12 m, per year | Implemented (2020 and 2011-2019 not testable) |
| Look-ahead probe (full, and filters-only) | Implemented |
| Controls (i) random entry (day-matched and unconditional), (ii) always-long drift for S1 / S2, (iii) leave-one-out | Implemented (control (ii) for S1 / S2 only, as spec) |
| Top 1 %, best trade, S2 overnight vs intraday | Implemented |
| Sensitivity: ST 3.0, stop ATR 10, AlphaTrend RSI, tie random, close-and-reverse | Implemented |
| FTMO fitness | Not computed: nothing passes |
| Placebo of his module-adding procedure (review test design 3), buy-and-hold curve comparison, per-year profit factor, parameters of Ultimate MA / Chandelier / AlphaTrend other than the Pine defaults | Not implemented (outside the spec) |
| 16 of 16 years green, 2011-2019 | Not testable (our data starts 12/2020) |

## Deviations from the spec and choices (all causal and simplest-option)

- Spread before 01/12/2021 and after 25/10/2026 is an estimate (no real spread exists there); E1 is partly estimated-cost. Swap is a one-date snapshot.
- Indicator warm-up: no signal before 04/01/2021.
- Entry windows are start-inclusive, end-exclusive (Pine session convention): 09:30-15:30 means entry minutes 09:30 to 15:29. Window tested on the m1 entry minute.
- Entry at the first m1 open at or after the HTF bar closes (delays only over the daily break, 26 setup 2 entries). Entry price: longs bid + spread, shorts bid.
- Stop = fill price -/+ 2 x ATR(14) of the signal bar (5m for S1, 1h for S4); long stop on bid low, short on ask; fill at the stop or the open if it gaps through.
- Flat at 16:00 fills at the bar-open price of the first m1 bar at or after 16:00 NY (8 early-close sessions fill at the next open).
- AlphaTrend exits (S3, S4) on the unfiltered opposite signal, no window or filter; close only by default: the exiting setup does not re-enter in the same minute.
- Setup 2 enters even when the Chandelier direction is already down; it exits at the next Chandelier sell flip.
- In the 1-tick layer slippage 0.25 pt is applied to every fill including stops.
- Max drawdown: closed-trade (points sorted by exit time) and minute-close mark-to-market; his are TradingView equity figures. Bootstrap resamples NY entry days.
- Random control has no stops; the day-matched control is biased in the control's favour (explained above).
- HC / catalogue row for TT1 not updated (writes are restricted to the B11 folders).

## What the data says, and the next untested item

On US100.cash 2021-26 the Trend Trio, built from the video's rules and Pine defaults, is a high-turnover long-biased system whose gross edge (+1.7 to +2.7 pts a trade) is smaller
than real spread plus swap, whose profit comes from a few long overnight and weekend holds in a drifting index, and whose recent years (2025-26) are the weakest, not the strongest.
His headline (+$356k in three years, PF 1.34) is not reproduced even with his own cost model. Signal look-ahead does not explain it; filter look-ahead can explain part of setup 1.
The remaining gap points at settings he did not show (setup 2's trade count is too high for his totals) and his futures data.

Next untested item (owner's call): ask for or infer the unshown parameters ([Q1]) and re-run setup 2 and the system, because the count mismatch (our S2 alone 2,415 trades in his window vs his whole system 2,200)
says our Ultimate MA / Chandelier is not his; then the filter-timing question ([Q2]) which is the only look-ahead candidate; then the placebo of his module-adding procedure.

## Open points ([Q])

1. [Q1] Ultimate MA type / length / colour rule, Chandelier ATR length / multiplier / close-based, AlphaTrend period / multiplier / MFI vs RSI, stop ATR length: Pine defaults used; setup 2's trade count says they differ from his.
2. [Q2] Filter alignment (15m SuperTrend, 15m Sling Shot, ADX, EMA 200): closed bar used (house default); forming-bar probe in stage 2.
3. [Q3] AlphaTrend "opposite signal": close only used; close-and-reverse in stage 4.
4. [Q4] Window end (15:30 etc.) inclusive or exclusive: exclusive used.
5. [Q5] Swap model for 2020-23 (rates near zero) vs the 25/10/2026 snapshot; US100.cash spread before 12/2021 is unmeasured.
6. [Q6] Should the day-matched random control be kept as the PASS control given its bias toward the control? Both versions fail every item here, so the verdict does not depend on it.
