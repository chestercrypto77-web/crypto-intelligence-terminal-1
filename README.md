# Crypto Intelligence Terminal V8.6.2

## Engine Health display fix

V8.6.2 fixes the Research Desk `NameError` introduced in V8.6.1.

The Engine Health JSON file was correctly created and updated by the hourly workflow,
but the Streamlit page did not load it into the Research Desk page before attempting
to display it.

No trading records, wallet positions, signal history or evidence data are reset.

## Upload

1. Extract the ZIP.
2. Upload every extracted item over the existing GitHub repository.
3. Commit.
4. Reboot Streamlit.

Running the Hourly Signal Recorder again is optional because this fix only affects the
page display. Your existing `engine_health.json` data will be shown immediately after
Streamlit reloads.
