# Data

Every input the pipeline reads, where it comes from and how to rebuild it. Paths are set in `config.toml` (see
`config.example.toml`); `data/sample/` holds a two-month slice of every file (see `data/sample/SAMPLE.md`).
The full run used US100.cash from 02/12/2020 to 06/11/2026 21:48 UTC; input sha256 values are in `results/full/manifest.json`.

## Bars: `<DATA_DIR>/US100.cash_{Minute,Minute5,Minute15,Hour}.parquet`

cTrader bar exports of the US100.cash CFD (a Nasdaq-100 cash index CFD) from the author's broker account.

| Column | Type | Meaning |
|---|---|---|
| Date | datetime64[ns], naive | bar OPEN time, UTC |
| Open, High, Low, Close | float64 | BID prices, index points |
| TickVolume | int64 | number of price ticks in the bar (the only activity measure; "volume" in MFI = tick count) |
| Volume | int64 | all zeros in these exports (not used) |
| Spread | float64 | placeholder written by the exporter (constant), NOT a real spread (not used) |

- The pipeline reads Date, Open, High, Low, Close, TickVolume. Duplicated Dates are dropped, rows sorted.
- 2m and 4m bars are built from the Minute file (see METHOD.md); no other timeframe is rebuilt.
- Session: the CFD trades about 23 h a day with a daily break around 17:00-18:00 New York time; prices are bid.
- Holes: `find_holes` (72 h) finds none in the four exports. A cTrader-server gap known for other symbols on
  10-11/08/2026 (1m / 5m) is not present in these US100.cash files (both days complete). 15 gaps of more than 10 minutes
  outside the daily break are holidays or early closes; 160 gaps of 2-10 minutes inside sessions (listed in
  `results/full/stage0.txt`).

### How to produce the same files

- cTrader: export the bars of the symbol for each timeframe to parquet with the columns above (the author used his own
  export cBot, which writes one `<SYM>_<TF>.parquet` per timeframe from cTrader's bar history; bar time = open, UTC, bid).
- Another 1-minute NQ / US100 source: write the four files with the same column names, UTC open times and one price side
  (bid, or mid with a spread file that matches). Build 5m / 15m / 1h from your 1m data only if your source has no native
  bars, on UTC clock boundaries (5m, 15m, 1h bars on these boundaries are what cTrader exports). If you use futures, set
  the spread to the futures bid/ask spread and the swap to zero (futures have no overnight financing; roll costs are
  different). Results on other data will differ: that is the point of checking.

## Spread: `SPREAD1M_PATH` (`US100.cash_spread1m.parquet`)

| Column | Type | Meaning |
|---|---|---|
| Date | datetime64[ns] | minute (UTC, open time) |
| spread | float64 | median ask - bid of the ticks in that minute, index points |
| ticks | int64 | number of ticks in that minute |

- Built from the cTrader tick history of the same symbol (one row per minute with ticks). Covers 01/12/2021-25/10/2026.
- A spread of 0 means "missing" (the broker's tick history has blocks with ask = bid), as does an absent minute: such
  minutes take the median of the same hour-of-week in the same month. Months with no real spread at all
  (12/2020-11/2021 and 26/10-06/11/2026) take the hour-of-week profile of the nearest real month: those costs are
  ESTIMATES (0.60 pt in 2020-21). Counts per year are printed in `results/full/stage0.txt`.
- Median real spread: about 0.6 pt in 2021, rising to 1.4-1.6 pt in 2023-26.

## Swap: `SWAP_PATH` (JSON)

```
{"symbols": {"US100.cash": {"swap_long": -6.9243, "swap_short": 0.034, ...}}}
```

- Index points per night per unit, as reported by a cTrader backtest on 25/10/2026: one date only. The rebuild applies it
  to every night of 2020-2026; it overstates the cost in 2020-23 when interest rates were near zero.
- Charged at each 17:00 New York rollover a position is held over; Friday counts 3 nights.

## Not used

The video's NQ futures data and TradingView chart values are not available here; no comparison against them is made.
