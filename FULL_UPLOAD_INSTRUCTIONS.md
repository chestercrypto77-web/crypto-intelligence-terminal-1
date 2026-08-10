# V12.2.0 Complete Safe Upload

1. Extract the ZIP.
2. GitHub → Add file → Upload files.
3. Upload every extracted item over the repository.
4. Do not delete the existing `data` folder.
5. Commit.
6. Reboot Streamlit.
7. Run Hourly Signal Recorder once.
8. Run 15-Minute Market Observer once.

New hourly steps:
- `trade_diagnostics.py`
- `challenger_arena.py`

New protected records:
- `data/trade_diagnostics.json`
- `data/challenger_arena.json`

Performance Lab will show the diagnosis inside each trade replay and a compact Challenger
Arena table at the bottom.
