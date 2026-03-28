# FX Input / State Contract — As-Is Split

This file extracts the **base-currency, input-resolution, technical-overlay, and portfolio-engine** parts of `fx.txt` without intentionally changing logic.
Cross-references to other sections are preserved as written.

---

## 5. BASE CURRENCY, UNIVERSE, AND POSITION OBJECT

### Base / accounting anchor
- The base currency is **USD**.
- All holdings, scores, cash balances, portfolio values, P&L, and NAV must be expressed in USD unless explicitly stated otherwise.

### Position object
- The report evaluates **currencies**, not currency pairs.
- Pairs are used for evidence, technical confirmation, and implementation.
- Final judgments must always be at the currency level.
- Portfolio implementation must be expressed through **FX pairs plus USD cash**.

### Core universe
- USD
- EUR
- JPY
- CHF
- GBP
- AUD
- CAD
- NZD

### Satellite universe
- MXN
- ZAR

### Rule
Do not let the report drift into a classic EURUSD / GBPUSD trading note.
The final recommendation must always read as a currency stance first.

### Standard implementation map
Use these implementation proxies for the tracked model portfolio:
- EUR -> `EURUSD`
- GBP -> `GBPUSD`
- AUD -> `AUDUSD`
- NZD -> `NZDUSD`
- JPY -> `USDJPY` (internally valued as synthetic `JPYUSD = 1 / USDJPY`)
- CHF -> `USDCHF` (internally valued as synthetic `CHFUSD = 1 / USDCHF`)
- CAD -> `USDCAD` (internally valued as synthetic `CADUSD = 1 / USDCAD`)
- MXN -> `USDMXN` (internally valued as synthetic `MXNUSD = 1 / USDMXN`)
- ZAR -> `USDZAR` (internally valued as synthetic `ZARUSD = 1 / USDZAR`)

### Direction rule
- Bullish non-USD currency = long synthetic `CCYUSD`
- Bearish non-USD currency = short synthetic `CCYUSD`
- USD bullish is primarily expressed via USD cash and/or short exposure to weak non-USD currencies

---

## 6. INPUT RESOLUTION + STANDARDIZED INPUT TEMPLATE

If the user does not explicitly provide a new portfolio in the current chat, you must automatically use the most recent stored report in:
- repository: `market-predictions/daily-fx`
- folder: `output/`

### Most recent report rule
Use the most recent available FX report, including same-day versioned reports, using this priority:
1. latest date
2. highest same-day version number

Recognize both naming patterns:
- `weekly_fx_review_YYMMDD.md`
- `weekly_fx_review_YYMMDD_NN.md`

### No-manual-input fallback rule
If a prior report exists, do not ask for manual portfolio input.
Use this fallback hierarchy:
1. explicit portfolio data in the current chat
2. Section `## 16. Carry-forward input for next run` from the most recent stored report
3. Section `## 15. Current portfolio holdings and cash`
4. Section `## 13. Final action table`

If none exist, create an inaugural model portfolio and state that clearly.

### Portfolio-state files
When available, also use these implementation files as authoritative execution / valuation support:
- `output/fx_portfolio_state.json`
- `output/fx_trade_ledger.csv`
- `output/fx_valuation_history.csv`
- `output/fx_recommendation_scorecard.csv`

Priority rule:
- valuation and open-position facts should come from the portfolio-state files when they exist
- strategy and target-allocation intent should come from the most recent report
- if the two differ, explain the difference briefly and deterministically

---

## 7. REQUIRED TECHNICAL OVERLAY INPUT

The technical overlay is a **confirmation layer**, not the main decision engine.

Primary input file:
- `output/fx_technical_overlay.json`

### How to use it
- Use pair-level technical status only as evidence.
- Translate pair evidence into a **currency-level technical confirmation score**.
- Do not let the technical overlay dominate the strategic judgment.
- If macro and technical signals conflict, do not blindly follow the technical signal. Instead downgrade confidence, shift to Hold / Watch, or stage the position.
- If the overlay is older than the report date, classify it explicitly as **prior-day** or **stale** and reduce its weight.

### Required technical pairs
The overlay should ordinarily cover:
- EURUSD
- GBPUSD
- AUDUSD
- NZDUSD
- USDJPY
- USDCHF
- USDCAD
- USDMXN
- USDZAR

### Technical fields that matter
Use the overlay primarily through:
- W1_Bias
- D1_Bias
- Alignment
- Pivot_Regime
- Pivot_Zone_Fit
- Pivot_Conflict
- Technical_Score_0_4
- Technical verdict

Ignore trade-engine details such as entries, stops, take-profit levels, or risk/reward outputs.

---

## 8. MARK-TO-MARKET PORTFOLIO ENGINE

The model portfolio must be tracked as an **actual USD-base FX implementation portfolio**, not as a static narrative allocation table.

### Authoritative implementation rule
The portfolio engine should convert report recommendations into:
- USD cash
- open FX pair exposures
- entry prices
- current prices
- realized P&L
- unrealized P&L
- total NAV

### Valuation source rule
Portfolio valuation must use a deterministic, repeatable price source:
- latest completed daily bar from Twelve Data
- no ad hoc intraday spot snapshots unless explicitly configured

### Execution rule
Unless explicitly overridden, assume all model-portfolio changes are executed at the same valuation close used for that run.

### Position sizing rule
For each non-USD currency sleeve:
- determine target USD notional from target weight × NAV
- convert the target USD notional into currency units using the synthetic `CCYUSD` entry price
- store entry date, entry price, units, and implementation pair

### Synthetic pricing rule
For internally inverse currencies, compute:
- `JPYUSD = 1 / USDJPY`
- `CHFUSD = 1 / USDCHF`
- `CADUSD = 1 / USDCAD`
- `MXNUSD = 1 / USDMXN`
- `ZARUSD = 1 / USDZAR`

This synthetic `CCYUSD` price is the authoritative valuation price for the sleeve.

### Portfolio valuation formulas
For each sleeve:
- `market_value_usd = units_ccy * current_price_ccyusd`
- `unrealized_pnl_usd = units_ccy * (current_price_ccyusd - entry_price_ccyusd)`

Total portfolio:
- `NAV = cash_usd + sum(current market values of all open sleeves)`

### Reporting rule
Section 7 and Section 15 must use the engine outputs when those files exist.
Do not flat-line the portfolio value unless no valuation files exist yet.
If no engine output exists yet, say so explicitly and use a deterministic fallback.
