# V11.0.0 complete safe upload

Do not delete the existing `data` folder.

1. Extract this ZIP.
2. GitHub → Add file → Upload files.
3. Drag every extracted item into the upload area.
4. Commit.
5. Reboot Streamlit.
6. Run Hourly Signal Recorder once.

The workflow should show:

- risk_guardian.py
- investment_committee.py
- portfolio_manager.py

The Investment Committee runs before the Portfolio Manager so unapproved entries cannot
be opened.
