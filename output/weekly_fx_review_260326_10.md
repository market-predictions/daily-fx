# Weekly FX Review

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary

This is a same-day continuation run using the carry-forward state from the most recent stored FX report, the latest technical overlay in `output/fx_technical_overlay.json`, and the live implementation files in `output/fx_portfolio_state.json` and `output/fx_valuation_history.csv`.

This is an automatically refreshed same-day continuation run using the latest live portfolio-state files, latest valuation history, and the latest technical overlay.

The strategic regime remains **mild risk-off with a defensive USD bias**. Current live portfolio value is **99,559.41 USD**, with unrealized P&L of **-439.49 USD** and cash of **35,841.92 USD**. The technical overlay currently reads: **overlay available**.

This auto-generated version is intended to keep the mailed report synchronized with the latest portfolio state. Strategic sections not rebuilt headlessly are carried forward from the latest prior report unless explicitly refreshed.

## 2. Portfolio action snapshot

- **Build:** USD
- **Add / build on weakness:** CHF
- **Hold / stage:** JPY, MXN, AUD
- **Hold:** CAD
- **Reduce / underweight:** EUR, GBP
- **Sell / avoid:** NZD, ZAR
- **Cash stance:** keep USD cash at **36%**
- **Change vs prior run:** no additional position changes executed on this run; this version reflects fresher valuation data only.

## 3. Global macro & FX regime dashboard

- **Global macro regime:** Positive but fragile growth; resilience offset by trade-policy uncertainty, higher energy prices, and geopolitical stress
- **Policy divergence:** USD remains rate-rich versus EUR and NZD; JPY normalization remains constructive in macro terms but is still not confirmed by the current technical overlay
- **Risk regime:** Mild risk-off
- **USD liquidity / funding:** Supportive for USD
- **Commodity impulse:** Supportive for CAD in macro terms; tactically constructive for AUD on technicals; adverse for major oil importers
- **Technical overlay:** Same-day available; USD positive, EUR strong negative, GBP strong negative, JPY strong negative, AUD mixed, CAD negative, NZD negative, MXN mixed, ZAR negative

The official policy backdrop still supports a defensive USD bias. The Fed’s latest indexed implementation note keeps the federal funds target range at **3.50–3.75%**. The ECB deposit facility remains **2.00%**. The BoE maintained Bank Rate at **3.75%** on 19 March 2026 and highlighted the inflationary and activity risks from the Middle East energy shock. The RBNZ OCR remains **2.25%**. The SNB policy rate is **0.00%**. The BoJ continues to encourage the uncollateralized overnight call rate to remain at around **0.75%**. The latest indexed RBA policy decision remains the 3 February move to **3.85%**. That leaves USD well supported on carry, liquidity, and risk conditions, while CHF remains the cleaner second-line defensive sleeve.

## 4. Structural currency opportunity radar

| Theme | Status | Current read |
|---|---|---|
| Dollar liquidity premium | active / investable | Elevated uncertainty, higher energy prices, and defensive funding demand keep USD supported |
| Swiss defensive role with intervention risk | active / investable | CHF remains the cleaner second-line defensive sleeve because the macro case is intact and the technical damage is limited versus JPY |
| Yen haven asymmetry | active / watch | Haven logic remains intact, but the overlay is still strongly negative, so position size should stay controlled |
| Commodity FX recovery | active / watch | AUD is no longer clearly positive on the latest overlay and now reads mixed, while CAD’s near-term confirmation remains softer than the broader macro case |
| Europe cyclical repair | fading / under pressure | Lower ECB rates, energy sensitivity, and negative technical confirmation keep EUR weak |
| EM carry under controlled volatility | active / watch | MXN remains carry-positive, but confirmation is only mixed |
| High-beta EM beta | invalidated | ZAR remains unattractive into a defensive, oil-shock-aware regime |

## 5. Key risks / invalidators

- A rapid and durable de-escalation in geopolitical risk plus a sharp oil reversal would reduce the USD / CHF defensive premium.
- A decisive broadening of non-US growth plus faster Fed easing would weaken the USD-overweight case.
- A reversal in USDJPY technical strength would improve the case for rebuilding JPY more aggressively.
- A material improvement in euro-area growth with no renewed energy pressure would improve EUR.
- A cleaner global risk-on reset would help AUD, NZD and ZAR faster than this framework currently assumes.

## 6. Bottom line

The correct portfolio posture remains **defense first, optionality second, high-beta last**. There is still no new evidence that justifies another rebalance. USD remains the strongest core anchor. CHF remains the cleaner secondary defensive allocation than JPY on this run. JPY stays in the portfolio at reduced size. AUD remains a staged allocation, but the latest overlay has softened from positive to mixed, which argues for patience rather than fresh aggression.

## 7. Equity curve and portfolio development

Valuation source: **Twelve Data latest completed daily bars / overlay reuse**.
Valuation date: **2026-03-26**.
Engine overlay timestamp: **2026-03-26T23:42:52Z**.

