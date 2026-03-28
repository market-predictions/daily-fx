# FX Output Contract — As-Is Split

This file extracts the **presentation, linkability, writing, and required-report-structure** parts of `fx.txt` without intentionally changing logic.
Cross-references to other sections are preserved as written.

---

## 2. CLIENT-GRADE PRESENTATION STANDARD

The report must be structured in two layers.

### Layer A — Client layer
This comes first and must be highly scannable:
1. Executive Summary
2. Portfolio Action Snapshot
3. Global Macro & FX Regime Dashboard
4. Structural Currency Opportunity Radar
5. Key Risks / Invalidators
6. Bottom Line
7. Equity Curve and Portfolio Development

### Layer B — Analyst layer
This comes second and contains full detail:
8. Currency Allocation Map
9. Macro Transmission & Second-Order Effects Map
10. Current Currency Review
11. Best New Currency Opportunities
12. Portfolio Rotation Plan
13. Final Action Table
14. Position Changes Executed This Run
15. Current Portfolio Holdings and Cash
16. Carry-forward Input for Next Run
17. Disclaimer

### Rule
The client layer must be understandable on its own.
The analyst layer must support and justify the client layer.
Do not begin with dense scorecards or long diagnostics.
Always start with what changed, what to do, and why.

---

## 2A. VISUAL DELIVERY CONTRACT FOR HTML + PDF

The HTML body and PDF are rendered by a downstream delivery script. Your job is to write content that fits that premium visual system cleanly.

### Visual intent
The delivered report must feel like a premium weekly private-bank style briefing, not a generic word-processor export, dashboard toy, or PowerPoint-like mock-up.

The HTML email is the lead client-facing product.
The PDF must follow the same design language, but it must not force the email into a PDF-like reading experience.

### Core visual principles
The delivery system assumes:
- a light warm paper background
- a darker slate-teal header band
- a serif masthead for the product name only
- sans-serif body typography
- restrained champagne accent rules
- minimal icon use
- strong spacing discipline
- no decorative repetition
- clear separation between executive layer and analyst appendix
- compact, clean tables where tables improve scanning
- PDF layout that follows the ETF-family design language while remaining print-safe
- portrait-friendly PDF pagination when that improves executive readability and table fit

### Presentation parity rule with the ETF sister report
The FX review must feel like the same reporting family as the ETF review:
- same visual hierarchy
- same executive restraint
- same premium email-first feel
- same clean section-kicker treatment
- same compact table discipline
- same analyst appendix separation
- same subdued subgroup labeling
- same controlled spacing
- same avoidance of dashboard clutter

Do not introduce a separate FX-specific visual language unless the content truly requires it.

### Non-negotiable presentation rules
Write in a way that supports a clean executive email:
- no repeated section naming inside the same section
- no duplicate header text that says the same thing twice
- no decorative internal labels such as "institutional", "client edition", "HTML/PDF", or implementation notes inside the report body
- the executive header subtitle must show only the fully written report date, not the report title repeated again
- the executive header may use a discreet right-aligned label "Investor Report" if it is visually balanced and subordinate to the masthead
- no unnecessary placeholder language such as "Suggested visual treatment"
- no visual clutter caused by too many colored pills, soft badges, or app-like UI elements
- no cheap or playful icon use inside the body
- no repeated decorative section headers where the body already makes the section purpose obvious
- no large analyst blocks that rely only on paragraph flow to separate one currency or idea from the next
- no long unbroken walls of bullets when a compact table would communicate better
- no excessive subheading variation that creates visual noise without adding hierarchy

### Writing rules required by the visual system
Write in a way that supports premium HTML/PDF rendering:
- Keep section openings short and decisive.
- Keep the Executive Summary compact and highly scannable.
- Keep action lists tight; do not flood the action snapshot with long bullets.
- Use short label-value lines where the structure asks for them.
- Keep tables compact, complete, and cleanly formatted.
- Preserve true line breaks in Markdown tables and lists; do not collapse them into escaped newline text.
- Avoid unnecessary filler sentences before the main conclusion.
- Do not write comments about formatting, design, rendering, or file generation into the report content.
- Prefer concise paragraphs over long narrative blocks.
- Keep repetitive wording to a minimum, especially across the executive sections.
- When the same point already appears in Executive Summary or Bottom Line, do not restate it again unless the later section adds new information.

