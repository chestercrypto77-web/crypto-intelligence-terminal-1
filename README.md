# Crypto Intelligence Terminal V6.0.0

## Conviction Engine

V6 turns **4H Intelligence** into the strongest indicator and central decision-support
page in the platform.

### Data architecture

- CoinGecko remains the portfolio price and market metadata source
- Yahoo Finance supplies hourly candles which are resampled into four-hour candles
- Binance confirms four-hour crypto candles when the pair is available
- Every portfolio holding is scanned
- Any additional crypto, US stock or ETF can be investigated on demand
- Data-source names, freshness and candle counts are visible
- Cross-source agreement or conflict is shown

### Decisive calls

The engine produces:

- STRONG BUY
- BUY
- BUY WATCH
- HOLD
- SELL WATCH
- SELL
- STRONG SELL

No 0–100 prediction score is displayed. Calls come from a transparent checklist of
14 observable conditions across:

- Trend
- Volume
- Momentum
- Structure
- Relative strength

Strong calls require agreement across independent categories. The page shows every
passing, failing and neutral condition.

### 4H page

- Action Required scans all portfolio holdings
- Calls are ranked by signal state and current movement
- Deep dive for any holding
- On-demand symbol input for other assets
- Four-hour, 12-hour and 24-hour movement
- RVOL and RVOL change
- RSI, ADX, EMA structure, MACD acceleration
- Green/red candle balance
- Higher highs, higher lows, breakouts and breakdowns
- Source confirmation table
- Explicit call thresholds

## Upload

Extract the ZIP and drag all five extracted items into GitHub
**Add file → Upload files**, commit the replacements, then reboot Streamlit.
