# V18 — Verified Adaptive Brain

V18 is a verification and attention release.

## Observer verification
The 5-minute workflow remains scheduled every 5 minutes and analyses 1-minute bars plus derived 5-minute structure. The 15-minute workflow remains four times per hour. Observer Audit records completed outputs, requested/analysed assets and gaps so missed runs become visible.

## Adaptive Attention
Baseline 1m/5m coverage is preserved for holdings. Activity, RVOL, move phase, open positions and external attention raise scrutiny for assets that deserve it.

## External Intelligence
External Attention combines:
- existing configured public feeds / YouTube monitor
- CoinGecko trending search attention
- optional NewsAPI headlines when `NEWSAPI_KEY` is configured

Attention is not sentiment and is never an automatic buy/sell signal.

## Brain receipts
Selected producer→consumer paths now leave receipts. Brain Audit treats a link as verified only when a downstream output records that it consumed upstream evidence.

## Strategy integrity
Strategy Lab now has a paper risk stop and an integrity audit that quarantines extreme return records. This directly addresses suspicious values such as average returns below -100%.
