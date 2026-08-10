# V13.0.0 Complete Safe Upload

1. Extract the ZIP.
2. GitHub → Add file → Upload files.
3. Upload every extracted item over the repository.
4. Do not delete your existing `data` folder.
5. Commit.
6. Reboot Streamlit.
7. Run Hourly Signal Recorder once.
8. Run 15-Minute Market Observer once.

New engines:
- `market_school.py`
- `intelligence_hub.py`

New protected records:
- `data/market_school.json`
- `data/intelligence_bus.json`

The first useful Market School statistics require historical Observer records. Evidence becomes
more useful as the 15-minute history grows.
