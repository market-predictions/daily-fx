# Weekly FX Review

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary

This is an **automated state-driven split run** using the latest stored FX report as the strategic carry-forward base, the latest technical overlay in `output/fx_technical_overlay.json`, and the live implementation files in `output/fx_portfolio_state.json`, `output/fx_trade_ledger.csv`, and `output/fx_valuation_history.csv`. Implementation and valuation facts are taken from the state files when they differ from older report text.

The strategic regime remains **mild risk-off / defensive USD bias / trade-and-geopolitics aware**. Current live portfolio value is **99,257.64 USD**, with cash at **35,733.34 USD**, gross exposure at **63,524.95 USD**, realized P&L at **-0.65 USD**, unrealized P&L at **-741.07 USD**, and the latest portfolio/overlay timestamp at **2026-03-28T08:58:02Z**.

The current ranking still favors **USD** as the core defensive anchor, with the strongest additional uses of capital now concentrated in **USD**, **CHF**, **AUD**. This automated generator does **not** perform a fresh live macro research pass; strategy-heavy narrative is therefore refreshed from carry-forward state, while technical, valuation, and implementation facts are updated from the repo’s current state files.

## 2. Portfolio action snapshot

| Sleeve | Action | Current read |
|---|---|---|
| USD | Buy | Strongest defensive anchor; supported by rates, liquidity, and broad overlay strength |
| EUR | Reduce | Lower-rate bloc plus strong negative technical confirmation |
| JPY | Hold / stage | Haven logic intact, but still strongly negative on current technical confirmation |
| CHF | Build on weakness | Clean second-line defensive sleeve despite negative technical confirmation |
| GBP | Reduce | Some rate support, but the technical picture remains strongly negative |
| AUD | Hold / stage | RBA stance remains supportive, but AUD is still only mixed technically and remains cyclical |
| CAD | Hold | Oil / terms-of-trade support intact, but weaker domestic growth and negative technical confirmation cap enthusiasm |
| NZD | Sell / avoid | Recovery story lacks urgency and the overlay remains negative |
| MXN | Hold / stage | Carry-positive macro story, but technical confirmation has weakened to negative |
| ZAR | Sell / avoid | Wrong exposure for a defensive, oil-shock-aware regime |

## 3. Global macro & FX regime dashboard

- **Global macro regime:** mild risk-off / defensive USD bias / trade-and-geopolitics aware (carried forward from the latest stored report; no live macro refresh in this automated generator).
- **Policy divergence:** **USD** remains favored versus lower-rate blocs; **AUD** and **MXN** retain selective support from higher-rate settings, but not enough to override defensive conditions.
- **Risk regime:** Mild risk-off.
- **USD liquidity / funding:** Supportive for **USD**.
- **Commodity impulse:** Supportive for **CAD** in macro terms; selectively constructive for **AUD**; adverse for major energy importers.
- **Technical overlay:** Same-day available; **USD** positive, **EUR** strong negative, **GBP** strong negative, **JPY** strong negative, **CHF** negative, **AUD** mixed, **CAD** negative, **NZD** negative, **MXN** negative, **ZAR** negative.

## 4. Structural currency opportunity radar

| Theme | Status | Current read |
|---|---|---|
| Dollar liquidity premium | active / investable | Elevated uncertainty and defensive funding demand keep **USD** supported. |
| Swiss defensive role with intervention risk | active / investable | **CHF** remains the cleaner second-line defensive sleeve, though intervention risk caps the upside tail. |
| Yen haven asymmetry | active / watch | Haven logic remains intact, but the overlay is still strongly negative, so position size should stay controlled. |
| Commodity FX recovery | active / watch | **CAD** has macro support from oil, while **AUD** benefits from the current rate stance; neither has clean broad confirmation. |
| Europe cyclical repair | fading / under pressure | Lower relative rates and negative technical confirmation keep **EUR** weak. |
| EM carry under controlled volatility | weakening / watch | **MXN** remains carry-interesting, but the overlay has softened to negative. |
| High-beta EM beta | invalidated | **ZAR** remains unattractive into a defensive, oil-shock-aware regime. |

## 5. Key risks / invalidators

- A rapid and durable de-escalation in geopolitical risk plus a sharp reversal in oil would reduce the **USD** / **CHF** defensive premium.
- A decisive broadening of non-U.S. growth plus materially easier Fed pricing would weaken the **USD** overweight case.
- A clean reversal in **USDJPY** technical strength would improve the case for rebuilding **JPY** more aggressively.
- A clearer euro-area growth improvement with no renewed energy pressure would improve **EUR**.
- A broad risk-on reset would help **AUD**, **NZD**, and **ZAR** faster than this framework currently assumes.

