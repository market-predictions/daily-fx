#!/usr/bin/env python3
"""
fx_portfolio_engine.py

First production-oriented blueprint for a USD-base FX pair portfolio engine.

Purpose
-------
1. Read the latest Weekly FX Review markdown from output/
2. Parse Section 13 (Final action table) as the authoritative target allocation
3. Fetch latest completed daily closes from Twelve Data
4. Convert raw pairs into synthetic CCYUSD prices
5. Rebalance the model portfolio into target weights
6. Mark-to-market the portfolio
7. Persist:
   - output/fx_portfolio_state.json
   - output/fx_trade_ledger.csv
   - output/fx_valuation_history.csv

Important assumptions for v1
----------------------------
- Base currency is always USD.
- Targets come from Section 13 of the latest report.
- USD target weight becomes cash.
- Non-USD target weights become currency sleeves valued through CCYUSD.
- Execution uses the latest completed daily close fetched from Twelve Data.
- Fees default to zero unless FX_TRADE_FEE_BPS is set.
- Current reports currently use positive target weights only; the engine also supports
  negative target weights if you later choose an alpha long/short book.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import requests

API_URL = "https://api.twelvedata.com/time_series"
OUTPUT_DIR = Path("output")
STATE_PATH = OUTPUT_DIR / "fx_portfolio_state.json"
LEDGER_PATH = OUTPUT_DIR / "fx_trade_ledger.csv"
VALUATION_HISTORY_PATH = OUTPUT_DIR / "fx_valuation_history.csv"

BASE_CURRENCY = "USD"
STARTING_CAPITAL_USD = float(os.environ.get("FX_PORTFOLIO_STARTING_CAPITAL_USD", "100000"))
PORTFOLIO_MODE = os.environ.get("FX_PORTFOLIO_MODE", "client_long_bias")
API_KEY = os.environ.get("TWELVEDATA_API_KEY", "").strip()
TRADE_FEE_BPS = float(os.environ.get("FX_TRADE_FEE_BPS", "0"))
HTTP_TIMEOUT_SECONDS = int(os.environ.get("TWELVEDATA_HTTP_TIMEOUT_SECONDS", "30"))
MAX_CALLS_PER_MINUTE = int(os.environ.get("TWELVEDATA_CALLS_PER_MINUTE", "8"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("TWELVEDATA_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_BUFFER_SECONDS = float(os.environ.get("TWELVEDATA_RATE_LIMIT_BUFFER_SECONDS", "1.0"))

REQUEST_TIMESTAMPS: List[float] = []
SESSION = requests.Session()

PAIR_CONFIG = {
    "EUR": {"raw_pair": "EUR/USD", "synthetic": "EURUSD", "invert": False},
    "GBP": {"raw_pair": "GBP/USD", "synthetic": "GBPUSD", "invert": False},
    "AUD": {"raw_pair": "AUD/USD", "synthetic": "AUDUSD", "invert": False},
    "NZD": {"raw_pair": "NZD/USD", "synthetic": "NZDUSD", "invert": False},
    "JPY": {"raw_pair": "USD/JPY", "synthetic": "JPYUSD", "invert": True},
    "CHF": {"raw_pair": "USD/CHF", "synthetic": "CHFUSD", "invert": True},
    "CAD": {"raw_pair": "USD/CAD", "synthetic": "CADUSD", "invert": True},
    "MXN": {"raw_pair": "USD/MXN", "synthetic": "MXNUSD", "invert": True},
    "ZAR": {"raw_pair": "USD/ZAR", "synthetic": "ZARUSD", "invert": True},
    "USD": {"raw_pair": None, "synthetic": "USDUSD", "invert": False},
}

REPORT_PATTERN = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$")
SECTION_13_PATTERN = re.compile(r"## 13\. Final action table\s*(.*?)\s*## 14\.", re.S)


@dataclass
class TargetRow:
    currency: str
    action: str
    target_weight_pct: float
    confidence: str


@dataclass
class TradeEvent:
    trade_id: str
    trade_date: str
    source_report: str
    currency: str
    raw_pair: str
    synthetic_pair: str
    action: str
    units_delta_ccy: float
    execution_price_ccyusd: float
    notional_usd: float
    fee_usd: float
    realized_pnl_usd: float
    post_trade_units_ccy: float
    post_trade_avg_entry_ccyusd: float
    comment: str


def require_api_key() -> str:
    if not API_KEY:
        raise RuntimeError("TWELVEDATA_API_KEY is required.")
    return API_KEY


def wait_for_api_slot() -> None:
    now = time.time()
    global REQUEST_TIMESTAMPS
    REQUEST_TIMESTAMPS = [t for t in REQUEST_TIMESTAMPS if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(REQUEST_TIMESTAMPS) >= MAX_CALLS_PER_MINUTE:
        sleep_for = RATE_LIMIT_WINDOW_SECONDS - (now - REQUEST_TIMESTAMPS[0]) + RATE_LIMIT_BUFFER_SECONDS
        if sleep_for > 0:
            time.sleep(sleep_for)
        now = time.time()
        REQUEST_TIMESTAMPS = [t for t in REQUEST_TIMESTAMPS if now - t < RATE_LIMIT_WINDOW_SECONDS]
    REQUEST_TIMESTAMPS.append(time.time())


def fetch_latest_daily_close(symbol: str) -> float:
    wait_for_api_slot()
    response = SESSION.get(
        API_URL,
        params={
            "apikey": require_api_key(),
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 2,
            "format": "JSON",
        },
        timeout=HTTP_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") == "error":
        raise RuntimeError(f"Twelve Data error for {symbol}: {payload.get('message')}")
    values = payload.get("values")
    if not values:
        raise RuntimeError(f"No daily values returned for {symbol}")
    latest = values[0]
    return float(latest["close"])


def synthetic_ccyusd(currency: str, raw_close: float) -> float:
    cfg = PAIR_CONFIG[currency]
    if cfg["invert"]:
        return 1.0 / raw_close
    return raw_close


def list_reports(output_dir: Path) -> List[Path]:
    files = []
    for p in output_dir.glob("weekly_fx_review_*.md"):
        if REPORT_PATTERN.search(p.name):
            files.append(p)
    return files


def latest_report_path(output_dir: Path) -> Path:
    candidates = []
    for path in list_reports(output_dir):
        m = REPORT_PATTERN.search(path.name)
        if not m:
            continue
        date_part = m.group(1)
        version = int(m.group(2) or 0)
        candidates.append((date_part, version, path.name, path))
    if not candidates:
        raise FileNotFoundError("No weekly_fx_review_*.md report found in output/")
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    return candidates[-1][3]


def parse_section_13_targets(md_text: str) -> List[TargetRow]:
    m = SECTION_13_PATTERN.search(md_text)
    if not m:
        raise RuntimeError("Could not find Section 13 in the report.")
    block = m.group(1).strip()
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    table_lines = [ln for ln in lines if ln.startswith("|")]
    if len(table_lines) < 3:
        raise RuntimeError("Section 13 table appears incomplete.")

    rows: List[TargetRow] = []
    for row in table_lines[2:]:
        parts = [p.strip() for p in row.strip("|").split("|")]
        if len(parts) < 4:
            continue
        currency = parts[0]
        action = parts[1]
        weight = float(parts[2])
        confidence = parts[3]
        rows.append(TargetRow(currency=currency, action=action, target_weight_pct=weight, confidence=confidence))
    return rows


def load_or_init_state(as_of_date: str) -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0",
        "portfolio_mode": PORTFOLIO_MODE,
        "base_currency": BASE_CURRENCY,
        "valuation_source": "Twelve Data latest completed daily bars",
        "inception_date": as_of_date,
        "starting_capital_usd": STARTING_CAPITAL_USD,
        "cash_usd": STARTING_CAPITAL_USD,
        "realized_pnl_usd": 0.0,
        "nav_usd": STARTING_CAPITAL_USD,
        "max_drawdown_pct": 0.0,
        "positions": [],
        "last_rebalance": {"date": as_of_date, "source_report": "", "trades_executed": 0},
        "last_valuation": {
            "date": as_of_date,
            "nav_usd": STARTING_CAPITAL_USD,
            "gross_exposure_usd": 0.0,
            "net_exposure_usd": 0.0,
            "unrealized_pnl_usd": 0.0,
            "since_inception_return_pct": 0.0,
            "daily_return_pct": 0.0,
        },
    }


def positions_by_currency(state: dict) -> Dict[str, dict]:
    return {pos["currency"]: pos for pos in state.get("positions", [])}


def fee_from_notional(notional_usd: float) -> float:
    return abs(notional_usd) * (TRADE_FEE_BPS / 10000.0)


def apply_trade(position: dict | None, delta_units: float, exec_price: float, trade_date: str) -> Tuple[dict | None, float]:
    if abs(delta_units) < 1e-12:
        return position, 0.0

    if position is None:
        position = {
            "units_ccy": 0.0,
            "avg_entry_price_ccyusd": 0.0,
            "opened_date": trade_date,
            "last_rebalanced_date": trade_date,
        }

    current_units = float(position.get("units_ccy", 0.0))
    avg_entry = float(position.get("avg_entry_price_ccyusd", 0.0))
    realized = 0.0

    if abs(current_units) < 1e-12 or (current_units > 0 and delta_units > 0) or (current_units < 0 and delta_units < 0):
        new_units = current_units + delta_units
        if abs(current_units) < 1e-12:
            new_avg = exec_price
        else:
            new_avg = ((abs(current_units) * avg_entry) + (abs(delta_units) * exec_price)) / abs(new_units)
    else:
        closing_units = min(abs(delta_units), abs(current_units))
        realized = closing_units * (exec_price - avg_entry) * (1 if current_units > 0 else -1)
        new_units = current_units + delta_units
        if abs(new_units) < 1e-12:
            new_avg = 0.0
        elif (current_units > 0 and new_units > 0) or (current_units < 0 and new_units < 0):
            new_avg = avg_entry
        else:
            new_avg = exec_price
            position["opened_date"] = trade_date

    position["units_ccy"] = new_units
    position["avg_entry_price_ccyusd"] = new_avg
    position["last_rebalanced_date"] = trade_date
    return position, realized


def mark_to_market(state: dict, price_map: Dict[str, float], valuation_date: str) -> dict:
    gross = 0.0
    net = 0.0
    unrealized = 0.0
    nav = float(state["cash_usd"]) + float(state["realized_pnl_usd"])

    new_positions = []
    for pos in state.get("positions", []):
        currency = pos["currency"]
        price = price_map[currency]
        units = float(pos["units_ccy"])
        market_value = units * price
        pnl = units * (price - float(pos["avg_entry_price_ccyusd"]))
        gross += abs(market_value)
        net += market_value
        unrealized += pnl
        nav += market_value
        current_weight = (market_value / nav * 100.0) if abs(nav) > 1e-12 else 0.0

        pos["current_price_ccyusd"] = round(price, 8)
        pos["market_value_usd"] = round(market_value, 2)
        pos["unrealized_pnl_usd"] = round(pnl, 2)
        pos["current_weight_pct"] = round(current_weight, 2)
        if abs(units) > 1e-10:
            new_positions.append(pos)

    starting_capital = float(state["starting_capital_usd"])
    since_inception = ((nav / starting_capital) - 1.0) * 100.0 if starting_capital else 0.0
    prev_nav = float(state.get("last_valuation", {}).get("nav_usd", starting_capital))
    daily_return = ((nav / prev_nav) - 1.0) * 100.0 if prev_nav else 0.0

    peak_nav = max(prev_nav, nav, starting_capital)
    drawdown = ((nav / peak_nav) - 1.0) * 100.0 if peak_nav else 0.0

    state["positions"] = new_positions
    state["nav_usd"] = round(nav, 2)
    state["max_drawdown_pct"] = min(float(state.get("max_drawdown_pct", 0.0)), drawdown)
    state["last_valuation"] = {
        "date": valuation_date,
        "nav_usd": round(nav, 2),
        "gross_exposure_usd": round(gross, 2),
        "net_exposure_usd": round(net, 2),
        "unrealized_pnl_usd": round(unrealized, 2),
        "since_inception_return_pct": round(since_inception, 4),
        "daily_return_pct": round(daily_return, 4),
    }
    return state


def rebalance_to_targets(state: dict, targets: List[TargetRow], price_map: Dict[str, float], report_name: str, trade_date: str) -> List[TradeEvent]:
    state = mark_to_market(state, price_map, trade_date)
    nav = float(state["nav_usd"])
    positions = positions_by_currency(state)
    trades: List[TradeEvent] = []

    # USD becomes cash target. Everything else becomes position target.
    for idx, target in enumerate(targets, start=1):
        currency = target.currency
        desired_weight = target.target_weight_pct / 100.0
        if currency == "USD":
            continue

        price = price_map[currency]
        target_notional = nav * abs(desired_weight)
        desired_units = (target_notional / price) * (1 if desired_weight >= 0 else -1)
        pos = positions.get(currency)
        current_units = float(pos["units_ccy"]) if pos else 0.0
        delta_units = desired_units - current_units
        if abs(delta_units) < 1e-10:
            if pos:
                pos["target_weight_pct"] = round(target.target_weight_pct, 2)
                pos["action_label"] = target.action
                pos["confidence"] = target.confidence
            continue

        trade_notional = abs(delta_units * price)
        fee = fee_from_notional(trade_notional)
        updated_pos, realized = apply_trade(pos, delta_units, price, trade_date)

        # cash movement: buy (positive delta) consumes cash; sell / short adds cash.
        state["cash_usd"] -= (delta_units * price) + fee
        state["realized_pnl_usd"] += realized

        cfg = PAIR_CONFIG[currency]
        updated_pos.update({
            "currency": currency,
            "raw_pair": cfg["raw_pair"],
            "synthetic_pair": cfg["synthetic"],
            "target_weight_pct": round(target.target_weight_pct, 2),
            "action_label": target.action,
            "confidence": target.confidence,
        })
        positions[currency] = updated_pos

        trade = TradeEvent(
            trade_id=f"{trade_date.replace('-', '')}-{idx:03d}-{currency}",
            trade_date=trade_date,
            source_report=report_name,
            currency=currency,
            raw_pair=cfg["raw_pair"],
            synthetic_pair=cfg["synthetic"],
            action="rebalance",
            units_delta_ccy=round(delta_units, 8),
            execution_price_ccyusd=round(price, 8),
            notional_usd=round(trade_notional, 2),
            fee_usd=round(fee, 2),
            realized_pnl_usd=round(realized, 2),
            post_trade_units_ccy=round(updated_pos["units_ccy"], 8),
            post_trade_avg_entry_ccyusd=round(updated_pos["avg_entry_price_ccyusd"], 8),
            comment=f"{target.action} target {target.target_weight_pct:.2f}%",
        )
        trades.append(trade)

    # Remove zeroed positions from list.
    state["positions"] = [p for p in positions.values() if abs(float(p.get("units_ccy", 0.0))) > 1e-10]

    # Re-mark after trades.
    state = mark_to_market(state, price_map, trade_date)
    state["last_rebalance"] = {
        "date": trade_date,
        "source_report": report_name,
        "trades_executed": len(trades),
    }
    return trades


def append_ledger_rows(trades: List[TradeEvent]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not LEDGER_PATH.exists()
    with LEDGER_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow([
                "trade_id",
                "trade_date",
                "source_report",
                "currency",
                "raw_pair",
                "synthetic_pair",
                "action",
                "units_delta_ccy",
                "execution_price_ccyusd",
                "notional_usd",
                "fee_usd",
                "realized_pnl_usd",
                "post_trade_units_ccy",
                "post_trade_avg_entry_ccyusd",
                "comment",
            ])
        for t in trades:
            writer.writerow([
                t.trade_id,
                t.trade_date,
                t.source_report,
                t.currency,
                t.raw_pair,
                t.synthetic_pair,
                t.action,
                t.units_delta_ccy,
                t.execution_price_ccyusd,
                t.notional_usd,
                t.fee_usd,
                t.realized_pnl_usd,
                t.post_trade_units_ccy,
                t.post_trade_avg_entry_ccyusd,
                t.comment,
            ])


def append_valuation_row(state: dict) -> None:
    last = state["last_valuation"]
    new_file = not VALUATION_HISTORY_PATH.exists()
    with VALUATION_HISTORY_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow([
                "date",
                "nav_usd",
                "cash_usd",
                "gross_exposure_usd",
                "net_exposure_usd",
                "realized_pnl_usd",
                "unrealized_pnl_usd",
                "daily_return_pct",
                "since_inception_return_pct",
                "drawdown_pct",
            ])
        writer.writerow([
            last["date"],
            state["nav_usd"],
            round(state["cash_usd"], 2),
            last["gross_exposure_usd"],
            last["net_exposure_usd"],
            round(state["realized_pnl_usd"], 2),
            last["unrealized_pnl_usd"],
            last["daily_return_pct"],
            last["since_inception_return_pct"],
            round(state.get("max_drawdown_pct", 0.0), 4),
        ])


def write_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def build_price_map(targets: List[TargetRow]) -> Dict[str, float]:
    currencies = sorted({t.currency for t in targets})
    price_map: Dict[str, float] = {"USD": 1.0}
    for ccy in currencies:
        if ccy == "USD":
            continue
        cfg = PAIR_CONFIG.get(ccy)
        if not cfg:
            raise KeyError(f"No PAIR_CONFIG for currency {ccy}")
        raw_close = fetch_latest_daily_close(cfg["raw_pair"])
        price_map[ccy] = synthetic_ccyusd(ccy, raw_close)
    return price_map


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = latest_report_path(OUTPUT_DIR)
    report_name = report_path.name
    report_text = report_path.read_text(encoding="utf-8")
    targets = parse_section_13_targets(report_text)

    trade_date = datetime.now(timezone.utc).date().isoformat()
    state = load_or_init_state(trade_date)
    price_map = build_price_map(targets)
    trades = rebalance_to_targets(state, targets, price_map, report_name, trade_date)

    append_ledger_rows(trades)
    append_valuation_row(state)
    write_state(state)

    print(f"PORTFOLIO_OK | report={report_name} | nav={state['nav_usd']:.2f} | trades={len(trades)}")


if __name__ == "__main__":
    main()
