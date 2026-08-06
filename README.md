# Crypto Intelligence Terminal V9.0.1

## Trading Visibility Interface Rebuild

V9.0.1 rebuilds Trading Desk, Strategy Lab and Performance Lab using the same colour-coded
card design as Markets and Watch.

### Front-line trading information

Open and closed trades now show only:

- asset
- wallet or strategy
- Long or Short
- entry
- current or exit price
- return
- allocated capital or result
- current status

Full evidence, risk, journal and raw records remain behind expandable trade panels.

### Strategy Lab

- one card per Champion or Challenger
- wallet value
- total return
- latest change
- open and closed trades
- win rate
- drawdown
- meaningful equity comparison only when enough history exists

### Performance Lab

- recent completed-trade cards
- net realised result
- win rate
- average return
- performance by wallet
- meaningful wallet equity chart
- Observer versus hourly timing
- learning evidence after enough completed trades

### 15-minute Observer

Observer remains visible under Trading Desk with wallet equity, cash, open and closed
positions, latest change, equity history and activity.

## Upload

1. Extract the ZIP.
2. Upload all extracted items over the current repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.
6. Run 15-Minute Observer once.
7. Check Trading Desk, Strategy Lab and Performance Lab.
