#!/usr/bin/env python3
"""
generate_fx_report.py

Headless generator skeleton for the Weekly FX Review.

Purpose
-------
Create a fresh, versioned `output/weekly_fx_review_YYMMDD[_NN].md` file
*after* the latest FX overlay and portfolio-state updates have completed.

Design philosophy
-----------------
- deterministic
- state-driven
- safe as a workflow step
- reuses the latest prior report for strategic carry-forward
- refreshes Section 7 / 15 / 16 from live portfolio-state files
- keeps the report sellable and coherent even before a fuller research engine exists

What this script does today
---------------------------
1. Reads:
   - output/fx_portfolio_state.json
   - output/fx_valuation_history.csv
   - output/fx_technical_overlay.json
   - latest prior weekly_fx_review_*.md
2. Creates a new versioned report for "today"
3. Rebuilds:
   - Section 1 (light auto executive summary)
   - Section 7 (equity / NAV)
   - Section 15 (current holdings and cash)
   - Section 16 (carry-forward)
4. Carries forward the latest prior strategic sections for now

What this script does NOT do yet
--------------------------------
- full autonomous macro / central-bank / geopolitics research
- full autonomous score recomputation
- full autonomous narrative rewriting of every section

So this is a robust workflow-safe skeleton, not the final full generator.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

TITLE = "Weekly FX Review"
DISCLAIMER_LINE = "> *This report is for informational and educational purposes only; please see the disclaimer at the end.*"
REPORT_RE = re.compile(r"weekly_fx_review_(\d{6})(?:_(\d{2}))?\.md$", re.IGNORECASE)
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$", re.MULTILINE)

REQUIRED_STATE_FILES = [
    "output/fx_portfolio_state.json",
    "output/fx_valuation_history.csv",
    "output/fx_technical_overlay.json",
]

SECTION_TITLES = {
    1: "Executive summary",
    2: "Portfolio action snapshot",
    3: "Global macro & FX regime dashboard",
    4: "Structural currency opportunity radar",
    5: "Key risks / invalidators",
    6: "Bottom line",
    7: "Equity curve and portfolio development",
    8: "Currency allocation map",
    9: "Macro transmission & second-order effects map",
    10: "Current currency review",
    11: "Best new currency opportunities",
    12: "Portfolio rotation plan",
    13: "Final action table",
    14: "Position changes executed this run",
    15: "Current portfolio holdings and cash",
    16: "Carry-forward input for next run",
    17: "Disclaimer",
}

TV_MAP = {
    "USD": "https://www.tradingview.com/chart/?symbol=DXY",
    "EUR": "https://www.tradingview.com/chart/?symbol=EURUSD",
    "GBP": "https://www.tradingview.com/chart/?symbol=GBPUSD",
    "AUD": "https://www.tradingview.com/chart/?symbol=AUDUSD",
    "NZD": "https://www.tradingview.com/chart/?symbol=NZDUSD",
    "JPY": "https://www.tradingview.com/chart/?symbol=1/USDJPY",
    "CHF": "https://www.tradingview.com/chart/?symbol=1/USDCHF",
    "CAD": "https://www.tradingview.com/chart/?symbol=1/USDCAD",
    "MXN": "https://www.tradingview.com/chart/?symbol=1/USDMXN",
    "ZAR": "https://www.tradingview.com/chart/?symbol=1/USDZAR",
}


@dataclass
class Section:
    number: int
    title: str
    body: str


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def latest_report_file(output_dir: Path) -> Optional[Path]:
    files = []
    for path in output_dir.glob("weekly_fx_review_*.md"):
        m = REPORT_RE.fullmatch(path.name)
        if not m:
            continue
        files.append((m.group(1), int(m.group(2) or "0"), path))
    if not files:
        return None
    files.sort(key=lambda x: (x[0], x[1]))
    return files[-1][2]


def next_report_path(output_dir: Path, today: datetime) -> Path:
    date_tag = today.strftime("%y%m%d")
    existing = []
    for path in output_dir.glob(f"weekly_fx_review_{date_tag}*.md"):
        m = REPORT_RE.fullmatch(path.name)
        if m:
            existing.append(int(m.group(2) or "0"))
    if not existing:
        return output_dir / f"weekly_fx_review_{date_tag}.md"
    next_version = max(existing) + 1
    return output_dir / f"weekly_fx_review_{date_tag}_{next_version:02d}.md"


def parse_sections(md: str) -> Dict[int, Section]:
    matches = list(SECTION_RE.finditer(md))
    sections: Dict[int, Section] = {}
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md)
        sections[int(m.group(1))] = Section(
            number=int(m.group(1)),
            title=m.group(2).strip(),
            body=md[start:end].strip(),
        )
    return sections


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def md_money(value: float) -> str:
    return f"{value:,.2f}".replace(".00", "")


def md_pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def latest_valuation_row(rows: List[dict]) -> dict:
    if not rows:
        raise RuntimeError("fx_valuation_history.csv is empty")
    return rows[-1]


def overlay_state_summary(overlay: dict) -> str:
    currencies = overlay.get("currency_states", {})
    preferred_order = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "NZD", "CHF", "MXN", "ZAR"]
    parts = []
    for ccy in preferred_order:
        state = currencies.get(ccy)
        if not state:
            continue
        verdict = state.get("technical_state") or state.get("technical_verdict") or state.get("state") or "mixed"
        parts.append(f"{ccy} {verdict}")
    return ", ".join(parts) if parts else "overlay available"


def build_section_1(prior_sections: Dict[int, Section], state: dict, overlay: dict) -> str:
    nav = state["last_valuation"]["nav_usd"]
    unreal = state["last_valuation"]["unrealized_pnl_usd"]
    cash = state["cash_usd"]
    regime = "mild risk-off with a defensive USD bias"
    overlay_summary = overlay_state_summary(overlay)

    prior_text = ""
    if 1 in prior_sections:
        first_para = prior_sections[1].body.split("\n\n")[0].strip()
        if first_para:
            prior_text = first_para + "\n\n"

    return normalize(
        f"{prior_text}"
        f"This is an automatically refreshed same-day continuation run using the latest live portfolio-state files, "
        f"latest valuation history, and the latest technical overlay.\n\n"
        f"The strategic regime remains **{regime}**. Current live portfolio value is **{md_money(nav)} USD**, "
        f"with unrealized P&L of **{md_money(unreal)} USD** and cash of **{md_money(cash)} USD**. "
        f"The technical overlay currently reads: **{overlay_summary}**.\n\n"
        f"This auto-generated version is intended to keep the mailed report synchronized with the latest portfolio state. "
        f"Strategic sections not rebuilt headlessly are carried forward from the latest prior report unless explicitly refreshed."
    )


def build_section_7(state: dict, valuation_rows: List[dict]) -> str:
    lv = state["last_valuation"]
    lines = [
        "Valuation source: **Twelve Data latest completed daily bars / overlay reuse**.  ",
        f"Valuation date: **{lv['date']}**.  ",
        f"Engine overlay timestamp: **{lv.get('overlay_as_of_utc', 'unknown')}**.\n",
        f"- Net asset value (USD): **{md_money(float(lv['nav_usd']))}**",
        f"- Cash (USD): **{md_money(float(state['cash_usd']))}**",
        f"- Gross exposure (USD): **{md_money(float(lv['gross_exposure_usd']))}**",
        f"- Net exposure (USD): **{md_money(float(lv['net_exposure_usd']))}**",
        f"- Realized P&L (USD): **{md_money(float(state['realized_pnl_usd']))}**",
        f"- Unrealized P&L (USD): **{md_money(float(lv['unrealized_pnl_usd']))}**",
        f"- Daily return (%): **{md_pct(float(lv['daily_return_pct']), 4)}**",
        f"- Since inception return (%): **{md_pct(float(lv['since_inception_return_pct']), 4)}**",
        f"- Max drawdown (%): **{md_pct(float(state['max_drawdown_pct']), 4)}**\n",
    ]
    if len(valuation_rows) <= 1:
        lines.append(
            "The equity curve is still shallow because the portfolio engine has only just been initialized. "
            "This is now a live implementation-history limitation, not a narrative placeholder.\n"
        )
    else:
        lines.append(
            "The equity curve below is sourced from the live portfolio engine and reflects actual mark-to-market updates "
            "stored in `output/fx_valuation_history.csv`.\n"
        )

    lines.append("| Date | NAV (USD) | Daily return (%) | Since inception return (%) | Drawdown (%) | Overlay timestamp |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for row in valuation_rows[-10:]:
        lines.append(
            f"| {row['date']} | {md_money(float(row['nav_usd']))} | "
            f"{md_pct(float(row['daily_return_pct']), 4)} | "
            f"{md_pct(float(row['since_inception_return_pct']), 4)} | "
            f"{md_pct(float(row['drawdown_pct']), 4)} | "
            f"{row.get('overlay_as_of_utc', '')} |"
        )
    return normalize("\n".join(lines))


def direction_from_position(pos: dict) -> str:
    units = float(pos.get("units_ccy", 0))
    return "Long" if units >= 0 else "Short"


def build_section_15(state: dict) -> str:
    lv = state["last_valuation"]
    nav = float(lv["nav_usd"])
    cash = float(state["cash_usd"])
    invested = float(lv["gross_exposure_usd"])

    lines = [
        f"- Starting capital (USD): **{md_money(float(state['starting_capital_usd']))}**",
        f"- Invested market value (USD): **{md_money(invested)}**",
        f"- Cash (USD): **{md_money(cash)}**",
        f"- Total portfolio value (USD): **{md_money(nav)}**",
        f"- Since inception return (%): **{md_pct(float(lv['since_inception_return_pct']), 4)}**",
        f"- Base currency: **{state['base_currency']}**\n",
        "| Currency sleeve | Implementation pair | Direction | Entry date | Entry price | Current price | Gross exposure (USD) | Unrealized P&L (USD) | Current weight (%) | Stance |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]

    for pos in state["positions"]:
        lines.append(
            f"| {pos['currency']} | {pos['raw_pair']} -> {pos['synthetic_pair']} | "
            f"{direction_from_position(pos)} {pos['currency']} | {pos['opened_date']} | "
            f"{float(pos['avg_entry_price_ccyusd']):.8f} | {float(pos['current_price_ccyusd']):.8f} | "
            f"{md_money(float(pos['market_value_usd']))} | {md_money(float(pos['unrealized_pnl_usd']))} | "
            f"{float(pos['current_weight_pct']):.2f} | {pos['action_label']} |"
        )

    lines.append(
        f"| USD cash | — | Long USD cash | {state['inception_date']} | 1.00000000 | 1.00000000 | "
        f"{md_money(cash)} | 0 | {100 * cash / nav:.2f} | Buy |"
    )
    return normalize("\n".join(lines))


def build_section_16(report_path: Path, state: dict, overlay: dict) -> str:
    lv = state["last_valuation"]
    lines = [
        "**This section is the canonical default input for the next run unless the user explicitly overrides it.**\n",
        "- Report type: Weekly FX Review",
        f"- Run date: {lv['date']}",
        f"- Run version: {extract_version(report_path.name)}",
        f"- Base currency: {state['base_currency']}",
        f"- Starting capital: {md_money(float(state['starting_capital_usd']))}",
        f"- Current total portfolio value: {md_money(float(lv['nav_usd']))}",
        f"- Cash: {md_money(float(state['cash_usd']))}",
        "- Holdings:",
    ]
    for pos in state["positions"]:
        lines.append(f"  - {pos['currency']} {float(pos['target_weight_pct']):.1f}%")
    cash_weight = 100 * float(state["cash_usd"]) / float(lv["nav_usd"])
    lines.append(f"  - USD cash {cash_weight:.1f}%")
    lines.append("- Strategic regime: mild risk-off / defensive USD bias / trade-and-geopolitics aware")
    lines.append(f"- Technical overlay state: {overlay_state_summary(overlay)}")
    lines.append(f"- Portfolio engine state: live; last valuation timestamp {lv.get('overlay_as_of_utc', 'unknown')}")
    lines.append("- Highest-priority adds next run if thesis improves further: CHF, USD cash")
    lines.append("- First candidates for rebuild if technicals improve: JPY, CAD")
    lines.append("- First candidates for reduction if regime softens: USD cash, CHF")
    lines.append("- First candidates for addition on improved global breadth: AUD, EUR")
    lines.append("- Avoid unless regime changes materially: NZD, ZAR")
    return normalize("\n".join(lines))


def extract_version(filename: str) -> str:
    m = REPORT_RE.fullmatch(filename)
    if not m:
        return "00"
    return m.group(2) or "00"


def section_text(number: int, body: str) -> str:
    return f"## {number}. {SECTION_TITLES[number]}\n\n{body.strip()}\n"


def build_report(
    prior_sections: Dict[int, Section],
    state: dict,
    valuation_rows: List[dict],
    overlay: dict,
    output_path: Path,
) -> str:
    sections: Dict[int, str] = {}

    sections[1] = build_section_1(prior_sections, state, overlay)
    sections[7] = build_section_7(state, valuation_rows)
    sections[15] = build_section_15(state)
    sections[16] = build_section_16(output_path, state, overlay)

    # carry forward all other sections when present
    for i in range(2, 18):
        if i in {7, 15, 16}:
            continue
        if i == 17 and i not in prior_sections:
            sections[i] = normalize(
                "This report is for informational and educational purposes only and does not constitute investment advice, "
                "a solicitation, or a recommendation to transact in any security, derivative, fund, or currency. "
                "The model portfolio is a rules-based illustrative framework built for analytical tracking."
            )
            continue
        if i not in sections and i in prior_sections:
            sections[i] = normalize(prior_sections[i].body)

    # safe defaults if some sections are missing
    defaults = {
        2: "- **Build:** USD\n- **Add / build on weakness:** CHF\n- **Hold / stage:** JPY, MXN, AUD\n- **Reduce / underweight:** EUR, GBP\n- **Sell / avoid:** NZD, ZAR",
        3: "- **Global macro regime:** mild risk-off\n- **Policy divergence:** USD still favored on carry\n- **Technical overlay:** available same-day",
        4: "| Theme | Status | Current read |\n|---|---|---|\n| Dollar liquidity premium | active / investable | USD demand remains firm |",
        5: "- A broad risk-on reset would weaken the defensive USD / CHF preference.",
        6: "The correct posture remains defense first, optionality second, high beta last.",
        8: "| Currency | Strategic score | Action | Role in portfolio |\n|---|---:|---|---|",
        9: "| Shock / driver | Likely winners | Likely losers | Transmission logic |\n|---|---|---|---|",
        10: "**USD — Buy**\nThe base-currency sleeve remains the strongest strategic anchor.",
        11: "1. **CHF** — clean defensive addition.\n2. **USD via cash** — strongest base expression.\n3. **AUD** — staged allocation.",
        12: "No additional rebalance is required on this run.",
        13: "| Currency | Action | Target weight (%) | Confidence |\n|---|---|---:|---|",
        14: "No additional position changes were executed on this run.",
        17: "This report is for informational and educational purposes only and does not constitute investment advice.",
    }
    for k, v in defaults.items():
        sections.setdefault(k, normalize(v))

    pieces = [
        f"# {TITLE}\n",
        f"{DISCLAIMER_LINE}\n",
    ]
    for i in range(1, 18):
        pieces.append(section_text(i, sections[i]))
    return normalize("\n".join(pieces))


def main() -> None:
    repo_root = Path(".")
    output_dir = repo_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    for rel in REQUIRED_STATE_FILES:
        if not (repo_root / rel).exists():
            raise FileNotFoundError(f"Missing required file: {rel}")

    state = load_json(output_dir / "fx_portfolio_state.json")
    overlay = load_json(output_dir / "fx_technical_overlay.json")
    valuation_rows = load_csv_rows(output_dir / "fx_valuation_history.csv")

    latest_prior = latest_report_file(output_dir)
    prior_sections: Dict[int, Section] = {}
    if latest_prior and latest_prior.exists():
        prior_md = normalize(latest_prior.read_text(encoding="utf-8"))
        prior_sections = parse_sections(prior_md)

    today = datetime.utcnow()
    output_path = next_report_path(output_dir, today)
    report_md = build_report(prior_sections, state, valuation_rows, overlay, output_path)
    output_path.write_text(report_md, encoding="utf-8")

    print(f"GENERATED_REPORT_OK | path={output_path.as_posix()} | source_state=output/fx_portfolio_state.json")


if __name__ == "__main__":
    main()
