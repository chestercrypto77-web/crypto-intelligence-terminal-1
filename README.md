# Crypto Intelligence Terminal V11.1.0 — PYR Lessons

PYR exposed three weaknesses: a neutral 15-minute reading was treated as a full exit, the legacy Observer learning book used oversized $10k positions, and closed assets were not explicitly reviewed for a fresh re-entry.

V11.1 changes those behaviours.

- NEUTRAL is no longer an exit by itself.
- Existing Observer trades require reversal, invalidation, a 2.25% hard risk stop, or profit-trailing failure.
- Recent exits remain under active 48-hour re-entry surveillance.
- Re-entry is smaller and must re-earn evidence; it is not revenge trading.
- Legacy Observer learning positions are capped at 2.5% of starting cash.
- Closed trades get a concise case file: entry quality, exit quality, re-entry status, process quality and one lesson.
- Raw JSON is removed from the normal Performance Lab review.


## V11.1.1 hotfix
Fixes the Performance Lab NameError by loading trade_reviews before the trade review cards render.


## V11.1.2 hotfix
Two UI regressions are corrected:
- Performance Lab now has the missing `TRADE_REVIEWS_FILE` path and can load structured reviews.
- Portfolio is restored to the main sidebar. The Portfolio page code was still present; it had simply been omitted from navigation.
No wallets, holdings, history, committee records, or learning data are reset.


## V11.1.3 navigation cleanup
The Intelligence page has been removed from the visible sidebar. Its research capability remains available internally to the engines, but it no longer takes up front-line interface space.
