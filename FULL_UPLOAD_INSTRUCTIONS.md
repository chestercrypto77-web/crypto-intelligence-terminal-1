# V12.0.0 Complete Safe Upload

1. Extract the ZIP.
2. GitHub → Add file → Upload files.
3. Upload every extracted item over the repository.
4. Do not delete the existing `data` folder.
5. Commit.
6. Reboot Streamlit.
7. Run Hourly Signal Recorder once.
8. Run 15-Minute Market Observer once.

New behind-the-scenes step: `learning_engine.py`
New protected record: `data/learning_state.json`