### Email-first execution addendum
The HTML email must read as a premium executive briefing first, and only secondarily as a full archival report.
That means the analyst appendix must remain complete in substance, but it must be rendered in a compact, controlled format.

The delivery layer should therefore prefer:
- compact summary cards at the top
- table-first rendering where possible
- clear visual separation between one currency and the next
- one consistent heading hierarchy
- reduced decorative variation in the analyst appendix
- minimal vertical waste

Do not design the email as a long scrolling analyst memo with lightly styled markdown pasted into a card shell.

### Section-specific formatting expectations
The delivery system expects the following:
- Executive Summary: compact summary lines plus a single decisive main takeaway.
- Portfolio Action Snapshot: present the action states in a compact, executive-friendly structure that can be rendered as a clean table or matrix.
- Section badges / numbered headers must remain visually centered and aligned with their heading text in the final email render.
- Global Macro & FX Regime Dashboard: no repeated heading inside the section body.
- Structural Currency Opportunity Radar: no repeated heading inside the section body.
- Current Currency Review: each currency block must begin with a clearly identifiable currency / stance heading and remain visually distinct from the next currency.
- Best New Currency Opportunities: each ranked opportunity must have a clean title line; avoid raw bracket-style labels such as `[Rank #1]` in the rendered output.
- Section kickers: the numeric badge, blue circle, and section title must be optically centered and aligned in the rendered email.
- Best New Currency Opportunities subgroup lines such as `A. Macro-derived opportunities` and `B. Structural opportunities` must render as subdued subgroup labels, clearly subordinate to the specific opportunity titles beneath them.
- Portfolio Rotation Plan: content must be cleanly renderable as a compact table or matrix instead of a long vertical bullet stack.
- Carry-forward Input for Next Run: preserve the required canonical sentence exactly in the markdown source, but do not display that sentence in the delivered client-facing HTML/PDF.
- The analyst appendix may restart the displayed section numbering from 1 and may use its own full header band with the fully written report date and a discreet right-aligned label "Analyst Report".
- Key Risks: render as a compact invalidator list; do not let it visually dissolve into generic bullets.
- Equity Curve and Portfolio Development: the chart must appear inside the section itself in the delivered HTML/PDF, not as a visually disconnected appendix item.
- Analyst appendix: preserve full substance, but render dense sections in a table-first, compressed style suitable for email reading.
- Section numbering badges are optional but, if used, they must align cleanly with the section label and must not create visual clutter.

### Icon rule
Icons are optional, not mandatory.
If icons are used at all, use them sparingly and only where they clearly improve scanability.
Do not rely on icons to create hierarchy.
Do not create a different icon treatment for every subsection.
The email should still look complete and premium if almost all body icons are removed.

### Delivery-script expectations
The downstream HTML renderer should, where possible:
- convert the portfolio action snapshot into a compact decision table
- convert the portfolio rotation plan into a compact matrix / table
- visually separate each current currency review from the next using a distinct heading treatment or card boundary
- remove raw bracketed labels such as `[Rank #1]` from rendered opportunity titles
- keep PDF generation aligned with the ETF-family email system, but allow a print-safe fallback layout when pagination requires it
- preserve the same design family as the ETF sister report
- prefer portrait-safe PDF behavior when that produces a tighter executive result

### Disclaimer display rules
Use this exact structure immediately below the title:
> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

---

## 2B. TRADINGVIEW LINK CONTRACT

The delivered HTML email and PDF should make standalone currency mentions clickable to TradingView.

### Purpose
The goal is that clients and internal readers can jump directly from the narrative to a live chart in one click.

### Mapping rule
Use this canonical TradingView mapping:
- USD -> `https://www.tradingview.com/chart/?symbol=DXY`
- EUR -> `https://www.tradingview.com/chart/?symbol=EURUSD`
- GBP -> `https://www.tradingview.com/chart/?symbol=GBPUSD`
- AUD -> `https://www.tradingview.com/chart/?symbol=AUDUSD`
- NZD -> `https://www.tradingview.com/chart/?symbol=NZDUSD`
- JPY -> `https://www.tradingview.com/chart/?symbol=1/USDJPY`
- CHF -> `https://www.tradingview.com/chart/?symbol=1/USDCHF`
- CAD -> `https://www.tradingview.com/chart/?symbol=1/USDCAD`
- MXN -> `https://www.tradingview.com/chart/?symbol=1/USDMXN`
- ZAR -> `https://www.tradingview.com/chart/?symbol=1/USDZAR`

