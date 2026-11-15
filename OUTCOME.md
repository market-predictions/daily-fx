# OUTCOME — daily-fx (FX-rapport, productie)

> **CONCEPT (2026-11-15)** — opgesteld door Claude uit de README, de oude missie en de recente runs. De eigenaar bevestigt of past aan; tot dan geldt dit als werkhypothese, niet als besluit.

**Doel:** Een correct FX-rapport per e-mail bij de lezers, volgens een vast ritme.

**Klaar als:**
- Het rapport is op de geplande dag verzonden (workflow `run-and-send-weekly-fx-report.yml` geslaagd).
- De dagelijkse runs (`generate_predictions.yml`, `run-fx-technical-overlay.yml`) slagen. Op 14-11 faalden beide minstens één keer.
- Nog te bouwen: één `acceptance.yml` die het rapport zelf controleert (cijfers kloppen met de state, niets ontbreekt).

**Alleen met akkoord van de eigenaar:** ontvangerslijst; verzendmodus; beslisregels van de portefeuille.

**Status:** laatste runs van de verzend-workflow.

## Open vragen aan de eigenaar
- Ritme: dagelijks of wekelijks? De repo heet daily, maar de verzend-workflow heet weekly.
- Wie zijn de lezers op dit moment?

## Besluiten
- 2026-11-15 — Overgestapt op het outcome-first model (control-plane). Oudere plan-, status- en controledocumenten in deze repo zijn niet meer leidend.
