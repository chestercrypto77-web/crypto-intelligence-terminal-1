# Crypto Intelligence Terminal V7.0.0

V7 adds a complete accountability and performance layer.

## Performance tracking
Every engine and external paper trade records directional results after:
- 1 hour
- 4 hours
- 12 hours
- 24 hours
- 3 days
- 7 days

It also records best favourable return, worst adverse return, and an automatic seven-day Win, Loss or Flat outcome. Long and short calls are measured correctly in opposite directions.

## Performance Lab
Compares Our Engine, Sheldon the Sniper, Mark and other sources using:
- Calls and evaluated calls
- Win rate
- Average return
- Average winner and loser
- Profit factor
- Full call-by-call checkpoint table

## Sheldon calls
Paper Trading includes a reviewed external-call builder. It prepares an updated `external_calls.json` file. Download it, replace `data/external_calls.json` in GitHub, and the hourly recorder will begin tracking the call separately.

## GitHub Actions setup
Your browser skipped the hidden `.github` folder. This release includes a visible backup:
`WORKFLOW_SETUP/hourly_signal_recorder.yml`

If Actions still shows “Get started with GitHub Actions”:
1. Click **set up a workflow yourself**
2. Name it `hourly_signal_recorder.yml`
3. Replace the example with the contents of the visible backup file
4. Commit it
5. Run **Hourly Signal Recorder**

A standalone workflow file is also provided beside the release ZIP.

## Upload
Extract the ZIP and drag all visible extracted files and folders into GitHub **Add file → Upload files**, commit, and reboot Streamlit.
