# Weekly FX Review

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary

This is a same-day continuation run using the carry-forward state from the most recent stored FX report, the refreshed technical overlay in `output/fx_technical_overlay.json`, and the live implementation files in `output/fx_portfolio_state.json` and `output/fx_valuation_history.csv`.

The strategic regime remains **mild risk-off with a defensive USD bias**. No new official central-bank action was identified since version 03. The ranking therefore remains **USD first, CHF second**, with **JPY retained as a smaller staged hold**, **AUD retained as a staged hold**, and **EUR / GBP kept in reduce territory**. The main operational nuance on this run is that the technical overlay has been refreshed more recently than the current portfolio-engine valuation snapshot, so the strategic read uses the fresher overlay while Sections 7 and 15 still reflect the latest committed engine state.

## 2. Portfolio action snapshot

- **Build:** USD
- **Add / build on weakness:** CHF
- **Hold / stage:** JPY, MXN, AUD
- **Hold:** CAD
- **Reduce / underweight:** EUR, GBP
- **Sell / avoid:** NZD, ZAR
- **Cash stance:** keep USD cash at **36%**
- **Change vs prior run:** no additional portfolio changes executed this run

## 3. Global macro & FX regime dashboard

- **Global macro regime:** Positive but fragile growth; resilience offset by trade-policy uncertainty and geopolitical stress
- **Policy divergence:** USD remains rate-rich versus EUR and NZD; JPY normalization remains constructive in macro terms but is not confirmed by the current technical overlay
- **Risk regime:** Mild risk-off
- **USD liquidity / funding:** Supportive for USD
- **Commodity impulse:** Positive for CAD in macro terms; more constructive for AUD on technicals; adverse for major oil importers
- **Technical overlay:** Same-day available; USD positive, EUR strong negative, GBP strong negative, JPY strong negative, AUD positive, CAD negative, others mixed

The reviewed official policy backdrop still supports a defensive dollar bias. The Fed range remains 3.50–3.75%, the ECB deposit facility remains 2.00%, the BoE Bank Rate remains 3.75%, and the RBA cash rate target remains 3.85%. That combination leaves USD well-supported on carry and liquidity, while AUD can remain tactically interesting without overtaking USD or CHF in the portfolio hierarchy.

## 4. Structural currency opportunity radar

| Theme | Status | Current read |
|---|---|---|
| Dollar liquidity premium | active / investable | Elevated trade and geopolitical uncertainty keep USD demand firm |
| Swiss defensive role with intervention risk | active / investable | CHF remains the cleaner second-line defensive sleeve because macro is constructive and technicals are not fighting the thesis |
| Yen haven asymmetry | active / watch | Haven logic remains intact, but the current overlay is still strongly negative, so position size should stay controlled |
| Commodity FX recovery | active / watch | AUD technicals remain improved, while CAD’s near-term technical confirmation has softened |
| Europe cyclical repair | fading / under pressure | Lower ECB rates, soft growth momentum, and negative technical confirmation keep EUR weak |
| EM carry under controlled volatility | active / watch | MXN remains carry-positive, but the overlay is only mixed |
| High-beta EM beta | invalidated | ZAR remains unattractive into a defensive, oil-shock-aware regime |

## 5. Key risks / invalidators

- A rapid and durable de-escalation in geopolitical risk plus a sharp oil reversal would reduce the USD / CHF defensive premium.
- A decisive broadening of non-US growth plus faster Fed easing would weaken the USD-overweight case.
- A reversal in USDJPY technical strength would improve the case for rebuilding JPY more aggressively.
- A material improvement in euro-area growth with no renewed energy pressure would improve EUR.
- A cleaner global risk-on reset would help AUD, NZD and ZAR faster than this framework currently assumes.

## 6. Bottom line

The correct portfolio posture remains **defense first, optionality second, high-beta last**. There is still no new evidence since version 03 that justifies another rebalance. USD remains the strongest core anchor. CHF remains the cleaner secondary defensive allocation than JPY on this run. JPY stays in the portfolio at reduced size. AUD remains a staged allocation. Operationally, the strategic overlay has moved forward, but the live portfolio files still reflect the latest executed rebalance rather than a new one.

