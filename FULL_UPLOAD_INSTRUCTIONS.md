# V8.9.0 complete safe upload

1. Do not delete the existing `data` folder.
2. Extract this ZIP.
3. GitHub → Add file → Upload files.
4. Drag every extracted item into the uploader.
5. Commit.
6. Reboot Streamlit.
7. Run `Hourly Signal Recorder` once.
8. Run `15-Minute Observer` once.

The observer workflow is included in `.github/workflows/observer_15m.yml`.

If GitHub skips the hidden `.github` folder, create a new workflow and copy the visible
backup from `WORKFLOW_SETUP/observer_15m.yml`.

Release files do not contain the live runtime JSON filenames, so recorded history is
preserved.
