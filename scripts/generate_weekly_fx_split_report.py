#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPORT_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)

DEFAULT_DISCLAIMER = (
    "This report is for informational and educational purposes only and does not constitute "
    "investment advice, a solicitation, or a recommendation to transact in any security, "
    "derivative, fund, or currency. The model portfolio is a rules-based illustrative framework "
    "built for analytical tracking. It does not account for taxes, transaction costs, funding costs, "
    "slippage, implementation constraints, legal restrictions, suitability requirements, or "
    "investor-specific objectives. Market conditions can change rapidly, including because of "
    "central-bank decisions, geopolitical developments, commodity-price shocks, and policy changes. "
    "Any use of this report or its model allocations is at the reader’s own risk."
)

CURRENCY_ORDER = ["USD", "EUR", "JPY", "CHF", "GBP", "AUD", "CAD", "NZD", "MXN", "ZAR"]

ACTION_PRIORITY = {
    "Buy": 5.0,
    "Build on weakness": 4.5,
    "Hold": 3.2,
    "Hold / stage": 3.0,
    "Watch": 2.0,
    "Reduce": 1.0,
    "Sell / avoid": 0.0,
}

TECH_BONUS = {
    "strong positive": 1.0,
    "positive": 0.5,
    "mixed": 0.0,
    "negative": -0.5,
    "strong negative": -1.0,
}

ROLE_TEXT = {
    "USD": "Base, liquidity buffer, defensive anchor",
    "CHF": "Defensive diversifier with cleaner strategic support than JPY",
    "JPY": "Haven sleeve retained, but current technical confirmation is still strongly negative",
    "CAD": "Oil / terms-of-trade support with weaker near-term confirmation",
    "AUD": "Mixed technical overlay offsets part of the cyclical risk",
    "MXN": "Carry-positive macro story, but technical confirmation has weakened to negative",
    "GBP": "Some rate support remains, but strong negative technical confirmation weakens the case",
    "EUR": "Lower-rate bloc with energy sensitivity and strong negative technical confirmation",
    "NZD": "Low-rate recovery story lacks urgency",
    "ZAR": "High-beta EM exposure not paid enough in this regime",
}

ACTION_READS = {
    "USD": "Strongest defensive anchor; supported by rates, liquidity, and broad overlay strength",
    "CHF": "Clean second-line defensive sleeve despite negative technical confirmation",
    "JPY": "Haven logic intact, but still strongly negative on current technical confirmation",
    "CAD": "Oil / terms-of-trade support intact, but weaker domestic growth and negative technical confirmation cap enthusiasm",
    "MXN": "Carry-positive macro story, but technical confirmation has weakened to negative",
    "AUD": "RBA stance remains supportive, but AUD is still only mixed technically and remains cyclical",
    "GBP": "Some rate support, but the technical picture remains strongly negative",
    "EUR": "Lower-rate bloc plus strong negative technical confirmation",
    "NZD": "Recovery story lacks urgency and the overlay remains negative",
    "ZAR": "Wrong exposure for a defensive, oil-shock-aware regime",
}

