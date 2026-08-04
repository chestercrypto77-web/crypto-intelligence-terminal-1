# Crypto Intelligence Terminal V8.8.1

## Watch and Strategy Lab Audit

This complete safe-upload release focuses on usability and proving that unattended
strategy wallets are updating correctly.

### Watch rebuild

Watch is now a colour-coded attention desk with:

- Immediate Attention
- Building Momentum
- Losing Momentum
- Risk Guardian Attention
- Research Candidates

Each item shows its call, 4H and 24H movement, RVOL, lifecycle and the fixed reason it
appeared on the page.

### Strategy Lab corrections

- Closed Candle Challenger now checks whether the 4H candle has actually completed.
- Challenger entry filters only control opening a position.
- Positions no longer close merely because RVOL or BTC confirmation later stops passing.
- Exits use the common base-engine reversal or HOLD rule.
- Previous equity, current equity and change this run are stored.
- Every wallet has a heartbeat.
- Every retained, opened, closed, filtered and rejected action is journalled.
- The page displays last run, market snapshot, wallets updated and database-save state.
- Workflow logs now expose each wallet's current change and activity.

### Upload

1. Extract the ZIP.
2. Upload every extracted item over the existing GitHub repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.
6. Check Watch and Strategy Lab.

Do not delete the existing data folder. Current strategy wallets and historical records
remain protected and will be upgraded in place.