## 6. Bottom line

The correct portfolio posture remains **defense first, optionality second, high-beta last**. **USD** remains the strongest core anchor. **CHF** remains the cleaner secondary defensive allocation than **JPY** on this run. **CAD**, **AUD**, and **MXN** remain secondary sleeves rather than leadership sleeves. **EUR** and **GBP** stay in reduce territory, while **NZD** and **ZAR** still do not deserve capital.

## 7. Equity curve and portfolio development

Valuation source: **Twelve Data latest completed daily bars / overlay reuse**. Valuation date: **2026-03-28**. Engine overlay timestamp: **2026-03-28T08:58:02Z**.

- Net asset value (USD): **99,257.64**
- Cash (USD): **35,733.34**
- Gross exposure (USD): **63,524.95**
- Net exposure (USD): **63,524.95**
- Realized P&L (USD): **-0.65**
- Unrealized P&L (USD): **-741.07**
- Daily return (%): **-0.0001**
- Since inception return (%): **-0.7424**
- Max drawdown (%): **-0.7424**

The equity curve below is sourced from the live portfolio engine and reflects actual mark-to-market updates stored in `output/fx_valuation_history.csv`.

| Date | NAV (USD) | Daily return (%) | Since inception return (%) | Drawdown (%) | Overlay timestamp |
|---|---|---|---|---|---|
| 2026-03-25 | 100,000.00 | 0.0000 | 0.0000 | 0.0000 | 2026-03-25T12:08:31Z |
| 2026-03-25 | 99,947.37 | -0.0000 | -0.0526 | -0.0526 | 2026-03-25T12:21:52Z |
| 2026-03-25 | 99,788.68 | -0.0000 | -0.2113 | -0.2113 | 2026-03-25T19:18:21Z |
| 2026-03-25 | 99,791.54 | -0.0000 | -0.2085 | -0.2113 | 2026-03-25T22:08:27Z |
| 2026-03-25 | 99,791.74 | -0.0000 | -0.2083 | -0.2113 | 2026-03-25T23:34:00Z |
| 2026-03-25 | 99,782.64 | 0.0000 | -0.2174 | -0.2174 | 2026-03-25T23:46:50Z |
| 2026-03-25 | 99,785.42 | -0.0000 | -0.2146 | -0.2174 | 2026-03-25T23:50:51Z |
| 2026-03-26 | 99,765.98 | -0.0000 | -0.2340 | -0.2340 | 2026-03-26T00:46:04Z |
| 2026-03-26 | 99,673.93 | -0.0000 | -0.3261 | -0.3261 | 2026-03-26T11:33:57Z |
| 2026-03-26 | 99,518.16 | -0.0001 | -0.4818 | -0.4818 | 2026-03-26T19:25:44Z |
| 2026-03-26 | 99,472.94 | -0.0000 | -0.5271 | -0.5271 | 2026-03-26T20:13:51Z |
| 2026-03-26 | 99,556.26 | -0.0003 | -0.4437 | -0.5271 | 2026-03-26T23:05:58Z |
| 2026-03-26 | 99,551.58 | -0.0000 | -0.4484 | -0.5271 | 2026-03-26T23:32:25Z |
| 2026-03-26 | 99,559.41 | -0.0000 | -0.4406 | -0.5271 | 2026-03-26T23:42:52Z |
| 2026-03-28 | 99,257.64 | -0.0001 | -0.7424 | -0.7424 | 2026-03-28T08:58:02Z |

## 8. Currency allocation map

| Currency | Strategic score | Action | Role in portfolio |
|---|---|---|---|
| USD | 19.2 | Buy | Base, liquidity buffer, defensive anchor |
| EUR | 4.2 | Reduce | Lower-rate bloc with energy sensitivity and strong negative technical confirmation |
| JPY | 12.0 | Hold / stage | Haven sleeve retained, but current technical confirmation is still strongly negative |
| CHF | 16.9 | Build on weakness | Defensive diversifier with cleaner strategic support than JPY |
| GBP | 4.8 | Reduce | Some rate support remains, but strong negative technical confirmation weakens the case |
| AUD | 11.8 | Hold / stage | Mixed technical overlay offsets part of the cyclical risk |
| CAD | 12.5 | Hold | Oil / terms-of-trade support with weaker near-term confirmation |
| NZD | 0.4 | Sell / avoid | Low-rate recovery story lacks urgency |
| MXN | 11.4 | Hold / stage | Carry-positive macro story, but technical confirmation has weakened to negative |
| ZAR | 0.4 | Sell / avoid | High-beta EM exposure not paid enough in this regime |

## 9. Macro transmission & second-order effects map