REVIEW_TEMPLATES = {
    "USD": "The current overlay remains positive for the dollar through broad non-USD weakness. **USD** remains the highest-quality base sleeve.",
    "EUR": "The current overlay remains explicitly strong negative on **EUR**. Macro carry-forward and technical confirmation continue to align to the downside.",
    "JPY": "The macro haven thesis remains intact, but the current overlay still shows a strong negative **JPY** confirmation through **USDJPY** strength. **JPY** remains in the portfolio, but only as a staged hold rather than a larger haven sleeve.",
    "CHF": "**CHF** remains one of the cleanest defensive diversifiers. The current overlay is negative, which tempers sizing, but the broader defensive case remains intact.",
    "GBP": "**GBP** retains some rate support, but the current technical overlay remains strong negative. That keeps **GBP** in reduce territory rather than leadership status.",
    "AUD": "**AUD** is still only mixed on the overlay and remains a cyclical currency in a mild risk-off world. That supports a staged allocation, not aggressive adding.",
    "CAD": "**CAD** still has macro support from oil and terms of trade, but the current overlay for **USDCAD** still argues against stronger conviction. That keeps **CAD** in smaller-hold territory.",
    "NZD": "The strategic case remains weak and the overlay remains negative. That is not enough to justify a rebuild.",
    "MXN": "**MXN** remains carry-positive on macro logic, but the latest overlay has softened to negative and the global backdrop is less friendly to EM carry. That keeps **MXN** in the portfolio, but with a stronger case for disciplined sizing.",
    "ZAR": "**ZAR** remains the wrong kind of exposure for a defensive portfolio with geopolitical and trade-policy awareness. The overlay remains negative and does not rescue the weak strategic case.",
}

PAIR_MAP = {
    "CHF": "USD/CHF -> CHFUSD",
    "JPY": "USD/JPY -> JPYUSD",
    "CAD": "USD/CAD -> CADUSD",
    "MXN": "USD/MXN -> MXNUSD",
    "AUD": "AUD/USD -> AUDUSD",
    "GBP": "GBP/USD -> GBPUSD",
    "EUR": "EUR/USD -> EURUSD",
}

@dataclass
class ScoreRow:
    currency: str
    action_label: str
    target_weight_pct: float
    entry_price_ccyusd: float
    technical_status: str
    overlay_as_of_utc: str
    source_report: str
    run_date: str


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


def next_split_name(split_dir: Path, yymmdd: str) -> str:
    if not split_dir.exists():
        split_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[int] = []
    base_exists = False
    for path in split_dir.glob(f"weekly_fx_review_{yymmdd}*.md"):
        match = REPORT_RE.fullmatch(path.name)
        if not match or match.group(1) != yymmdd:
            continue
        if match.group(2) is None:
            base_exists = True
            candidates.append(0)
        else:
            candidates.append(int(match.group(2)))
    if not candidates:
        return f"weekly_fx_review_{yymmdd}.md"
    if not base_exists:
        return f"weekly_fx_review_{yymmdd}.md"
    return f"weekly_fx_review_{yymmdd}_{max(candidates) + 1:02d}.md"


def parse_sections(text: str) -> dict[int, str]:
    matches = list(SECTION_RE.finditer(text))
    out: dict[int, str] = {}
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        out[int(match.group(1))] = text[start:end].strip()
    return out


def parse_carry_forward_value(section16: str, label: str) -> str | None:
    pattern = re.compile(rf"(?m)^-\s*{re.escape(label)}:\s*(.+?)\s*$")
    m = pattern.search(section16)
    return m.group(1).strip() if m else None


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def latest_score_rows(scorecard_path: Path, preferred_source_report: str | None) -> dict[str, ScoreRow]:
    rows = load_csv_rows(scorecard_path)
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["run_date"], row["overlay_as_of_utc"], row["source_report"])] .append(row)
    if not grouped:
        raise RuntimeError("Recommendation scorecard is empty")
    ranked_keys = sorted(grouped.keys(), key=lambda x: (x[0], x[1], x[2]))
    chosen_key = ranked_keys[-1]
    if preferred_source_report:
        for key in reversed(ranked_keys):
            if key[2] == preferred_source_report:
                chosen_key = key
                break
    chosen_rows = grouped[chosen_key]
    out: dict[str, ScoreRow] = {}
    for row in chosen_rows:
        out[row["currency"]] = ScoreRow(
            currency=row["currency"],
            action_label=row["action_label"],
            target_weight_pct=float(row["target_weight_pct"]),
            entry_price_ccyusd=float(row["entry_price_ccyusd"]),
            technical_status=row["technical_status"],
            overlay_as_of_utc=row["overlay_as_of_utc"],
            source_report=row["source_report"],
            run_date=row["run_date"],
        )
    return out


