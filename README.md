# Crypto Intelligence Terminal V8.8.0

## Risk Guardian

V8.8 adds an independent defensive layer that runs after the signal recorder,
Research Desk and Strategy Lab.

Risk Guardian does not create BUY signals. It can only:

- report NORMAL
- report CAUTION
- report INVALIDATION RISK
- report DATA UNRELIABLE
- freeze new calls

### Checks

- stale signal snapshot
- excessive unavailable market data
- external-source failures
- 4H and 12H volatility shocks
- RVOL and price shocks
- bullish calls under bearish pressure
- bearish calls under bullish pressure
- low market participation
- research-wallet drawdown
- asset-level entry vetoes

### New page

Risk Guardian includes:

- overall risk state
- whether new calls are allowed
- portfolio defensive actions
- market and data checks
- asset risk radar
- entry vetoes
- risk history

### Important limitation

The current GitHub workflow still runs hourly. V8.8 adds the defensive logic and audit
trail, but not a genuinely faster-than-hourly worker. A later release can add a separate
15-minute observer once the hourly system has collected enough evidence.

### Upload

1. Extract the ZIP.
2. Upload every extracted item over the existing GitHub repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.

Do not delete the existing data folder. Risk Guardian files are created only when missing.
The stable hourly workflow does not need editing.