## 7. Equity curve and portfolio development

Valuation source: **Twelve Data latest completed daily bars / overlay reuse**.  
Valuation date: **2026-03-25**.  
Engine overlay timestamp: **2026-03-25T12:08:31Z**.

- Net asset value (USD): **100,000**
- Cash (USD): **36,000**
- Gross exposure (USD): **64,000**
- Net exposure (USD): **64,000**
- Realized P&L (USD): **0.0**
- Unrealized P&L (USD): **0.0**
- Daily return (%): **0.0**
- Since inception return (%): **0.0**
- Max drawdown (%): **0.0**

The equity curve remains flat because the live portfolio engine has only just been initialized and the valuation history still contains only the inception row. This is an implementation-history limitation, not a narrative placeholder.

| Date | NAV (USD) | Daily return (%) | Since inception return (%) | Drawdown (%) | Comment |
|---|---:|---:|---:|---:|---|
| 2026-03-25 | 100,000 | 0.0 | 0.0 | 0.0 | Portfolio engine initialized from v02 allocation |

## 8. Currency allocation map

| Currency | Strategic score | Action | Role in portfolio |
|---|---:|---|---|
| USD | 16.5 | Buy | Base, liquidity buffer, defensive anchor |
| CHF | 11.6 | Build on weakness | Defensive diversifier with cleaner current confirmation than JPY |
| JPY | 10.6 | Hold / stage | Haven sleeve retained, but current technical confirmation is strongly negative |
| CAD | 9.4 | Hold | Oil / terms-of-trade support with weaker near-term technical confirmation |
| MXN | 8.0 | Hold / stage | Carry-positive, size moderated by risk regime |
| AUD | 7.8 | Hold / stage | Positive technical overlay offsets part of the macro drag |
| GBP | 6.8 | Reduce | Rate support remains, but negative technical confirmation weakens the case |
| EUR | 6.2 | Reduce | Lower-rate bloc with energy sensitivity and negative technical confirmation |
| NZD | 5.2 | Sell / avoid | Low-rate recovery story lacks urgency |
| ZAR | 5.0 | Sell / avoid | High-beta EM exposure not paid enough in this regime |

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
The Fed range still favors USD on carry and liquidity. The updated technical overlay is now modestly more supportive for the dollar than in earlier same-day versions. USD remains the highest-quality base sleeve.

**EUR — Reduce**  
The ECB deposit facility remains low relative to the Fed, and the updated overlay is now explicitly strong negative on EUR. Macro and technical signals continue to align to the downside.

**JPY — Hold / stage**  
The macro haven thesis remains intact, but the current overlay still shows a strong negative JPY confirmation through USDJPY strength. JPY remains in the portfolio, but the correct stance is a smaller staged hold rather than a larger haven sleeve.

**CHF — Build on weakness**  
CHF remains one of the cleanest defensive diversifiers. The current overlay is mildly negative for CHF, which tempers sizing but does not break the broader strategic case.

**GBP — Reduce**  
GBP retains some rate support, but the current technical overlay remains strong negative. With no new positive macro catalyst, the macro and technical picture still justifies a reduction.

**AUD — Hold / stage**  
The RBA still shows a 3.85% cash rate after February’s hike, and the overlay remains positive on AUDUSD. AUD is still cyclical and not a leadership currency in a mild risk-off world, but it still deserves a staged allocation.

**CAD — Hold**  
CAD’s main support remains oil and terms of trade rather than policy leadership. But the current technical overlay for USDCAD is still positive, which means CAD confirmation remains weak. That argues for a smaller hold rather than a larger sleeve.

**NZD — Sell / avoid**  
The strategic case remains weak and the overlay has deteriorated to negative, which is not enough to justify a rebuild.

**MXN — Hold / stage**  
MXN remains carry-positive, but the overlay is only mixed, so the correct stance remains selective holding rather than aggressive adding.

**ZAR — Sell / avoid**  
ZAR remains the wrong kind of exposure for a defensive portfolio with geopolitical and trade-policy awareness. The overlay is only mixed and does not rescue the weak strategic case.

## 11. Best new currency opportunities

