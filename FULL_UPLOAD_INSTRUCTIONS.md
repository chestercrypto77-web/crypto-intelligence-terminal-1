# V15.0.0 Complete Upload

Use the same complete-upload method as V14.

1. Extract the ZIP.
2. Upload the complete release over the crypto repository.
3. Do not delete your existing `data` folder.
4. Commit to `main`.
5. Reboot Streamlit.
6. Run **Hourly Signal Recorder** once.
7. Run **15-Minute Market Observer** once.
8. Run **5-Minute Microstructure Observer** once.
9. Run **Nightly Deep Learning Review** once.

V15 adds protected learning records. Existing runtime records are never included in the release ZIP, so the upload does not overwrite the accumulated trading/learning history.
