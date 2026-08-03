# Crypto Intelligence Terminal V6.1.1

## Hourly automatic signal recording

This release changes the unattended call engine from one scan every four hours to one scan every hour.

The engine still evaluates the **four-hour trading framework**. Running it hourly allows the platform to detect a developing change during the current four-hour window rather than waiting up to four hours for the next scheduled job.

### Every hour the recorder

1. Reads every holding from `holdings.json`
2. Retrieves current Yahoo Finance and Binance candle data where available
3. Evaluates the V6 conviction checklist
4. Compares each asset with its previously recorded call
5. Records a new signal-history entry when the state changes
6. Opens a paper trade when an actionable signal changes into:
   - Strong Buy
   - Buy
   - Buy Watch
   - Sell Watch
   - Sell
   - Strong Sell
7. Freezes the timestamp, entry price, evidence and source
8. Commits the updated records to GitHub

### Duplicate protection

Hourly scans do not repeatedly open the same trade. A paper trade is created only when the signal state changes, and signal IDs include the asset, call and four-hour candle time.

### Important distinction

This is an **hourly scan of a four-hour signal model**. Signals developing inside an unfinished four-hour candle may change before that candle closes. We will preserve those changes so the Performance Lab can later compare early intrabar calls with confirmed closed-candle calls.

## Upload and activate

1. Extract the ZIP.
2. Drag every extracted file and folder into GitHub **Add file → Upload files**.
3. Commit the replacement files.
4. Reboot Streamlit.
5. Open GitHub **Actions**.
6. Select **Hourly Signal Recorder**.
7. Click **Run workflow** once and confirm it succeeds.

After that, the workflow runs at 17 minutes past every hour.
