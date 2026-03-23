#!/usr/bin/env python3
"""
fx_technical_overlay.py

Standalone FX technical overlay for the Weekly FX Review.
It fetches daily price data directly from Twelve Data, computes a light
technical status per pair, resamples weekly candles locally from daily data,
and then translates pair verdicts into currency-level technical confirmation
scores.

Design goals:
- no dependency on prediction.py or its outputs
- no entry / stop / take-profit logic
- robust against Twelve Data per-minute rate limits
- scalable if more FX pairs are added later
"""

from __future__ import annotations

import json
import os
import statistics
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque

import requests

API_URL = "https://api.twelvedata.com/time_series"
OUTPUT_PATH = Path("output/fx_technical_overlay.json")
API_KEY = os.environ.get("TWELVEDATA_API_KEY", "").strip()

# Keep this map easy to extend later. The rate limiter below will continue to work
# even if more pairs are added and multiple pauses are needed.
PAIR_MAP = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "AUDUSD": "AUD/USD",
    "NZDUSD": "NZD/USD",
    "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF",
    "USDCAD": "USD/CAD",
    "USDMXN": "USD/MXN",
    "USDZAR": "USD/ZAR",
}

PAIR_TO_CURRENCIES = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "AUDUSD": ("AUD", "USD"),
    "NZDUSD": ("NZD", "USD"),
    "USDJPY": ("USD", "JPY"),
    "USDCHF": ("USD", "CHF"),
    "USDCAD": ("USD", "CAD"),
    "USDMXN": ("USD", "MXN"),
    "USDZAR": ("USD", "ZAR"),
}

ALL_CURRENCIES = ["USD", "EUR", "JPY", "CHF", "GBP", "AUD", "CAD", "NZD", "MXN", "ZAR"]

