# Crypto Intelligence Terminal V6.1.0

## Automatic four-hour signal recording

This release lets the engine record calls while nobody is using Streamlit.

A GitHub Actions workflow runs every four hours, scans every holding, evaluates the V6 conviction checklist, freezes each completed-candle call and entry price, and opens a paper trade whenever the signal changes into Strong Buy, Buy, Buy Watch, Sell Watch, Sell or Strong Sell.

### New files

- `.github/workflows/four_hour_signal_recorder.yml`
- `scripts/signal_recorder.py`
- `data/signals_latest.json`
- `data/signal_history.json`
- `data/paper_trades.json`
- `data/external_calls.json`

### New page

**Paper Trading** shows open engine paper trades, frozen entries, signal changes and the full signal journal.

## Activate after uploading

1. Upload every extracted file and folder to GitHub.
2. Open the repository **Actions** tab.
3. Choose **Four Hour Signal Recorder**.
4. Click **Run workflow** once.
5. Wait for it to finish.
6. Refresh Streamlit.

The workflow will then run automatically every four hours.

If the workflow cannot commit:
GitHub repository → Settings → Actions → General → Workflow permissions → Read and write permissions.

GitHub scheduled workflows are unattended but can occasionally start late. In a public repository, schedules can be disabled after 60 days without repository activity. The Paper Trading page displays the last recorder timestamp so stale scans are visible.

## Upload

Extract the ZIP, drag all contents into GitHub **Add file → Upload files**, commit, then reboot Streamlit.
