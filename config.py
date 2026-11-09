"""Path configuration for the Trend Trio rebuild.

Every path comes from `config.toml` (next to this file, not committed; copy `config.example.toml`) or from an environment
variable `TT_<KEY>`; the environment variable wins. A relative path is taken relative to the repository root (the folder of
this file), so `data/sample` works from any working directory.

Keys: DATA_DIR, OUT_DIR, SPREAD1M_PATH, SWAP_PATH (see config.example.toml and DATA.md).
A missing key raises RuntimeError naming the key. There is no default path and no fallback.
"""
import os
import tomllib
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parent
CONFIG_FILE: Path = ROOT / "config.toml"
KEYS = ("DATA_DIR", "OUT_DIR", "SPREAD1M_PATH", "SWAP_PATH")
_file_cfg: dict | None = None


def _load_file() -> dict:
    global _file_cfg
    if _file_cfg is None:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as fh:
                _file_cfg = tomllib.load(fh)
        else:
            _file_cfg = {}
    return _file_cfg


def get(key: str) -> str:
    """Absolute path for `key`: env TT_<key> first, then config.toml. Relative values resolve against the repo root."""
    if key not in KEYS:
        raise KeyError(f"config: unknown key {key} (known: {', '.join(KEYS)})")
    val = os.environ.get("TT_" + key)
    if not val:
        val = _load_file().get(key)
    if val is None or str(val) == "":
        raise RuntimeError(f"config: key {key} is not set. Set TT_{key} in the environment or {key} in {CONFIG_FILE} "
                           f"(copy config.example.toml to config.toml).")
    p = Path(str(val))
    return str(p if p.is_absolute() else (ROOT / p).resolve())
