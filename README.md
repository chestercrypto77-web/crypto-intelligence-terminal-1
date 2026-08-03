# Crypto Intelligence Terminal V8.1.0

## Safe full-update foundation

V8.1 establishes the permanent update process for future releases.

### From now on

Every release will be a complete project ZIP. Upload every extracted item over the
existing GitHub repository. Do not delete the repository first.

### Recorded data is protected

Live history files are not shipped in release ZIPs. They remain in your GitHub `data`
folder while the application code is replaced.

The new bootstrap process:

- creates a live file only when it is missing
- validates existing files
- never overwrites accumulated records

### Stable hourly workflow

The workflow now calls one stable entry point:

`python scripts/hourly_runner.py`

That runner performs runtime bootstrap, external-source monitoring and signal recording.
Future releases can update the runner and scripts without requiring repeated workflow
editing.

### Included safeguards

- Persistent-data contract
- Runtime templates
- Safe bootstrap script
- Stable hourly runner
- Release preflight validator
- Duplicate old workflow removed
- Full upload instructions

Read `UPDATE_POLICY.md` once. After the one-time workflow replacement, future updates
should be the simple drag-and-drop process you prefer.