1. **CHF** — The cleanest incremental defensive addition because the macro thesis is intact even though the overlay is no longer as supportive as earlier in the day.
2. **USD via elevated cash** — The strongest base-currency expression remains additional USD cash.
3. **AUD as a staged allocation** — Not a full regime winner, but the positive technical overlay still makes a modest staged sleeve more attractive than before.

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

No additional position changes were executed on this run. The live portfolio state still reflects the rebalance executed from version 02.

## 15. Current portfolio holdings and cash

- Starting capital (USD): **100,000**
- Invested market value (USD): **64,000**
- Cash (USD): **36,000**
- Total portfolio value (USD): **100,000**
- Since inception return (%): **0.0**
- Base currency: **USD**

| Currency sleeve | Implementation pair | Direction | Entry date | Entry price | Current price | Gross exposure (USD) | Unrealized P&L (USD) | Current weight (%) | Stance |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| CHF | USDCHF -> CHFUSD | Long CHF | 2026-03-25 | 1.26786099 | 1.26786099 | 13,000 | 0.0 | 13.0 | Build on weakness |
| JPY | USDJPY -> JPYUSD | Long JPY | 2026-03-25 | 0.00629635 | 0.00629635 | 13,000 | 0.0 | 13.0 | Hold / stage |
| CAD | USDCAD -> CADUSD | Long CAD | 2026-03-25 | 0.72498441 | 0.72498441 | 10,000 | 0.0 | 10.0 | Hold |
| MXN | USDMXN -> MXNUSD | Long MXN | 2026-03-25 | 0.05639694 | 0.05639694 | 8,000 | 0.0 | 8.0 | Hold / stage |
| AUD | AUDUSD | Long AUD | 2026-03-25 | 0.69675000 | 0.69675000 | 8,000 | 0.0 | 8.0 | Hold / stage |
| GBP | GBPUSD | Long GBP | 2026-03-25 | 1.34207000 | 1.34207000 | 7,000 | 0.0 | 7.0 | Reduce |
| EUR | EURUSD | Long EUR | 2026-03-25 | 1.16077000 | 1.16077000 | 5,000 | 0.0 | 5.0 | Reduce |
| USD cash | — | Long USD cash | 2026-03-25 | 1.00000000 | 1.00000000 | 36,000 | 0.0 | 36.0 | Buy |

## 16. Carry-forward input for next run

**This section is the canonical default input for the next run unless the user explicitly overrides it.**

- Report type: Weekly FX Review
- Run date: 2026-03-25
- Run version: 04
- Base currency: USD
- Starting capital: 100,000
- Current total portfolio value: 100,000
- Cash: 36,000
- Holdings:
  - USD cash 36%
  - JPY 13%
  - CHF 13%
  - CAD 10%
  - MXN 8%
  - AUD 8%
  - GBP 7%
  - EUR 5%
  - NZD 0%
  - ZAR 0%
- Strategic regime: mild risk-off / defensive USD bias / trade-and-geopolitics aware
- Technical overlay state: available same-day and fresher than current engine valuation; USD positive, EUR strong negative, GBP strong negative, JPY strong negative, AUD positive, CAD negative, NZD negative, others mixed
- Portfolio engine state: initialized on 2026-03-25; valuation history currently contains inception row only
- Highest-priority adds next run if thesis improves further: CHF, USD cash
- First candidates for rebuild if technicals improve: JPY, CAD
- First candidates for reduction if regime softens: USD cash, CHF
- First candidates for addition on improved global breadth: AUD, EUR
- Avoid unless regime changes materially: NZD, ZAR

## 17. Disclaimer

This report is for informational and educational purposes only and does not constitute investment advice, a solicitation, or a recommendation to transact in any security, derivative, fund, or currency. The model portfolio is a rules-based illustrative framework built for analytical tracking. It does not account for taxes, transaction costs, funding costs, slippage, implementation constraints, legal restrictions, suitability requirements, or investor-specific objectives. Market conditions can change rapidly, including because of central-bank decisions, geopolitical developments, commodity-price shocks, and policy changes. Any use of this report or its model allocations is at the reader’s own risk.