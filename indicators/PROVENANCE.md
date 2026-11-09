# Provenance of the indicator ports

Python ports of TradingView Pine indicators, copied on 09/11/2026 from the author's shared python indicator library
(`Common/SOStrategiesBB/PyIndicatorPorts/` in his private research tree). They are independent re-implementations of the
published Pine logic (see each module's docstring for what was read and what was recalled); they contain no Pine source.

| File | sha256 of the source file at copy time | Changed in this repo |
|---|---|---|
| pine_common.py | 95f2d2a80312e7df681c986568432b25f73c7732fd4c496b3d58b75cfbec1ed0 | yes: the test-data path `DEFAULT_PARQUET` now comes from `config.py` (`<DATA_DIR>/US100.cash_Minute5.parquet`) instead of a fixed local path |
| supertrend_port.py | 8c1437ea3a003a5fe77f26d65aeada86494355e37230382dbab17d895438ca0b | no |
| ultimate_ma_port.py | 6c4beac98f3b74e20c27db5bfcefeee1c5f9f11b694e25349aab5ace487bf8ad | no |
| slingshot_port.py | 464254f2715dc67369b13214d690b8c7ebcd116d4f105a8ddeb506794249cfc4 | no |
| chandelier_port.py | 00be0d95f323d0761e479b45b9df1e7a8561c4d18250d290b4c08d600442724e | no |
| alphatrend_port.py | 8f158d866d278f015ada442b3d55daec05f03807917e6de4b90d283413a0d574 | no |
| dmi_port.py | 2f102c36066e22dd32970c047fdeb3b6addd20eb4c8a4d4add8d7e078eac35c3 | no |
| test_alphatrend_port.py | 5d8d3c5408aea1a10855a3abcd8a8ba90fb7c9f28f211d2cce967d8cf9bb3b94 | no |
| test_chandelier_port.py | 02f64e6ad762895d4fbde29dbe358965a9018b959726a74e1491da7baad4ebdf | no |
| test_dmi_port.py | 663faac4b8f2ae321d0f8a9a5ede88fa0c5a577c7f63cb31f92a4ce2c5950092 | no |
| test_slingshot_port.py | 7c628ed70af02e22b3425616ce937e07274f166cd549a529ed3ac3be1922d2b9 | no |
| test_supertrend_port.py | 572cde9ff2e6913f364cb687922d330e62408e70891f4022494af64adc1ecfba | no |
| test_ultimate_ma_port.py | 9146c69ead72a445b5b468a7ced0d3e1298f12d92afb41998df00944b762ee16 | no |

Other copied code:

| File | Source | sha256 of the source file | Note |
|---|---|---|---|
| scripts/common.py | the author's `SOMultiMAsPullbackRider/Research/scripts/common.py` | aef0d9ea7931bfc544cba124f3903e21399a30d536d72b973edc6f9c94804395 | only the function `find_holes` (unchanged), the one name B11 imports |
| scripts/b11_common.py | B11 research folder | e0f4ea938c3e4a4a3e4ec6e762dec2fa235199d557a2d78079fdd517b92a714f | paths -> `config.py`, `os.path.join`; logic unchanged |
| scripts/b11_stage0.py | B11 research folder | 84b180c3d0e40af6b608f40bcd9eade4a9cebfe84b66d6ce7e9b04b7a87677e7 | same |
| scripts/b11_run.py | B11 research folder | 72c99b9dc0a9a61b7b5f076f571dec7c0721a6d43cd21774189836099118222d | same |

Line endings were normalised to LF. `export_trades.py`, `run_sample.py` and `check_sample.py` were written for this repo.

Run the tests (plain python, no pytest), with `DATA_DIR` set (the shipped sample is enough):

```
python indicators/test_supertrend_port.py      # likewise for the five other test_*.py; each ends with "ALL OK"
```
