# Crypto Intelligence Terminal V13.0.0 — Connected Intelligence & Market School

V13 changes the architecture from several useful engines into one connected learning system.

## Market School

`market_school.py` studies every chart state recorded in `observer_history.json`, not just
positions the system happened to trade. It labels what subsequently happened over 1H, 4H,
12H and 24H and builds repeated-pattern evidence from:

- Observer state
- relative volume and its acceleration
- RSI zone
- MACD state
- breakout / breakdown / range structure
- bullish vs bearish condition alignment

It also records large moves of 8%+ so missed opportunities become training examples.

Future prices are used only to label historical examples. The live committee never receives
the future label for the current setup.

## Shared Intelligence Bus

`intelligence_hub.py` connects current Observer evidence, hourly signals, Investment Committee,
Risk Guardian, Market School, Diagnostics, Learning Engine and Challenger Arena into one
structured asset dossier.

## Market Memory analyst

The Investment Committee now has an independent Market Memory analyst. It only votes when
historical analogues have enough samples. Immature evidence remains neutral.

## Feedback upstream

The Portfolio Manager reads the shared bus. Mature historical evidence may modestly boost or
reduce candidate ranking, but it cannot override the Risk Guardian or Committee permissions.

Every new Core/Swing position stores its `case_id`, committee snapshot, entry features and
shared-intelligence snapshot so later diagnostics can identify which specialist was right or
wrong.

This release borrows architectural lessons, not code, from production/open quantitative
frameworks: event/message-bus communication, modular controllers/executors, research-to-live
consistency, ensemble decision making, backtesting discipline and anti-lookahead validation.
