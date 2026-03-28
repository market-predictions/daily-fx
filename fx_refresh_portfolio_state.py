#!/usr/bin/env python3
"""
fx_refresh_portfolio_state.py

Refresh the FX portfolio/state artifacts *after* fx_technical_overlay.py has updated
output/fx_technical_overlay.json.

This script intentionally does NOT call Twelve Data itself. It reuses the latest
technical overlay prices so that the expensive/rate-limited OHLC fetch stays in
fx_technical_overlay.py.

It updates:
- output/fx_portfolio_state.json
- output/fx_valuation_history.csv
- output/fx_recommendation_scorecard.csv
- output/fx_state_refresh_manifest.json
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("output")
OVERLAY_PATH = OUTPUT_DIR / "fx_technical_overlay.json"
PORTFOLIO_STATE_PATH = OUTPUT_DIR / "fx_portfolio_state.json"
VALUATION_HISTORY_PATH = OUTPUT_DIR / "fx_valuation_history.csv"
SCORECARD_PATH = OUTPUT_DIR / "fx_recommendation_scorecard.csv"
MANIFEST_PATH = OUTPUT_DIR / "fx_state_refresh_manifest.json"

REPORT_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)
CURRENCY_ORDER = ["USD", "EUR", "JPY", "CHF", "GBP", "AUD", "CAD", "NZD", "MXN", "ZAR"]
CURRENCY_TO_PAIR = {
    "USD": None,
    "EUR": "EURUSD",
    "GBP": "GBPUSD",
    "AUD": "AUDUSD",
    "NZD": "NZDUSD",
    "JPY": "USDJPY",
    "CHF": "USDCHF",
    "CAD": "USDCAD",
    "MXN": "USDMXN",
    "ZAR": "USDZAR",
}
DIRECT_CCYUSD_PAIRS = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}
SCORECARD_HEADERS = [
    "run_date",
    "source_report",
    "currency",
    "action_label",
    "target_weight_pct",
    "entry_price_ccyusd",
    "technical_status",
    "overlay_as_of_utc",
]
VALUATION_HEADERS = [
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
    "overlay_as_of_utc",
]
DEFAULT_ACTIONS = {
    "USD": ("Buy", 36.0),
    "CHF": ("Build on weakness", 13.0),
    "JPY": ("Hold / stage", 13.0),
    "CAD": ("Hold", 10.0),
    "MXN": ("Hold / stage", 8.0),
    "AUD": ("Hold / stage", 8.0),
    "GBP": ("Reduce", 7.0),
    "EUR": ("Reduce", 5.0),
    "NZD": ("Sell / avoid", 0.0),
    "ZAR": ("Sell / avoid", 0.0),
}


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report_file(output_dir: Path) -> Path:
    candidates: list[tuple[str, int, Path]] = []
    for path in output_dir.glob("weekly_fx_review_*.md"):
        match = REPORT_RE.fullmatch(path.name)
        if not match:
            continue
        candidates.append((match.group(1), int(match.group(2) or "0"), path))
    if not candidates:
        raise FileNotFoundError(f"No files found matching output/weekly_fx_review_*.md in {output_dir}")
    candidates.sort(key=lambda row: (row[0], row[1]))
    return candidates[-1][2]


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def latest_close_map(overlay: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for row in overlay.get("pairs", []):
        pair = row.get("pair")
        latest_close = row.get("Evidence", {}).get("latest_close")
        if pair and latest_close is not None:
            out[pair] = float(latest_close)
    return out


def current_price_ccyusd(currency: str, pair_closes: dict[str, float]) -> float:
    if currency == "USD":
        return 1.0
    pair = CURRENCY_TO_PAIR[currency]
    if pair not in pair_closes:
        raise RuntimeError(f"Missing overlay price for {currency} via pair {pair}")
    close = float(pair_closes[pair])
    if pair in DIRECT_CCYUSD_PAIRS:
        return close
    return 1.0 / close


def choose_latest_scorecard_group(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    if not rows:
        return {}
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["run_date"], row["overlay_as_of_utc"], row["source_report"])
        groups.setdefault(key, []).append(row)
    chosen_key = sorted(groups.keys(), key=lambda x: (x[0], x[1], x[2]))[-1]
    return {row["currency"]: row for row in groups[chosen_key]}


def build_scorecard_rows(
    latest_group: dict[str, dict[str, str]],
    overlay: dict,
    latest_report_name: str,
    pair_closes: dict[str, float],
) -> list[dict[str, object]]:
    run_date = str(overlay["as_of_utc"])[:10]
    overlay_ts = str(overlay["as_of_utc"])
    currency_overlay = overlay.get("currencies", {})
    rows: list[dict[str, object]] = []

    for currency in CURRENCY_ORDER:
        template = latest_group.get(currency)
        if template:
            action_label = template["action_label"]
            target_weight_pct = float(template["target_weight_pct"])
        else:
            action_label, target_weight_pct = DEFAULT_ACTIONS[currency]

        rows.append(
            {
                "run_date": run_date,
                "source_report": latest_report_name,
                "currency": currency,
                "action_label": action_label,
                "target_weight_pct": round(target_weight_pct, 1),
                "entry_price_ccyusd": round(current_price_ccyusd(currency, pair_closes), 8),
                "technical_status": currency_overlay.get(currency, {}).get("ta_status", "mixed"),
                "overlay_as_of_utc": overlay_ts,
            }
        )
    return rows


def update_portfolio_state(
    portfolio_state: dict,
    valuation_history_rows: list[dict[str, str]],
    pair_closes: dict[str, float],
    overlay_ts: str,
) -> tuple[dict, dict[str, object]]:
    cash_usd = round(float(portfolio_state["cash_usd"]), 2)
    realized_pnl_usd = round(float(portfolio_state.get("realized_pnl_usd", 0.0)), 2)
    starting_capital_usd = round(float(portfolio_state["starting_capital_usd"]), 2)

    gross_exposure_usd = 0.0
    unrealized_pnl_usd = 0.0

    for pos in portfolio_state.get("positions", []):
        currency = pos["currency"]
        entry_price = float(pos["avg_entry_price_ccyusd"])
        units = float(pos["units_ccy"])
        price = round(current_price_ccyusd(currency, pair_closes), 8)
        market_value = round(units * price, 2)
        pnl = round(units * (price - entry_price), 2)
        pos["current_price_ccyusd"] = price
        pos["market_value_usd"] = market_value
        pos["unrealized_pnl_usd"] = pnl
        gross_exposure_usd += market_value
        unrealized_pnl_usd += pnl

    nav_usd = round(cash_usd + gross_exposure_usd, 2)
    previous_peak = round(float(portfolio_state.get("peak_nav_usd", nav_usd)), 2)
    peak_nav_usd = max(previous_peak, nav_usd)
    since_inception_return_pct = round(((nav_usd / starting_capital_usd) - 1.0) * 100.0, 4)

    existing_drawdown = float(portfolio_state.get("max_drawdown_pct", 0.0))
    current_drawdown_pct = round(((nav_usd / peak_nav_usd) - 1.0) * 100.0, 4) if peak_nav_usd else 0.0
    max_drawdown_pct = round(min(existing_drawdown, current_drawdown_pct), 4)

    history_without_current = [row for row in valuation_history_rows if row.get("overlay_as_of_utc") != overlay_ts]
    previous_nav = nav_usd
    if history_without_current:
        previous_nav = float(history_without_current[-1]["nav_usd"])
    daily_return_pct = round(((nav_usd / previous_nav) - 1.0) * 100.0, 4) if previous_nav else 0.0

    for pos in portfolio_state.get("positions", []):
        pos["current_weight_pct"] = round((float(pos["market_value_usd"]) / nav_usd) * 100.0, 2) if nav_usd else 0.0

    portfolio_state["cash_usd"] = cash_usd
    portfolio_state["realized_pnl_usd"] = realized_pnl_usd
    portfolio_state["nav_usd"] = nav_usd
    portfolio_state["peak_nav_usd"] = peak_nav_usd
    portfolio_state["max_drawdown_pct"] = max_drawdown_pct
    portfolio_state["last_valuation"] = {
        "date": overlay_ts[:10],
        "nav_usd": nav_usd,
        "gross_exposure_usd": round(gross_exposure_usd, 2),
        "net_exposure_usd": round(gross_exposure_usd, 2),
        "unrealized_pnl_usd": round(unrealized_pnl_usd, 2),
        "since_inception_return_pct": since_inception_return_pct,
        "daily_return_pct": daily_return_pct,
        "overlay_as_of_utc": overlay_ts,
    }

    valuation_row = {
        "date": overlay_ts[:10],
        "nav_usd": nav_usd,
        "cash_usd": cash_usd,
        "gross_exposure_usd": round(gross_exposure_usd, 2),
        "net_exposure_usd": round(gross_exposure_usd, 2),
        "realized_pnl_usd": realized_pnl_usd,
        "unrealized_pnl_usd": round(unrealized_pnl_usd, 2),
        "daily_return_pct": daily_return_pct,
        "since_inception_return_pct": since_inception_return_pct,
        "drawdown_pct": max_drawdown_pct,
        "overlay_as_of_utc": overlay_ts,
    }
    return portfolio_state, valuation_row


def upsert_valuation_history(rows: list[dict[str, str]], new_row: dict[str, object]) -> list[dict[str, object]]:
    cleaned = [row for row in rows if row.get("overlay_as_of_utc") != new_row["overlay_as_of_utc"]]
    cleaned.append(new_row)
    cleaned.sort(key=lambda row: row["overlay_as_of_utc"])
    return cleaned


def upsert_scorecard(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, object]],
    latest_report_name: str,
    overlay_ts: str,
) -> list[dict[str, object]]:
    cleaned = [
        row
        for row in existing_rows
        if not (row.get("overlay_as_of_utc") == overlay_ts and row.get("source_report") == latest_report_name)
    ]
    cleaned.extend(new_rows)
    order_index = {code: idx for idx, code in enumerate(CURRENCY_ORDER)}
    cleaned.sort(key=lambda row: (row["run_date"], row["overlay_as_of_utc"], row["source_report"], order_index.get(row["currency"], 999)))
    return cleaned


def build_manifest(latest_report_name: str, overlay: dict, portfolio_state: dict, valuation_row: dict[str, object]) -> dict:
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_report": latest_report_name,
        "overlay_as_of_utc": overlay["as_of_utc"],
        "valuation_source": portfolio_state.get("valuation_source", "overlay reuse"),
        "updated_files": [
            str(PORTFOLIO_STATE_PATH),
            str(VALUATION_HISTORY_PATH),
            str(SCORECARD_PATH),
            str(MANIFEST_PATH),
        ],
        "nav_usd": valuation_row["nav_usd"],
        "cash_usd": valuation_row["cash_usd"],
        "gross_exposure_usd": valuation_row["gross_exposure_usd"],
        "unrealized_pnl_usd": valuation_row["unrealized_pnl_usd"],
        "daily_return_pct": valuation_row["daily_return_pct"],
        "since_inception_return_pct": valuation_row["since_inception_return_pct"],
    }


def main() -> None:
    overlay = load_json(OVERLAY_PATH)
    portfolio_state = load_json(PORTFOLIO_STATE_PATH)
    valuation_history_rows = load_csv_rows(VALUATION_HISTORY_PATH)
    scorecard_rows = load_csv_rows(SCORECARD_PATH)
    latest_report = latest_report_file(OUTPUT_DIR)
    latest_report_name = latest_report.name

    pair_closes = latest_close_map(overlay)
    overlay_ts = str(overlay["as_of_utc"])

    latest_scorecard_group = choose_latest_scorecard_group(scorecard_rows)
    new_scorecard_rows = build_scorecard_rows(latest_scorecard_group, overlay, latest_report_name, pair_closes)

    updated_portfolio_state, valuation_row = update_portfolio_state(
        portfolio_state=portfolio_state,
        valuation_history_rows=valuation_history_rows,
        pair_closes=pair_closes,
        overlay_ts=overlay_ts,
    )
    updated_valuation_history = upsert_valuation_history(valuation_history_rows, valuation_row)
    updated_scorecard = upsert_scorecard(scorecard_rows, new_scorecard_rows, latest_report_name, overlay_ts)
    manifest = build_manifest(latest_report_name, overlay, updated_portfolio_state, valuation_row)

    PORTFOLIO_STATE_PATH.write_text(json.dumps(updated_portfolio_state, indent=2), encoding="utf-8")
    write_csv_rows(VALUATION_HISTORY_PATH, VALUATION_HEADERS, updated_valuation_history)
    write_csv_rows(SCORECARD_PATH, SCORECARD_HEADERS, updated_scorecard)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(
        "FX_STATE_REFRESH_OK | "
        f"report={latest_report_name} | "
        f"overlay={overlay_ts} | "
        f"nav={valuation_row['nav_usd']} | "
        f"cash={valuation_row['cash_usd']}"
    )


if __name__ == "__main__":
    main()