- Net asset value (USD): **99,559.41**
- Cash (USD): **35,841.92**
- Gross exposure (USD): **63,718.04**
- Net exposure (USD): **63,718.04**
- Realized P&L (USD): **-0.55**
- Unrealized P&L (USD): **-439.49**
- Daily return (%): **-0.0000**
- Since inception return (%): **-0.4406**
- Max drawdown (%): **-0.5271**

The equity curve below is sourced from the live portfolio engine and reflects actual mark-to-market updates stored in `output/fx_valuation_history.csv`.

| Date | NAV (USD) | Daily return (%) | Since inception return (%) | Drawdown (%) | Overlay timestamp |
|---|---:|---:|---:|---:|---|
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

## 8. Currency allocation map

| Currency | Strategic score | Action | Role in portfolio |
|---|---:|---|---|
| USD | 16.5 | Buy | Base, liquidity buffer, defensive anchor |
| CHF | 11.6 | Build on weakness | Defensive diversifier with cleaner current confirmation than JPY |
| JPY | 10.6 | Hold / stage | Haven sleeve retained, but current technical confirmation is strongly negative |
| CAD | 9.4 | Hold | Oil / terms-of-trade support with weaker near-term technical confirmation |
| MXN | 8.0 | Hold / stage | Carry-positive, size moderated by risk regime |
| AUD | 7.6 | Hold / stage | Mixed technical overlay offsets part of the macro drag |
| GBP | 6.8 | Reduce | Rate support remains, but negative technical confirmation weakens the case |
| EUR | 6.2 | Reduce | Lower-rate bloc with energy sensitivity and negative technical confirmation |
| NZD | 5.2 | Sell / avoid | Low-rate recovery story lacks urgency |
| ZAR | 4.9 | Sell / avoid | High-beta EM exposure not paid enough in this regime |

## 9. Macro transmission & second-order effects map

| Shock / driver | Likely winners | Likely losers | Transmission logic |
|---|---|---|---|
| Trade-policy uncertainty | USD, CHF, JPY | AUD, NZD, ZAR | Global cyclicals and high-beta FX underperform when policy visibility falls |
| Fed on hold, ECB/RBNZ lower-rate settings | USD | EUR, NZD | Rate differential and cash carry favor USD |
| BoJ normalization from low base | JPY | Funding currencies versus JPY | Incremental tightening reduces the drag from ultra-easy policy, but near-term price action is not yet confirming |
| Oil and broader geopolitical stress | USD, CHF, CAD | EUR, NZD, ZAR | Higher energy costs raise defensive demand and hurt importers |
| Sticky inflation pockets outside Europe | USD, GBP, AUD | Low-yielders | Higher-for-longer pockets keep policy dispersion alive |

## 10. Current currency review

**USD — Buy**
The Fed’s latest indexed policy setting still favors USD on carry and liquidity, and the current overlay remains positive for the dollar through broad non-USD weakness. USD remains the highest-quality base sleeve.

**EUR — Reduce**
The ECB deposit facility remains low relative to the Fed, and the current overlay remains explicitly strong negative on EUR. Macro and technical signals continue to align to the downside.

**JPY — Hold / stage**
The macro haven thesis remains intact, but the current overlay still shows a strong negative JPY confirmation through USDJPY strength. JPY remains in the portfolio, but the correct stance is a smaller staged hold rather than a larger haven sleeve.

**CHF — Build on weakness**
CHF remains one of the cleanest defensive diversifiers. The current overlay is still negative for CHF, which tempers sizing but does not break the broader strategic case.

**GBP — Reduce**
GBP retains some rate support, but the current technical overlay remains strong negative. The latest BoE communication also highlights the inflationary and growth risks from the energy shock, which is not enough to turn GBP into a leadership currency.

**AUD — Hold / stage**
The latest indexed RBA policy decision remains 3.85%, but the overlay is now mixed rather than clearly positive. AUD is still cyclical and not a leadership currency in a mild risk-off world, so it still deserves only a staged allocation.

**CAD — Hold**
CAD’s main support remains oil and terms of trade rather than policy leadership. But the current technical overlay for USDCAD remains positive, which means CAD confirmation remains weak. That argues for a smaller hold rather than a larger sleeve.

**NZD — Sell / avoid**
The strategic case remains weak and the overlay remains negative, which is not enough to justify a rebuild.

**MXN — Hold / stage**
MXN remains carry-positive, but the overlay is only mixed, so the correct stance remains selective holding rather than aggressive adding.

**ZAR — Sell / avoid**
ZAR remains the wrong kind of exposure for a defensive portfolio with geopolitical and trade-policy awareness. The overlay is now negative rather than mixed and does not rescue the weak strategic case.

## 11. Best new currency opportunities

1. **CHF** — The cleanest incremental defensive addition because the macro thesis is intact even though the overlay is no longer strongly supportive.
2. **USD via elevated cash** — The strongest base-currency expression remains additional USD cash.
3. **AUD as a staged allocation** — No longer a clean technical buy, but still a better cyclical placeholder than NZD or ZAR because the overlay has softened only to mixed rather than outright negative.