### Writing rule for linkability
To support renderer-side auto-linking:
- keep standalone currency mentions as plain uppercase ISO codes where possible: `USD`, `EUR`, `JPY`, `CHF`, etc.
- do not hide intended clickable currency mentions inside code blocks
- do not replace standalone currency labels with long-form names when the ISO code is the clearer decision label
- do not rely on pair strings such as `USDJPY` or `EURUSD` when the decision is at the currency level; pair strings are evidence, not the clickable currency label itself

### Minimum locations where linkable currency labels are expected
Where natural, keep currency labels clean and standalone in:
- Executive Summary
- Currency Allocation Map
- Current Currency Review
- Best New Currency Opportunities
- Portfolio Rotation Plan
- Final Action Table
- Current Portfolio Holdings and Cash

### Delivery rule
The downstream HTML/PDF renderer should:
- wrap standalone currency mentions with the TradingView URL from the mapping above
- preserve those links in the PDF where possible
- set links to open in a new tab in the HTML delivery layer

---

## 12. REPORT WRITING RULES

The report must:
- stay decisive
- stay concise
- stay premium
- stay readable
- stay repeatable

### Action language
Use explicit labels:
- Buy
- Hold
- Reduce
- Sell
- Watch
- Build on weakness
- Hold / stage

### Tone
- institutional
- disciplined
- compact
- decision-led
- not promotional
- not chatty
- not theatrical

### Pair evidence rule
When you cite technical pair evidence:
- keep it subordinate to the currency conclusion
- do not let pair details overwhelm the client layer
- keep pair-heavy detail primarily in the analyst layer

### Currency mention rule
When a sentence is really about a currency decision, prefer a standalone uppercase currency label such as `USD`, `EUR`, `JPY`, or `CHF` over a long-form name or a pair string, because the delivery layer may convert those standalone currency mentions into TradingView links.

---

## 13. REQUIRED OUTPUT STRUCTURE

The final report must contain **all** of the following sections in this exact order.

# Weekly FX Review

> *This report is for informational and educational purposes only; please see the disclaimer at the end.*

## 1. Executive summary

## 2. Portfolio action snapshot

## 3. Global macro & FX regime dashboard

## 4. Structural currency opportunity radar

## 5. Key risks / invalidators

## 6. Bottom line

## 7. Equity curve and portfolio development

### Section 7 content rule
When valuation files exist, Section 7 must be sourced from actual portfolio valuation data, not from narrative carry-forward alone.
It must include, at minimum:
- valuation date
- NAV (USD)
- since inception return (%)
- daily or latest period return (%) where available
- realized P&L (USD) where available
- unrealized P&L (USD) where available
- a compact valuation history table

If valuation files do not yet exist, say so explicitly and use a deterministic fallback.

## 8. Currency allocation map

## 9. Macro transmission & second-order effects map

## 10. Current currency review

## 11. Best new currency opportunities

## 12. Portfolio rotation plan

## 13. Final action table

### Section 13 authority rule
Section 13 is the authoritative target-allocation table for the model portfolio at the end of the run.
The portfolio engine is expected to translate this section into implementation weights and positions.

## 14. Position changes executed this run

### Section 14 execution rule
Section 14 must explicitly state whether changes were actually implemented in the model portfolio on this run.
If the engine rebalanced the portfolio, state the changes.
If no rebalance occurred, say so explicitly.

## 15. Current portfolio holdings and cash

Required labels inside Section 15:
- Starting capital (USD):
- Invested market value (USD):
- Cash (USD):
- Total portfolio value (USD):
- Since inception return (%):
- Base currency:

### Section 15 content rule
When portfolio-state files exist, Section 15 must be sourced from actual open positions and cash.
The holdings table should, where available, include:
- currency sleeve
- implementation pair
- direction
- entry date
- entry price
- current price
- gross exposure (USD)
- unrealized P&L (USD)
- current weight (%)
- stance

Where natural, keep the currency sleeve labels as standalone uppercase currency codes so the delivery layer can hyperlink them to TradingView.

If portfolio-state files do not yet exist, use the target allocation table and state that Section 15 is a fallback representation rather than a live marked-to-market holdings table.

## 16. Carry-forward input for next run

This exact sentence must appear in the markdown source:
**This section is the canonical default input for the next run unless the user explicitly overrides it.**

## 17. Disclaimer
