# Crypto Intelligence Terminal V8.9.0

## 15-Minute Observer and Signal Timing Lab

V8.9 adds a separate early-detection engine that analyses 15-minute market data and
compares its detections with the hourly 4H Champion.

### Included

- 15-minute observer signals
- Early Buy and Early Sell detections
- Buy Watch, Sell Watch and Volatility Watch
- 15-minute observer lifecycle and history
- separate USD 100,000 observer paper wallet
- fees, slippage, position limit and cash reserve
- open and closed observer positions
- observer-versus-hourly timing comparisons
- early price advantage measurement
- Early Shift Detection on Watch
- dedicated 15M Observer page
- separate observer workflow

### Workflows

The existing Hourly Signal Recorder also runs the observer once per hour as a reliable
fallback.

A new `15-Minute Observer` workflow attempts runs at minutes 02, 17, 32 and 47 of each
hour. GitHub scheduled jobs may occasionally be delayed, so the displayed run timestamps
are the source of truth.

### Important

The observer is a challenger. It does not replace the 4H Champion or make real trades.

### Upload

1. Extract the ZIP.
2. Upload every extracted item over the existing GitHub repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.
6. Open Actions and run 15-Minute Observer once manually.
7. Open Watch and 15M Observer.

Do not delete the existing data folder. All accumulated records remain protected.