def fmt_money(value: float) -> str:
    return f"{value:,.2f}"


def fmt_pct(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def overlay_summary(overlay: dict) -> str:
    order = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "MXN", "ZAR"]
    bits = []
    currencies = overlay.get("currencies", {})
    for code in order:
        if code in currencies:
            bits.append(f"**{code}** {currencies[code]['ta_status']}")
    return ", ".join(bits)


def derive_strategic_score(action_label: str, tech_status: str, target_weight_pct: float) -> float:
    base = ACTION_PRIORITY.get(action_label, 0.0) * 3.0
    tech = (TECH_BONUS.get(tech_status, 0.0) + 1.0) * 0.8
    alloc = min(target_weight_pct / 4.0, 3.0)
    return round(base + tech + alloc, 1)


def choose_top_opportunities(scores: dict[str, ScoreRow]) -> list[str]:
    candidates = []
    for code, row in scores.items():
        if row.action_label in {"Reduce", "Sell / avoid"}:
            continue
        value = ACTION_PRIORITY.get(row.action_label, 0.0)
        value += TECH_BONUS.get(row.technical_status, 0.0)
        value += row.target_weight_pct / 20.0
        candidates.append((value, code))
    candidates.sort(reverse=True)
    top: list[str] = []
    for _, code in candidates:
        if code not in top:
            top.append(code)
        if len(top) == 3:
            break
    return top


def position_rows(portfolio_state: dict) -> list[dict]:
    positions = portfolio_state.get("positions", [])
    nav = float(portfolio_state["nav_usd"])
    out = []
    for pos in positions:
        derived_weight = (float(pos["market_value_usd"]) / nav) * 100.0 if nav else 0.0
        out.append(
            {
                "currency": pos["currency"],
                "implementation_pair": PAIR_MAP.get(pos["currency"], pos["raw_pair"]),
                "direction": f"Long {pos['currency']}",
                "entry_date": pos["opened_date"],
                "entry_price": float(pos["avg_entry_price_ccyusd"]),
                "current_price": float(pos["current_price_ccyusd"]),
                "gross_exposure_usd": float(pos["market_value_usd"]),
                "unrealized_pnl_usd": float(pos["unrealized_pnl_usd"]),
                "current_weight_pct": derived_weight,
                "stance": pos["action_label"],
            }
        )
    out.sort(key=lambda row: CURRENCY_ORDER.index(row["currency"]) if row["currency"] in CURRENCY_ORDER else 999)
    return out


def latest_rebalance_rows(trade_ledger_path: Path, source_report: str | None) -> list[dict[str, str]]:
    rows = load_csv_rows(trade_ledger_path)
    if source_report:
        matched = [row for row in rows if row["source_report"] == source_report]
        if matched:
            return matched
    return []


