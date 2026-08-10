# V12.1.0 Complete Safe Upload

1. Extract the ZIP.
2. GitHub → Add file → Upload files.
3. Upload every extracted item over the repository.
4. Do not delete the existing `data` folder.
5. Commit.
6. Reboot Streamlit.
7. Run Hourly Signal Recorder once.
8. Run 15-Minute Market Observer once.

Then open Performance Lab and expand a trade.

The review engine will rebuild visual trade replays from the existing protected
`observer_history.json` and `signal_history.json` records where available.