# Twelve Data free/cheap tiers are often minute-limited.
# Leave headroom by default and allow override via env var.
MAX_CALLS_PER_MINUTE = int(os.environ.get("TWELVEDATA_CALLS_PER_MINUTE", "8"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("TWELVEDATA_RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_BUFFER_SECONDS = float(os.environ.get("TWELVEDATA_RATE_LIMIT_BUFFER_SECONDS", "1.0"))
MAX_RETRIES = int(os.environ.get("TWELVEDATA_MAX_RETRIES", "5"))
HTTP_TIMEOUT_SECONDS = int(os.environ.get("TWELVEDATA_HTTP_TIMEOUT_SECONDS", "30"))

REQUEST_TIMESTAMPS: Deque[float] = deque()
SESSION = requests.Session()


@dataclass
class PairSignal:
    pair: str
    symbol: str
    w1_bias: str
    d1_bias: str
    alignment: str
    pivot_regime: str
    pivot_zone_fit: str
    pivot_conflict: bool
    technical_score_0_4: float
    verdict: str
    evidence: dict


def require_api_key() -> str:
    if not API_KEY:
        raise RuntimeError("No API key found. Set TWELVEDATA_API_KEY in the environment.")
    return API_KEY


def wait_for_api_slot() -> None:
    """Sliding-window rate limiter that supports any number of future pairs.

    If the pair universe expands, this function will keep pausing as often as
    necessary. It does not assume only one pause will ever be needed.
    """
    now = time.time()
    while REQUEST_TIMESTAMPS and now - REQUEST_TIMESTAMPS[0] >= RATE_LIMIT_WINDOW_SECONDS:
        REQUEST_TIMESTAMPS.popleft()

    if len(REQUEST_TIMESTAMPS) < MAX_CALLS_PER_MINUTE:
        REQUEST_TIMESTAMPS.append(now)
        return

    sleep_for = RATE_LIMIT_WINDOW_SECONDS - (now - REQUEST_TIMESTAMPS[0]) + RATE_LIMIT_BUFFER_SECONDS
    if sleep_for > 0:
        print(
            f"RATE_LIMIT_WAIT | sleeping={sleep_for:.1f}s | calls_in_window={len(REQUEST_TIMESTAMPS)} | limit={MAX_CALLS_PER_MINUTE}",
            flush=True,
        )
        time.sleep(sleep_for)

    now = time.time()
    while REQUEST_TIMESTAMPS and now - REQUEST_TIMESTAMPS[0] >= RATE_LIMIT_WINDOW_SECONDS:
        REQUEST_TIMESTAMPS.popleft()
    REQUEST_TIMESTAMPS.append(time.time())


def is_rate_limit_message(message: str) -> bool:
    msg = message.lower()
    return (
        "run out of api credits" in msg
        or "rate limit" in msg
        or "too many requests" in msg
        or "credits for the current minute" in msg
    )


def fetch_series(symbol: str, interval: str, outputsize: int = 260) -> list[dict]:
    params = {
        "apikey": require_api_key(),
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "format": "JSON",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        wait_for_api_slot()

        try:
            response = SESSION.get(API_URL, params=params, timeout=HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt >= MAX_RETRIES:
                raise RuntimeError(f"Network/parse error for {symbol} {interval}: {exc}") from exc
            sleep_for = min(2 ** attempt, 30)
            print(
                f"FETCH_RETRY | symbol={symbol} interval={interval} attempt={attempt}/{MAX_RETRIES} sleep={sleep_for}s reason=network_or_parse",
                flush=True,
            )
            time.sleep(sleep_for)
            continue

        if payload.get("status") == "error":
            message = str(payload.get("message", "Unknown Twelve Data error"))
            if is_rate_limit_message(message) and attempt < MAX_RETRIES:
                # Back off for a full minute plus buffer to survive strict or shared limits.
                sleep_for = RATE_LIMIT_WINDOW_SECONDS + RATE_LIMIT_BUFFER_SECONDS
                print(
                    f"FETCH_RETRY | symbol={symbol} interval={interval} attempt={attempt}/{MAX_RETRIES} sleep={sleep_for:.1f}s reason=rate_limit",
                    flush=True,
                )
                time.sleep(sleep_for)
                continue
            raise RuntimeError(f"Twelve Data error for {symbol} {interval}: {message}")

        values = payload.get("values")
        if not values:
            raise RuntimeError(f"No price data returned for {symbol} {interval}.")

        # API returns newest first; reverse to oldest->newest.
        values = list(reversed(values))
        parsed = []
        for row in values:
            parsed.append(
                {
                    "datetime": row["datetime"],
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                }
            )
        return parsed

    raise RuntimeError(f"Unable to fetch {symbol} {interval} after {MAX_RETRIES} attempts.")


def resample_daily_to_weekly(daily: list[dict]) -> list[dict]:
    """Build weekly OHLC bars from daily data so we only spend one API call per pair."""
    weekly: list[dict] = []
    current_key = None
    bucket = None

    for row in daily:
        dt = datetime.fromisoformat(row["datetime"])
        iso = dt.isocalendar()
        key = (iso.year, iso.week)

        if key != current_key:
            if bucket is not None:
                weekly.append(bucket)
            bucket = {
                "datetime": row["datetime"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
            }
            current_key = key
        else:
            bucket["high"] = max(bucket["high"], row["high"])
            bucket["low"] = min(bucket["low"], row["low"])
            bucket["close"] = row["close"]

    if bucket is not None:
        weekly.append(bucket)

    return weekly


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    out = [values[0]]
    for price in values[1:]:
        out.append(alpha * price + (1 - alpha) * out[-1])
    return out


def pct_change(a: float, b: float) -> float:
    if a == 0:
        return 0.0
    return (b - a) / a


def classify_bias(closes: list[float], ema_fast: list[float], ema_slow: list[float]) -> str:
    if len(closes) < 3 or len(ema_fast) < 3 or len(ema_slow) < 3:
        return "neutral"

    c = closes[-1]
    ef = ema_fast[-1]
    es = ema_slow[-1]
    ef_prev = ema_fast[-3]
    es_prev = ema_slow[-3]
    slope_fast = ef - ef_prev
    slope_slow = es - es_prev

    strong_bull = c > ef > es and slope_fast > 0 and slope_slow >= 0
    strong_bear = c < ef < es and slope_fast < 0 and slope_slow <= 0

    if strong_bull:
        return "bullish"
    if strong_bear:
        return "bearish"
    if c > es and ef >= es:
        return "mild bullish"
    if c < es and ef <= es:
        return "mild bearish"
    return "neutral"


def weekly_pivot_regime(weekly: list[dict], current_price: float) -> tuple[str, str]:
    if len(weekly) < 2:
        return "neutral", "neutral"

    prev = weekly[-2]
    pivot = (prev["high"] + prev["low"] + prev["close"]) / 3
    range_half = max((prev["high"] - prev["low"]) / 2, 1e-9)
    upper_mid = pivot + 0.25 * range_half
    lower_mid = pivot - 0.25 * range_half

    if current_price > upper_mid:
        return "bullish", "above pivot"
    if current_price < lower_mid:
        return "bearish", "below pivot"
    return "neutral", "around pivot"


def median_abs_pct_changes(closes: list[float], lookback: int = 20) -> float:
    if len(closes) < lookback + 1:
        return 0.0
    changes = [abs(pct_change(closes[i - 1], closes[i])) for i in range(len(closes) - lookback, len(closes))]
    return statistics.median(changes) if changes else 0.0


def technical_score(
    w1_bias: str,
    d1_bias: str,
    alignment: str,
    pivot_regime: str,
    pivot_conflict: bool,
) -> float:
    raw_score = 0.0

    if w1_bias == "bullish":
        raw_score += 1.6
    elif w1_bias == "mild bullish":
        raw_score += 1.0
    elif w1_bias == "bearish":
        raw_score -= 1.6
    elif w1_bias == "mild bearish":
        raw_score -= 1.0

    if d1_bias == "bullish":
        raw_score += 1.0
    elif d1_bias == "mild bullish":
        raw_score += 0.6
    elif d1_bias == "bearish":
        raw_score -= 1.0
    elif d1_bias == "mild bearish":
        raw_score -= 0.6

    if alignment == "aligned bullish":
        raw_score += 0.7
    elif alignment == "aligned bearish":
        raw_score -= 0.7

    if pivot_regime == "bullish":
        raw_score += 0.4
    elif pivot_regime == "bearish":
        raw_score -= 0.4

    # Conflict should reduce conviction, not flip the sign.
    if pivot_conflict:
        if raw_score > 0:
            raw_score -= 0.4
        elif raw_score < 0:
            raw_score += 0.4

    raw_score = max(-4.0, min(4.0, raw_score))
    score_0_4 = round((raw_score + 4.0) / 2.0, 2)
    return max(0.0, min(4.0, score_0_4))


def verdict_from_score(score_0_4: float) -> str:
    if score_0_4 >= 3.4:
        return "strong positive"
    if score_0_4 >= 2.6:
        return "positive"
    if score_0_4 >= 1.5:
        return "mixed"
    if score_0_4 >= 0.8:
        return "negative"
    return "strong negative"


def alignment_from_biases(w1_bias: str, d1_bias: str) -> str:
    bullish_set = {"bullish", "mild bullish"}
    bearish_set = {"bearish", "mild bearish"}
    if w1_bias in bullish_set and d1_bias in bullish_set:
        return "aligned bullish"
    if w1_bias in bearish_set and d1_bias in bearish_set:
        return "aligned bearish"
    return "mixed"


def compute_pair_signal(pair: str, symbol: str) -> PairSignal:
    daily = fetch_series(symbol, "1day", 260)
    weekly = resample_daily_to_weekly(daily)

    if len(daily) < 60:
        raise RuntimeError(f"Not enough daily history returned for {pair}. Need at least 60 bars.")
    if len(weekly) < 30:
        raise RuntimeError(f"Not enough weekly history could be built from daily data for {pair}. Need at least 30 bars.")

    closes_d1 = [row["close"] for row in daily]
    closes_w1 = [row["close"] for row in weekly]

    d1_ema20 = ema(closes_d1, 20)
    d1_ema50 = ema(closes_d1, 50)
    w1_ema13 = ema(closes_w1, 13)
    w1_ema26 = ema(closes_w1, 26)

    d1_bias = classify_bias(closes_d1, d1_ema20, d1_ema50)
    w1_bias = classify_bias(closes_w1, w1_ema13, w1_ema26)
    alignment = alignment_from_biases(w1_bias, d1_bias)
    pivot_regime, pivot_zone_fit = weekly_pivot_regime(weekly, closes_d1[-1])

    pivot_conflict = (
        (alignment == "aligned bullish" and pivot_regime == "bearish")
        or (alignment == "aligned bearish" and pivot_regime == "bullish")
    )

    score_0_4 = technical_score(
        w1_bias=w1_bias,
        d1_bias=d1_bias,
        alignment=alignment,
        pivot_regime=pivot_regime,
        pivot_conflict=pivot_conflict,
    )
    verdict = verdict_from_score(score_0_4)

    evidence = {
        "latest_close": round(closes_d1[-1], 6),
        "d1_ema20": round(d1_ema20[-1], 6),
        "d1_ema50": round(d1_ema50[-1], 6),
        "w1_ema13": round(w1_ema13[-1], 6),
        "w1_ema26": round(w1_ema26[-1], 6),
        "recent_d1_median_abs_pct_change": round(median_abs_pct_changes(closes_d1, 20), 6),
        "daily_bars_used": len(daily),
        "weekly_bars_built": len(weekly),
    }

    return PairSignal(
        pair=pair,
        symbol=symbol,
        w1_bias=w1_bias,
        d1_bias=d1_bias,
        alignment=alignment,
        pivot_regime=pivot_regime,
        pivot_zone_fit=pivot_zone_fit,
        pivot_conflict=pivot_conflict,
        technical_score_0_4=score_0_4,
        verdict=verdict,
        evidence=evidence,
    )


def pair_effect_value(verdict: str) -> float:
    mapping = {
        "strong positive": 2.0,
        "positive": 1.0,
        "mixed": 0.0,
        "negative": -1.0,
        "strong negative": -2.0,
    }
    return mapping[verdict]


def status_from_currency_score(score: float) -> str:
    if score >= 1.25:
        return "strong positive"
    if score >= 0.45:
        return "positive"
    if score > -0.45:
        return "mixed"
    if score > -1.25:
        return "negative"
    return "strong negative"


def translate_to_currency_scores(pair_signals: list[PairSignal]) -> dict:
    accumulator = {ccy: {"sum": 0.0, "count": 0, "evidence": []} for ccy in ALL_CURRENCIES}

    for signal in pair_signals:
        base, quote = PAIR_TO_CURRENCIES[signal.pair]
        effect = pair_effect_value(signal.verdict)

        accumulator[base]["sum"] += effect
        accumulator[base]["count"] += 1
        accumulator[base]["evidence"].append(f"{signal.pair} -> {signal.verdict}")

        accumulator[quote]["sum"] -= effect
        accumulator[quote]["count"] += 1
        accumulator[quote]["evidence"].append(f"{signal.pair} -> inverse of {signal.verdict}")

    currencies = {}
    for ccy, payload in accumulator.items():
        avg = payload["sum"] / payload["count"] if payload["count"] else 0.0
        currencies[ccy] = {
            "ta_score": round(avg, 2),
            "ta_status": status_from_currency_score(avg),
            "primary_pair_evidence": payload["evidence"][:4],
            "confirmation_flag": "confirming" if abs(avg) >= 0.45 else "mixed",
        }
    return currencies


def main() -> None:
    pair_signals: list[PairSignal] = []

    for pair, symbol in PAIR_MAP.items():
        print(f"PAIR_START | pair={pair} symbol={symbol}", flush=True)
        pair_signals.append(compute_pair_signal(pair, symbol))
        print(f"PAIR_DONE | pair={pair}", flush=True)

    currencies = translate_to_currency_scores(pair_signals)
    payload = {
        "as_of_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "anchor_currency": "USD",
        "source": "Twelve Data API",
        "rate_limit_config": {
            "calls_per_minute": MAX_CALLS_PER_MINUTE,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            "buffer_seconds": RATE_LIMIT_BUFFER_SECONDS,
        },
        "pairs": [
            {
                "pair": sig.pair,
                "symbol": sig.symbol,
                "W1_Bias": sig.w1_bias,
                "D1_Bias": sig.d1_bias,
                "Alignment": sig.alignment,
                "Pivot_Regime": sig.pivot_regime,
                "Pivot_Zone_Fit": sig.pivot_zone_fit,
                "Pivot_Conflict": sig.pivot_conflict,
                "Technical_Score_0_4": sig.technical_score_0_4,
                "Technical_Verdict": sig.verdict,
                "Evidence": sig.evidence,
            }
            for sig in pair_signals
        ],
        "currencies": currencies,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"OVERLAY_OK | output={OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