| Shock / driver | Likely winners | Likely losers | Transmission logic |
|---|---|---|---|
| Energy-shock / geopolitical stress | USD, CHF, CAD | EUR, NZD, ZAR | Higher fuel costs raise defensive demand, help energy-linked terms of trade, and hurt importers. |
| Fed on hold versus lower-rate blocs | USD | EUR, NZD, CHF cash alternatives | Rate differential and cash carry favor **USD**. |
| BoJ normalization from a still-low base | JPY | Traditional funding trades versus JPY | Incremental tightening reduces the structural drag on **JPY**, though price action is not yet confirming. |
| Hawkish AUD carry without broad risk-on | AUD | Lower-yield cyclical alternatives | **AUD** gets some rate support, but not enough to become a leadership sleeve in mild risk-off. |
| Trade-policy uncertainty | USD, CHF | AUD, NZD, ZAR, cyclical EUR rebound trades | Reduced visibility hurts high-beta currencies and supports liquid defensive anchors. |

## 10. Current currency review

**USD — Buy**
The current overlay remains positive for the dollar through broad non-USD weakness. **USD** remains the highest-quality base sleeve.

**EUR — Reduce**
The current overlay remains explicitly strong negative on **EUR**. Macro carry-forward and technical confirmation continue to align to the downside.

**JPY — Hold / stage**
The macro haven thesis remains intact, but the current overlay still shows a strong negative **JPY** confirmation through **USDJPY** strength. **JPY** remains in the portfolio, but only as a staged hold rather than a larger haven sleeve.

**CHF — Build on weakness**
**CHF** remains one of the cleanest defensive diversifiers. The current overlay is negative, which tempers sizing, but the broader defensive case remains intact.

**GBP — Reduce**
**GBP** retains some rate support, but the current technical overlay remains strong negative. That keeps **GBP** in reduce territory rather than leadership status.

**AUD — Hold / stage**
**AUD** is still only mixed on the overlay and remains a cyclical currency in a mild risk-off world. That supports a staged allocation, not aggressive adding.

**CAD — Hold**
**CAD** still has macro support from oil and terms of trade, but the current overlay for **USDCAD** still argues against stronger conviction. That keeps **CAD** in smaller-hold territory.

**NZD — Sell / avoid**
The strategic case remains weak and the overlay remains negative. That is not enough to justify a rebuild.

**MXN — Hold / stage**
**MXN** remains carry-positive on macro logic, but the latest overlay has softened to negative and the global backdrop is less friendly to EM carry. That keeps **MXN** in the portfolio, but with a stronger case for disciplined sizing.

**ZAR — Sell / avoid**
**ZAR** remains the wrong kind of exposure for a defensive portfolio with geopolitical and trade-policy awareness. The overlay remains negative and does not rescue the weak strategic case.

## 11. Best new currency opportunities

1. **USD** — The strongest base-currency expression remains additional **USD** cash rather than forcing new beta.
2. **CHF** — The cleanest incremental defensive addition because the macro thesis is intact even though the overlay is negative rather than neutral.
3. **AUD** — Not a clean technical buy, but still a better cyclical placeholder than the weaker high-beta alternatives because the overlay is mixed rather than outright broken.

## 12. Portfolio rotation plan

| Bucket | Positioning |
|---|---|
| Core defense | USD cash 36%, CHF 13% |
| Defensive optionality | JPY 13% |
| Secondary macro hold | CAD 10% |
| Staged cyclicals / carry | MXN 8%, AUD 8% |
| Reduce / underweight | GBP 7%, EUR 5% |
| Avoid | NZD 0%, ZAR 0% |

No fresh rebalance is assumed in this automated generator run beyond the authoritative implementation state already stored in the repo.

## 13. Final action table

| Currency | Action | Target weight (%) | Confidence |
|---|---|---|---|
| USD | Buy | 36 | High |
| EUR | Reduce | 5 | Medium-High |
| JPY | Hold / stage | 13 | Medium |
| CHF | Build on weakness | 13 | Medium |
| GBP | Reduce | 7 | Medium-High |
| AUD | Hold / stage | 8 | Medium |
| CAD | Hold | 10 | Medium |
| NZD | Sell / avoid | 0 | Medium-High |
| MXN | Hold / stage | 8 | Medium |
| ZAR | Sell / avoid | 0 | Medium-High |

## 14. Position changes executed this run

No **additional** position changes are executed inside this automated generator run. However, the authoritative implementation state currently reflects a rebalance sourced from `weekly_fx_review_260328_01.md`, with **7 trades executed** on **2026-03-28**.

Authoritative latest rebalance adjustments already recorded in the trade ledger:

