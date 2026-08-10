# V14.0.0 Complete Safe Upload

1. Extract the ZIP.
2. GitHub -> Add file -> Upload files.
3. Upload all extracted files over the repository.
4. Do not delete the existing data folder.
5. Commit.
6. Reboot Streamlit.
7. Check `.github/workflows`. You should see FOUR operating workflows:
   - hourly_signal_recorder.yml
   - observer_15m.yml
   - microstructure_5m.yml
   - nightly_deep_learning.yml
8. If the two new workflows are missing, open `WORKFLOW_SETUP`; exact copies are stored there so they can be manually created in `.github/workflows`.
9. Run `5-Minute Microstructure Observer` once.
10. Run `15-Minute Market Observer` once.
11. Run `Hourly Signal Recorder` once.
12. Run `Nightly Deep Learning Review` once if you want an immediate full learning refresh.

The release does not include live wallet/history JSON. Existing runtime records are preserved.
