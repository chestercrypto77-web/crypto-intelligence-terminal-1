# Crypto Intelligence Terminal V8.9.1

## Observer Stability Fix

This release fixes the missing 15M Observer page title and NumPy/Pandas JSON
serialisation failure discovered in the first V8.9 live workflow.

It also makes the Observer optional inside the core hourly workflow, adds Observer
startup tests, verifies Observer output JSON before committing, and includes a
repeatable release smoke-test suite.

The release tests cover page navigation, JSON serialisation, synthetic bullish and
bearish Observer data, long and short wallet mechanics, reversal exits, protected
runtime templates, compilation, safe-data preflight and ZIP integrity.

These tests validate software behaviour. Live trading performance still requires
continued paper-trading evidence.

## Upload

1. Extract the ZIP.
2. Upload all extracted files over the current repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.
6. Run 15-Minute Observer once.

Do not delete the existing data folder.