| Currency | Units delta | Execution price (CCYUSD) | Notional USD | Comment |
|---|---|---|---|---|
| CHF | 11.0323 | 1.25349411 | 13.83 | Build on weakness target 13.00% |
| JPY | 2,153.9720 | 0.00623746 | 13.44 | Hold / stage target 13.00% |
| CAD | 3.6817 | 0.71978694 | 2.65 | Hold target 10.00% |
| MXN | 1,224.9486 | 0.05518554 | 67.60 | Hold / stage target 8.00% |
| AUD | -7.8811 | 0.68777000 | 5.42 | Hold / stage target 8.00% |
| GBP | 14.7663 | 1.32608000 | 19.58 | Reduce target 7.00% |
| EUR | -2.6865 | 1.15112000 | 3.09 | Reduce target 5.00% |

## 15. Current portfolio holdings and cash

- Starting capital (USD): **100,000.00**
- Invested market value (USD): **63,524.95**
- Cash (USD): **35,733.34**
- Total portfolio value (USD): **99,257.64**
- Since inception return (%): **-0.7424**
- Base currency: **USD**

The holdings below are sourced from the live portfolio-state file. The displayed **Current weight (%)** column is derived deterministically as `market_value_usd / NAV`, because the stored `current_weight_pct` values in the state file do not reconcile to the NAV/cash totals.

| Currency sleeve | Implementation pair | Direction | Entry date | Entry price | Current price | Gross exposure (USD) | Unrealized P&L (USD) | Current weight (%) | Stance |
|---|---|---|---|---|---|---|---|---|---|
| EUR | EUR/USD -> EURUSD | Long EUR | 2026-03-25 | 1.16075959 | 1.15112000 | 4,962.89 | -41.56 | 5.00 | Reduce |
| JPY | USD/JPY -> JPYUSD | Long JPY | 2026-03-25 | 0.00629623 | 0.00623746 | 12,903.50 | -121.57 | 13.00 | Hold / stage |
| CHF | USD/CHF -> CHFUSD | Long CHF | 2026-03-25 | 1.26781290 | 1.25349411 | 12,903.50 | -147.40 | 13.00 | Build on weakness |
| GBP | GBP/USD -> GBPUSD | Long GBP | 2026-03-25 | 1.34201115 | 1.32608000 | 6,948.04 | -83.47 | 7.00 | Reduce |
| AUD | AUD/USD -> AUDUSD | Long AUD | 2026-03-25 | 0.69670514 | 0.68777000 | 7,940.62 | -103.16 | 8.00 | Hold / stage |
| CAD | USD/CAD -> CADUSD | Long CAD | 2026-03-25 | 0.72497879 | 0.71978694 | 9,925.77 | -71.59 | 10.00 | Hold |
| MXN | USD/MXN -> MXNUSD | Long MXN | 2026-03-25 | 0.05638311 | 0.05518554 | 7,940.62 | -172.32 | 8.00 | Hold / stage |
| USD cash | — | Long USD cash | 2026-03-25 | 1.00000000 | 1.00000000 | 35,733.34 | 0.00 | 36.00 | Buy |

## 16. Carry-forward input for next run

**This section is the canonical default input for the next run unless the user explicitly overrides it.**

- Report type: Weekly FX Review
- Run date: 2026-03-28
- Run version: automated-split
- Base currency: USD
- Starting capital: 100,000.00
- Current total portfolio value: 99,257.64
- Cash: 35,733.34
- Holdings:
  - EUR 5%
  - JPY 13%
  - CHF 13%
  - GBP 7%
  - AUD 8%
  - CAD 10%
  - MXN 8%
  - USD cash 36%
- Strategic regime: mild risk-off / defensive USD bias / trade-and-geopolitics aware
- Technical overlay state: overlay available
- Portfolio engine state: live; last valuation date 2026-03-28 and latest portfolio-state overlay timestamp 2026-03-28T08:58:02Z
- Technical overlay as of: 2026-03-28T08:58:02Z
- Highest-priority adds next run if thesis improves further: USD, CHF
- First candidates for rebuild if technicals improve: JPY, AUD, CAD
- First candidates for reduction if regime softens: USD, CHF
- First candidates for addition on improved global breadth: AUD, EUR
- Avoid unless regime changes materially: NZD, ZAR

## 17. Disclaimer

This report is for informational and educational purposes only and does not constitute investment advice, a solicitation, or a recommendation to transact in any security, derivative, fund, or currency. The model portfolio is a rules-based illustrative framework built for analytical tracking. It does not account for taxes, transaction costs, funding costs, slippage, implementation constraints, legal restrictions, suitability requirements, or investor-specific objectives. Market conditions can change rapidly, including because of central-bank decisions, geopolitical developments, commodity-price shocks, and policy changes. Any use of this report or its model allocations is at the reader’s own risk.