def section_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def build_report(run_date: datetime, output_dir: Path, split_dir: Path) -> tuple[str, Path]:
    latest_report = latest_report_file(output_dir)
    latest_text = latest_report.read_text(encoding="utf-8")
    sections = parse_sections(latest_text)
    section16 = sections.get(16, "")
    section17 = sections.get(17, DEFAULT_DISCLAIMER)

    portfolio_state = load_json(output_dir / "fx_portfolio_state.json")
    overlay = load_json(output_dir / "fx_technical_overlay.json")
    valuation_rows = load_csv_rows(output_dir / "fx_valuation_history.csv")
    last_rebalance = portfolio_state.get("last_rebalance", {})
    score_rows = latest_score_rows(output_dir / "fx_recommendation_scorecard.csv", last_rebalance.get("source_report"))
    positions = position_rows(portfolio_state)
    rebalance_rows = latest_rebalance_rows(output_dir / "fx_trade_ledger.csv", last_rebalance.get("source_report"))

    yymmdd = run_date.strftime("%y%m%d")
    split_name = next_split_name(split_dir, yymmdd)
    split_path = split_dir / split_name

    strategic_regime = parse_carry_forward_value(section16, "Strategic regime") or "mild risk-off / defensive USD bias"
    carry_forward_overlay = parse_carry_forward_value(section16, "Technical overlay state") or "same-day available"
    top_opps = choose_top_opportunities(score_rows)

    lines: list[str] = []
    lines.append("# Weekly FX Review")
    lines.append("")
    lines.append("> *This report is for informational and educational purposes only; please see the disclaimer at the end.*")
    lines.append("")
    lines.append("## 1. Executive summary")
    lines.append("")
    lines.append(
        "This is an **automated state-driven split run** using the latest stored FX report as the strategic carry-forward base, "
        "the latest technical overlay in `output/fx_technical_overlay.json`, and the live implementation files in "
        "`output/fx_portfolio_state.json`, `output/fx_trade_ledger.csv`, and `output/fx_valuation_history.csv`. "
        "Implementation and valuation facts are taken from the state files when they differ from older report text."
    )
    lines.append("")
    lines.append(
        f"The strategic regime remains **{strategic_regime}**. Current live portfolio value is **{fmt_money(float(portfolio_state['nav_usd']))} USD**, "
        f"with cash at **{fmt_money(float(portfolio_state['cash_usd']))} USD**, gross exposure at **{fmt_money(float(portfolio_state['last_valuation']['gross_exposure_usd']))} USD**, "
        f"realized P&L at **{fmt_money(float(portfolio_state['realized_pnl_usd']))} USD**, unrealized P&L at **{fmt_money(float(portfolio_state['last_valuation']['unrealized_pnl_usd']))} USD**, "
        f"and the latest portfolio/overlay timestamp at **{portfolio_state['last_valuation']['overlay_as_of_utc']}**."
    )
    lines.append("")
    opp_text = ", ".join(f"**{code}**" for code in top_opps)
    lines.append(
        f"The current ranking still favors **USD** as the core defensive anchor, with the strongest additional uses of capital now concentrated in {opp_text}. "
        f"This automated generator does **not** perform a fresh live macro research pass; strategy-heavy narrative is therefore refreshed from carry-forward state, while technical, valuation, and implementation facts are updated from the repo’s current state files."
    )
    lines.append("")
    lines.append("## 2. Portfolio action snapshot")
    lines.append("")
    snapshot_rows = []
    for code in CURRENCY_ORDER:
        row = score_rows.get(code)
        if not row:
            continue
        snapshot_rows.append([code, row.action_label, ACTION_READS.get(code, row.technical_status)])
    lines.append(section_table(["Sleeve", "Action", "Current read"], snapshot_rows))
    lines.append("")
    lines.append("## 3. Global macro & FX regime dashboard")
    lines.append("")
    lines.append(f"- **Global macro regime:** {strategic_regime} (carried forward from the latest stored report; no live macro refresh in this automated generator).")
    lines.append("- **Policy divergence:** **USD** remains favored versus lower-rate blocs; **AUD** and **MXN** retain selective support from higher-rate settings, but not enough to override defensive conditions.")
    lines.append("- **Risk regime:** Mild risk-off.")
    lines.append("- **USD liquidity / funding:** Supportive for **USD**.")
    lines.append("- **Commodity impulse:** Supportive for **CAD** in macro terms; selectively constructive for **AUD**; adverse for major energy importers.")
    lines.append(f"- **Technical overlay:** Same-day available; {overlay_summary(overlay)}.")
    lines.append("")
    lines.append("## 4. Structural currency opportunity radar")
    lines.append("")
    radar_rows = [
        ["Dollar liquidity premium", "active / investable", "Elevated uncertainty and defensive funding demand keep **USD** supported."],
        ["Swiss defensive role with intervention risk", "active / investable", "**CHF** remains the cleaner second-line defensive sleeve, though intervention risk caps the upside tail."],
        ["Yen haven asymmetry", "active / watch", "Haven logic remains intact, but the overlay is still strongly negative, so position size should stay controlled."],
        ["Commodity FX recovery", "active / watch", "**CAD** has macro support from oil, while **AUD** benefits from the current rate stance; neither has clean broad confirmation."],
        ["Europe cyclical repair", "fading / under pressure", "Lower relative rates and negative technical confirmation keep **EUR** weak."],
        ["EM carry under controlled volatility", "weakening / watch", "**MXN** remains carry-interesting, but the overlay has softened to negative."],
        ["High-beta EM beta", "invalidated", "**ZAR** remains unattractive into a defensive, oil-shock-aware regime."],
    ]
    lines.append(section_table(["Theme", "Status", "Current read"], radar_rows))
    lines.append("")
    lines.append("## 5. Key risks / invalidators")
    lines.append("")
    lines.append("- A rapid and durable de-escalation in geopolitical risk plus a sharp reversal in oil would reduce the **USD** / **CHF** defensive premium.")
    lines.append("- A decisive broadening of non-U.S. growth plus materially easier Fed pricing would weaken the **USD** overweight case.")
    lines.append("- A clean reversal in **USDJPY** technical strength would improve the case for rebuilding **JPY** more aggressively.")
    lines.append("- A clearer euro-area growth improvement with no renewed energy pressure would improve **EUR**.")
    lines.append("- A broad risk-on reset would help **AUD**, **NZD**, and **ZAR** faster than this framework currently assumes.")
    lines.append("")
    lines.append("## 6. Bottom line")
    lines.append("")
    lines.append(
        "The correct portfolio posture remains **defense first, optionality second, high-beta last**. "
        "**USD** remains the strongest core anchor. **CHF** remains the cleaner secondary defensive allocation than **JPY** on this run. "
        "**CAD**, **AUD**, and **MXN** remain secondary sleeves rather than leadership sleeves. **EUR** and **GBP** stay in reduce territory, "
        "while **NZD** and **ZAR** still do not deserve capital."
    )
    lines.append("")
    lines.append("## 7. Equity curve and portfolio development")
    lines.append("")
    lv = portfolio_state["last_valuation"]
    lines.append(f"Valuation source: **{portfolio_state['valuation_source']}**. Valuation date: **{lv['date']}**. Engine overlay timestamp: **{lv['overlay_as_of_utc']}**.")
    lines.append("")
    lines.append(f"- Net asset value (USD): **{fmt_money(float(portfolio_state['nav_usd']))}**")
    lines.append(f"- Cash (USD): **{fmt_money(float(portfolio_state['cash_usd']))}**")
    lines.append(f"- Gross exposure (USD): **{fmt_money(float(lv['gross_exposure_usd']))}**")
    lines.append(f"- Net exposure (USD): **{fmt_money(float(lv['net_exposure_usd']))}**")
    lines.append(f"- Realized P&L (USD): **{fmt_money(float(portfolio_state['realized_pnl_usd']))}**")
    lines.append(f"- Unrealized P&L (USD): **{fmt_money(float(lv['unrealized_pnl_usd']))}**")
    lines.append(f"- Daily return (%): **{fmt_pct(float(lv['daily_return_pct']))}**")
    lines.append(f"- Since inception return (%): **{fmt_pct(float(lv['since_inception_return_pct']))}**")
    lines.append(f"- Max drawdown (%): **{fmt_pct(float(portfolio_state['max_drawdown_pct']))}**")
    lines.append("")
    lines.append("The equity curve below is sourced from the live portfolio engine and reflects actual mark-to-market updates stored in `output/fx_valuation_history.csv`.")
    lines.append("")
    val_headers = ["Date", "NAV (USD)", "Daily return (%)", "Since inception return (%)", "Drawdown (%)", "Overlay timestamp"]
    val_table_rows = []
    for row in valuation_rows:
        val_table_rows.append([
            row["date"],
            fmt_money(float(row["nav_usd"])),
            fmt_pct(float(row["daily_return_pct"])),
            fmt_pct(float(row["since_inception_return_pct"])),
            fmt_pct(float(row["drawdown_pct"])),
            row["overlay_as_of_utc"],
        ])
    lines.append(section_table(val_headers, val_table_rows))
    lines.append("")
    lines.append("## 8. Currency allocation map")
    lines.append("")
    alloc_rows = []
    for code in CURRENCY_ORDER:
        row = score_rows.get(code)
        if not row:
            continue
        alloc_rows.append([
            code,
            f"{derive_strategic_score(row.action_label, row.technical_status, row.target_weight_pct):.1f}",
            row.action_label,
            ROLE_TEXT.get(code, row.technical_status),
        ])
    lines.append(section_table(["Currency", "Strategic score", "Action", "Role in portfolio"], alloc_rows))
    lines.append("")
    lines.append("## 9. Macro transmission & second-order effects map")
    lines.append("")
    transmission_rows = [
        ["Energy-shock / geopolitical stress", "USD, CHF, CAD", "EUR, NZD, ZAR", "Higher fuel costs raise defensive demand, help energy-linked terms of trade, and hurt importers."],
        ["Fed on hold versus lower-rate blocs", "USD", "EUR, NZD, CHF cash alternatives", "Rate differential and cash carry favor **USD**."],
        ["BoJ normalization from a still-low base", "JPY", "Traditional funding trades versus JPY", "Incremental tightening reduces the structural drag on **JPY**, though price action is not yet confirming."],
        ["Hawkish AUD carry without broad risk-on", "AUD", "Lower-yield cyclical alternatives", "**AUD** gets some rate support, but not enough to become a leadership sleeve in mild risk-off."],
        ["Trade-policy uncertainty", "USD, CHF", "AUD, NZD, ZAR, cyclical EUR rebound trades", "Reduced visibility hurts high-beta currencies and supports liquid defensive anchors."],
    ]
    lines.append(section_table(["Shock / driver", "Likely winners", "Likely losers", "Transmission logic"], transmission_rows))
    lines.append("")
    lines.append("## 10. Current currency review")
    lines.append("")
    for code in CURRENCY_ORDER:
        row = score_rows.get(code)
        if not row:
            continue
        lines.append(f"**{code} — {row.action_label}**")
        lines.append(REVIEW_TEMPLATES.get(code, f"The current technical status is **{row.technical_status}** and the action remains **{row.action_label}**."))
        lines.append("")
    lines.append("## 11. Best new currency opportunities")
    lines.append("")
    opp_reason = {
        "USD": "The strongest base-currency expression remains additional **USD** cash rather than forcing new beta.",
        "CHF": "The cleanest incremental defensive addition because the macro thesis is intact even though the overlay is negative rather than neutral.",
        "JPY": "The haven case remains intact, but rebuilds should stay staged until technical confirmation improves.",
        "CAD": "Oil and terms-of-trade support keep **CAD** interesting, but weaker technical confirmation caps conviction.",
        "AUD": "Not a clean technical buy, but still a better cyclical placeholder than the weaker high-beta alternatives because the overlay is mixed rather than outright broken.",
        "MXN": "Carry remains helpful, but the negative overlay argues for disciplined sizing instead of aggressive adding.",
    }
    for idx, code in enumerate(top_opps, start=1):
        lines.append(f"{idx}. **{code}** — {opp_reason.get(code, 'Remains one of the better available uses of capital in the current state-driven ranking.')}")
    lines.append("")
    lines.append("## 12. Portfolio rotation plan")
    lines.append("")
    rotation_rows = [
        ["Core defense", "USD cash 36%, CHF 13%"],
        ["Defensive optionality", "JPY 13%"],
        ["Secondary macro hold", "CAD 10%"],
        ["Staged cyclicals / carry", "MXN 8%, AUD 8%"],
        ["Reduce / underweight", "GBP 7%, EUR 5%"],
        ["Avoid", "NZD 0%, ZAR 0%"],
    ]
    lines.append(section_table(["Bucket", "Positioning"], rotation_rows))
    lines.append("")
    lines.append("No fresh rebalance is assumed in this automated generator run beyond the authoritative implementation state already stored in the repo.")
    lines.append("")
    lines.append("## 13. Final action table")
    lines.append("")
    final_rows = []
    for code in CURRENCY_ORDER:
        row = score_rows.get(code)
        if not row:
            continue
        confidence = "High" if code == "USD" else ("Medium-High" if row.action_label in {"Reduce", "Sell / avoid"} and row.technical_status in {"negative", "strong negative"} else "Medium")
        final_rows.append([code, row.action_label, f"{row.target_weight_pct:.0f}", confidence])
    lines.append(section_table(["Currency", "Action", "Target weight (%)", "Confidence"], final_rows))
    lines.append("")
    lines.append("## 14. Position changes executed this run")
    lines.append("")
    trades_executed = last_rebalance.get("trades_executed", 0)
    source_report = last_rebalance.get("source_report", "unknown")
    rebalance_date = last_rebalance.get("date", "unknown")
    lines.append(
        "No **additional** position changes are executed inside this automated generator run. "
        f"However, the authoritative implementation state currently reflects a rebalance sourced from `{source_report}`, "
        f"with **{trades_executed} trades executed** on **{rebalance_date}**."
    )
    lines.append("")
    if rebalance_rows:
        trade_table_rows = []
        for row in rebalance_rows:
            trade_table_rows.append([
                row["currency"],
                f"{float(row['units_delta_ccy']):,.4f}",
                f"{float(row['execution_price_ccyusd']):.8f}",
                fmt_money(float(row["notional_usd"])),
                row["comment"],
            ])
        lines.append("Authoritative latest rebalance adjustments already recorded in the trade ledger:")
        lines.append("")
        lines.append(section_table(["Currency", "Units delta", "Execution price (CCYUSD)", "Notional USD", "Comment"], trade_table_rows))
        lines.append("")
    lines.append("## 15. Current portfolio holdings and cash")
    lines.append("")
    lines.append(f"- Starting capital (USD): **{fmt_money(float(portfolio_state['starting_capital_usd']))}**")
    lines.append(f"- Invested market value (USD): **{fmt_money(float(lv['gross_exposure_usd']))}**")
    lines.append(f"- Cash (USD): **{fmt_money(float(portfolio_state['cash_usd']))}**")
    lines.append(f"- Total portfolio value (USD): **{fmt_money(float(portfolio_state['nav_usd']))}**")
    lines.append(f"- Since inception return (%): **{fmt_pct(float(lv['since_inception_return_pct']))}**")
    lines.append(f"- Base currency: **{portfolio_state['base_currency']}**")
    lines.append("")
    lines.append(
        "The holdings below are sourced from the live portfolio-state file. The displayed **Current weight (%)** column is derived deterministically as "
        "`market_value_usd / NAV`, because the stored `current_weight_pct` values in the state file do not reconcile to the NAV/cash totals."
    )
    lines.append("")
    holding_rows = []
    for row in positions:
        holding_rows.append([
            row["currency"],
            row["implementation_pair"],
            row["direction"],
            row["entry_date"],
            f"{row['entry_price']:.8f}",
            f"{row['current_price']:.8f}",
            fmt_money(row["gross_exposure_usd"]),
            fmt_money(row["unrealized_pnl_usd"]),
            f"{row['current_weight_pct']:.2f}",
            row["stance"],
        ])
    holding_rows.append([
        "USD cash",
        "—",
        "Long USD cash",
        portfolio_state["inception_date"],
        "1.00000000",
        "1.00000000",
        fmt_money(float(portfolio_state["cash_usd"])),
        "0.00",
        f"{(float(portfolio_state['cash_usd']) / float(portfolio_state['nav_usd']) * 100.0):.2f}",
        score_rows["USD"].action_label if "USD" in score_rows else "Buy",
    ])
    lines.append(section_table(
        ["Currency sleeve", "Implementation pair", "Direction", "Entry date", "Entry price", "Current price", "Gross exposure (USD)", "Unrealized P&L (USD)", "Current weight (%)", "Stance"],
        holding_rows,
    ))
    lines.append("")
    lines.append("## 16. Carry-forward input for next run")
    lines.append("")
    lines.append("**This section is the canonical default input for the next run unless the user explicitly overrides it.**")
    lines.append("")
    lines.append("- Report type: Weekly FX Review")
    lines.append(f"- Run date: {run_date.strftime('%Y-%m-%d')}")
    lines.append("- Run version: automated-split")
    lines.append(f"- Base currency: {portfolio_state['base_currency']}")
    lines.append(f"- Starting capital: {fmt_money(float(portfolio_state['starting_capital_usd']))}")
    lines.append(f"- Current total portfolio value: {fmt_money(float(portfolio_state['nav_usd']))}")
    lines.append(f"- Cash: {fmt_money(float(portfolio_state['cash_usd']))}")
    lines.append("- Holdings:")
    for row in holding_rows[:-1]:
        lines.append(f"  - {row[0]} {row[8].rstrip('0').rstrip('.') if '.' in row[8] else row[8]}%")
    lines.append(f"  - USD cash {holding_rows[-1][8].rstrip('0').rstrip('.') if '.' in holding_rows[-1][8] else holding_rows[-1][8]}%")
    lines.append(f"- Strategic regime: {strategic_regime}")
    lines.append(f"- Technical overlay state: {carry_forward_overlay}")
    lines.append(f"- Portfolio engine state: live; last valuation date {lv['date']} and latest portfolio-state overlay timestamp {lv['overlay_as_of_utc']}")
    lines.append(f"- Technical overlay as of: {overlay['as_of_utc']}")
    lines.append("- Highest-priority adds next run if thesis improves further: " + ", ".join(top_opps[:2]))
    rebuilds = [code for code in ["JPY", "AUD", "CAD", "EUR"] if code in score_rows]
    lines.append("- First candidates for rebuild if technicals improve: " + ", ".join(rebuilds[:3]))
    softeners = [code for code in ["USD", "CHF", "AUD"] if code in score_rows]
    lines.append("- First candidates for reduction if regime softens: " + ", ".join(softeners[:2]))
    addition = [code for code in ["AUD", "EUR", "CAD"] if code in score_rows]
    lines.append("- First candidates for addition on improved global breadth: " + ", ".join(addition[:2]))
    avoids = [code for code in ["NZD", "ZAR"] if code in score_rows]
    lines.append("- Avoid unless regime changes materially: " + ", ".join(avoids))
    lines.append("")
    lines.append("## 17. Disclaimer")
    lines.append("")
    lines.append(section17.strip() or DEFAULT_DISCLAIMER)
    lines.append("")

    text = "\n".join(lines)
    return text, split_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an automated state-driven FX split report.")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--split-dir", default="output_split_test")
    parser.add_argument("--run-date", default=None, help="Optional YYYY-MM-DD run date in Europe/Amsterdam timezone")
    args = parser.parse_args()

    if args.run_date:
        run_date = datetime.strptime(args.run_date, "%Y-%m-%d")
    else:
        run_date = datetime.now(ZoneInfo("Europe/Amsterdam"))
    output_dir = Path(args.output_dir)
    split_dir = Path(args.split_dir)

    report_text, split_path = build_report(run_date, output_dir, split_dir)
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.write_text(report_text, encoding="utf-8")
    print(f"GENERATE_OK | split_report={split_path.as_posix()}")


if __name__ == "__main__":
    main()
