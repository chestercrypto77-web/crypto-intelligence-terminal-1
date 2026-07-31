# Crypto Intelligence Terminal V5.4.3

Live Move Detection update, built directly from V5.4.2.

## Why this update was needed

A fast move could appear clearly on an exchange chart while the portfolio pages still
looked neutral or negative. The main portfolio used only the CoinGecko 24-hour field,
while the 4H tools used separate Yahoo hourly candles. Those feeds could disagree or
refresh at different times.

## Changes

- Added two-minute hourly move detection for held assets
- Added 1-hour, 6-hour and 24-hour observed returns
- Added recent green/red candle counts
- Added hourly RVOL and RVOL change
- Uses the freshest available 24-hour return between CoinGecko and hourly candles
- Shows the selected data source and age
- Added **Moves now** to Today
- Added **Live portfolio moves** to Portfolio
- Replaced hidden score-based attention ordering with observable move ordering
- Positive movers are now ranked by 6-hour, 1-hour and 24-hour movement
- Research now shows source and data freshness

No confidence scores or prediction scores were added.

## Upload

Extract the ZIP, drag all five extracted items into GitHub **Add file → Upload files**,
commit the replacements, then reboot Streamlit.