## 12. Portfolio rotation plan

No additional rebalance is required on this run.

- Keep USD cash at 36%.
- Keep JPY at 13%.
- Keep CHF at 13%.
- Keep CAD at 10%.
- Keep MXN at 8%.
- Keep AUD at 8%.
- Keep GBP at 7%.
- Keep EUR at 5%.
- Keep NZD and ZAR at zero.

## 13. Final action table

| Currency | Action | Target weight (%) | Confidence |
|---|---|---:|---|
| USD | Buy | 36 | High |
| CHF | Build on weakness | 13 | Medium |
| JPY | Hold / stage | 13 | Medium |
| CAD | Hold | 10 | Medium |
| MXN | Hold / stage | 8 | Medium |
| AUD | Hold / stage | 8 | Medium |
| GBP | Reduce | 7 | Medium |
| EUR | Reduce | 5 | Medium-High |
| NZD | Sell / avoid | 0 | Medium-High |
| ZAR | Sell / avoid | 0 | Medium-High |

## 14. Position changes executed this run

No additional position changes were executed on this run. The live portfolio state still reflects the rebalance sourced from `weekly_fx_review_260326_04.md`, with `trades_executed = 7` on 2026-03-26.

## 15. Current portfolio holdings and cash

- Starting capital (USD): **100,000**
- Invested market value (USD): **63,718.04**
- Cash (USD): **35,841.92**
- Total portfolio value (USD): **99,559.41**
- Since inception return (%): **-0.4406**
- Base currency: **USD**

| Currency sleeve | Implementation pair | Direction | Entry date | Entry price | Current price | Gross exposure (USD) | Unrealized P&L (USD) | Current weight (%) | Stance |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| CHF | USD/CHF -> CHFUSD | Long CHF | 2026-03-25 | 1.26782826 | 1.25865324 | 12,942.73 | -94.35 | 26.53 | Build on weakness |
| JPY | USD/JPY -> JPYUSD | Long JPY | 2026-03-25 | 0.00629629 | 0.00626294 | 12,942.73 | -68.91 | 20.97 | Hold / stage |
| CAD | USD/CAD -> CADUSD | Long CAD | 2026-03-25 | 0.72498017 | 0.72216766 | 9,955.94 | -38.77 | 13.89 | Hold |
| MXN | USD/MXN -> MXNUSD | Long MXN | 2026-03-25 | 0.05639339 | 0.05582856 | 7,964.76 | -80.58 | 10.00 | Hold / stage |
| AUD | AUD/USD -> AUDUSD | Long AUD | 2026-03-25 | 0.69670514 | 0.68939000 | 7,964.76 | -84.51 | 9.09 | Hold / stage |
| GBP | GBP/USD -> GBPUSD | Long GBP | 2026-03-25 | 1.34205618 | 1.33387000 | 6,969.16 | -42.77 | 7.37 | Reduce |
| EUR | EUR/USD -> EURUSD | Long EUR | 2026-03-25 | 1.16075959 | 1.15390000 | 4,977.97 | -29.59 | 5.00 | Reduce |
| USD cash | — | Long USD cash | 2026-03-25 | 1.00000000 | 1.00000000 | 35,841.92 | 0 | 36.00 | Buy |

## 16. Carry-forward input for next run

**This section is the canonical default input for the next run unless the user explicitly overrides it.**

- Report type: Weekly FX Review
- Run date: 2026-03-26
- Run version: 10
- Base currency: USD
- Starting capital: 100,000
- Current total portfolio value: 99,559.41
- Cash: 35,841.92
- Holdings:
  - CHF 13.0%
  - JPY 13.0%
  - CAD 10.0%
  - MXN 8.0%
  - AUD 8.0%
  - GBP 7.0%
  - EUR 5.0%
  - USD cash 36.0%
- Strategic regime: mild risk-off / defensive USD bias / trade-and-geopolitics aware
- Technical overlay state: overlay available
- Portfolio engine state: live; last valuation timestamp 2026-03-26T23:42:52Z
- Highest-priority adds next run if thesis improves further: CHF, USD cash
- First candidates for rebuild if technicals improve: JPY, CAD
- First candidates for reduction if regime softens: USD cash, CHF
- First candidates for addition on improved global breadth: AUD, EUR
- Avoid unless regime changes materially: NZD, ZAR

## 17. Disclaimer

This report is for informational and educational purposes only and does not constitute investment advice, a solicitation, or a recommendation to transact in any security, derivative, fund, or currency. The model portfolio is a rules-based illustrative framework built for analytical tracking. It does not account for taxes, transaction costs, funding costs, slippage, implementation constraints, legal restrictions, suitability requirements, or investor-specific objectives. Market conditions can change rapidly, including because of central-bank decisions, geopolitical developments, commodity-price shocks, and policy changes. Any use of this report or its model allocations is at the reader’s own risk.
