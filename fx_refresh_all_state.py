#!/usr/bin/env python3
"""
fx_refresh_all_state.py

Wrapper that refreshes the full FX technical/state layer in two stages:
1. fx_technical_overlay.py  -> Twelve Data OHLC fetch + technical overlay
2. fx_refresh_portfolio_state.py -> portfolio/state/valuation/scorecard refresh
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run_step(script_name: str) -> None:
    script_path = ROOT / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Missing required script: {script_path}")
    print(f"STEP_START | script={script_name}", flush=True)
    subprocess.run([sys.executable, str(script_path)], check=True)
    print(f"STEP_DONE | script={script_name}", flush=True)


def main() -> None:
    run_step("fx_technical_overlay.py")
    run_step("fx_refresh_portfolio_state.py")
    print("FX_REFRESH_ALL_OK", flush=True)


if __name__ == "__main__":
    main()
