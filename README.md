# Crypto Intelligence Terminal V13.1.0 — Microstructure Intelligence

V13.1 adds a dedicated 1-minute / 5-minute execution-timing layer.

The important change is semantic: a local top is no longer treated as automatically meaning
"open a Short", and a local bottom is no longer automatically "open a Long".

The microstructure observer distinguishes:

- LONG ENTRY
- SHORT ENTRY
- LONG EXIT / PROFIT PROTECT
- SHORT EXIT / PROFIT PROTECT
- LONG PULLBACK WATCH
- SHORT PULLBACK WATCH
- LONG REVERSAL WATCH
- SHORT REVERSAL WATCH
- NO ACTION

This lets the system learn the difference between:
1. protect profit on an existing position,
2. wait through a pullback,
3. open a new opposite-direction trade,
4. re-enter the original trend.

The new 5-minute GitHub workflow fetches 1-minute bars and derives 5-minute structure every run.
GitHub scheduled Actions cannot reliably execute every single minute; 5 minutes is the practical
cadence in the current infrastructure. Each run still studies the underlying 1-minute bars.

The microstructure analyst is deliberately lower weight than the higher-timeframe Committee.
1m noise improves timing; it must not become the whole thesis.
