# Crypto Intelligence Terminal V12.2.0 — Diagnostics & Challenger Arena

V12.2 makes intelligence improvement an operating loop rather than a slogan.

## Every loss becomes homework

`trade_diagnostics.py` classifies every completed result using the evidence that was
actually captured. Examples:

- ENTRY NEVER WORKED
- WEAK ENTRY / FAST ADVERSE MOVE
- WINNER GIVEN BACK
- CONTROLLED RISK LOSS
- EXIT / RE-ENTRY FAILURE
- PROFIT UNDER-CAPTURED
- WIN — PROCESS REVIEW

MFE (maximum favourable excursion), MAE (maximum adverse excursion), exit behaviour and
post-exit movement are kept separate so the engine can distinguish entry mistakes from
management mistakes.

## Winner vs loser comparison

The engine compares captured entry conditions across winners and losers: participation,
volume change, multi-timeframe returns and bullish/bearish evidence. Legacy trades with
missing snapshots are not silently invented.

## Challenger Arena

Four shadow strategies now compete with identical position sizing and trade management:

- Base Committee
- Volume Confirmation
- Multi-Timeframe Confirmation
- Selective Edge

Because management is held constant, the experiment primarily tests entry selectivity.
They use shadow paper only. They cannot touch Core, Swing or Scalp capital and cannot
change live rules.

A challenger is only marked eligible for human review after at least 30 closed trades,
55% win rate, profit factor >= 1.25 and expectancy >= +0.20%. Promotion is never automatic.
