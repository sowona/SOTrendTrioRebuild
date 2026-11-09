# Sample data

A slice of the inputs used for the full run, shipped so the pipeline can be run and checked (`scripts/run_sample.py`,
`scripts/check_sample.py`). The full history is broker data and is not included.

- Window: bars with open time from 01/08/2025 00:00 to 02/10/2025 23:59 UTC (end exclusive 03/10/2025).
  - 01/08-31/08/2025: warm-up (indicators and portfolio state). One month was enough: the September trades of the sample run
    equal the full run's September trades exactly (all 396 trade rows, every column).
  - 01/09-30/09/2025: trades scored (entry in September, UTC).
  - 01/10-02/10/2025: tail so the last September trades can close (the last one exits 01/10/2025 10:44 UTC).
  - No known data hole in the window.
- Files are the same rows and columns as the full inputs (see DATA.md), cut to the window, rewritten with pyarrow (zstd).

| File | Rows | sha256 |
|---|---|---|
| US100.cash_Minute.parquet | 61,195 | 71e40c0a72e9174c4832906e8d4fd00f2f23abfe285b13e7ebb00e7c742488aa |
| US100.cash_Minute5.parquet | 12,239 | cbb1586f72ece4f937c256ef469a533da6dc41ce32f86933a0cbf5676bdab27f |
| US100.cash_Minute15.parquet | 4,124 | 5244c01cb5dae9be98710e8fe85ce34b2d51c7b8bad1351b9461340c0ab6743f |
| US100.cash_Hour.parquet | 1,031 | 4ef0040c72109668381a896b881e22ffeb1cca7ebef554124a084a1dfd881756 |
| US100.cash_spread1m.parquet | 61,195 | 56e4258905e3252912dc827162630497c4fa0f282ff7fa9049b4dd32111f990f |
| swap_snapshot_US100.cash_25-10-2026.json | - | aa238cfcef095ea463a7355cde1300039dd6762bea49d4fe3e893e61b36cbb9c |

The swap file holds only the US100.cash entry of the author's broker swap snapshot (25/10/2026).
