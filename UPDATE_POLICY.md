# Safe update policy

## The rule from V8.1 onward

Every release is a complete project upload.

You upload all extracted files and folders over the existing repository. You do not
delete the repository first.

## What is replaced

- application code
- scripts
- configuration
- styling
- documentation
- runtime templates

## What is preserved

The following live files in `data/` are never included in release ZIPs and are therefore
not overwritten by a normal GitHub upload:

- signals_latest.json
- signal_history.json
- paper_trades.json
- external_calls.json
- external_inbox.json
- external_seen.json
- external_monitor_status.json

The workflow runs `scripts/bootstrap_runtime.py`. It creates a missing live file from its
template, but it never replaces a file that already exists.

## One final workflow setup

Install `hourly_signal_recorder.yml` once. It calls only:

`python scripts/hourly_runner.py`

Future releases can change what the runner does without requiring another workflow edit.

## Normal future update

1. Extract the complete release ZIP.
2. GitHub → Add file → Upload files.
3. Drag every extracted item into the upload area.
4. Commit.
5. Reboot Streamlit.
6. Run the hourly workflow once as a quick check.

No data copying, no selective patching, and no workflow editing should normally be needed.


V8.5 follows this policy. Upload the entire extracted release over the existing repository.
