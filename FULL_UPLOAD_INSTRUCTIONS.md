# V8.0.0 complete upload

This is the full project release.

## Safest update method for your existing repository

1. Do **not** delete the existing `data` folder. It contains your accumulated calls.
2. Extract this ZIP.
3. GitHub → **Add file → Upload files**.
4. Drag every extracted item into the uploader.
5. Commit the replacement files.
6. Reboot Streamlit.
7. Open GitHub Actions and manually run **Hourly Signal Recorder** once.

GitHub will replace matching code files and retain your existing live JSON files because
this release contains templates rather than files with the same live names.

## Brand-new repository

Upload the whole release, then run the workflow. The recorder creates the live runtime
JSON files automatically.

## Hidden folders

If `.github` is skipped by your browser, use:

`WORKFLOW_SETUP/hourly_signal_recorder.yml`

through GitHub → Actions → set up a workflow yourself.

If `.streamlit` is skipped, the application still runs, but the preferred theme settings
will be absent.
