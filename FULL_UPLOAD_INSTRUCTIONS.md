# V8.9.1 complete safe upload

1. Keep the existing GitHub data folder.
2. Extract this ZIP.
3. GitHub → Add file → Upload files.
4. Drag every extracted item into the uploader.
5. Commit the replacements.
6. Reboot Streamlit.
7. Run Hourly Signal Recorder once.
8. Run 15-Minute Observer once.

The Observer workflow is included in `.github/workflows/observer_15m.yml`.
A visible backup is at `WORKFLOW_SETUP/observer_15m.yml`.
