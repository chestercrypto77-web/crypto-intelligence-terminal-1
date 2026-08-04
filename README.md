# Crypto Intelligence Terminal V8.7.0

## Strategy Lab — Champion versus Challengers

V8.7 turns the registered challenger strategies into active unattended paper wallets.

### Strategies

- 4H Conviction V1 — Champion
- Closed Candle Confirmation — Challenger
- RVOL 1.50 — Challenger
- BTC Confirmation — Challenger

Each strategy receives the same hourly market evidence and uses identical:

- USD 100,000 starting capital
- 10% position size
- maximum eight positions
- 20% minimum cash reserve
- 0.10% fee per side
- 0.05% slippage per side
- signal-reversal and HOLD exits

Only the challenger rule differs.

### Strategy Lab page

The new page includes:

- strategy leaderboard
- equity curves
- wallet return
- open and closed trades
- win rate
- average return
- profit factor
- maximum drawdown
- latest activity
- challenger filtering counts
- promotion gate

A challenger cannot become the Champion automatically. The page requires at least
50 closed trades before it can become eligible for manual promotion review.

### Upload

1. Extract the ZIP.
2. Upload every extracted item over the existing GitHub repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.

Do not delete the existing data folder. Strategy Lab data is created only when missing.
The stable hourly workflow does not need editing.
