# Crypto Intelligence Terminal V8.6.1

## Engine reliability update

This complete safe-upload release addresses the issues found during the first two
Research Desk workflow audits.

### Fixes

- Correct Yahoo symbols for POL and SUPER
- CoinGecko historical price/volume fallback using each holding's configured coin ID
- Explicit reporting of requested, analysed, fallback and unavailable assets
- Equivalent open paper trades are no longer duplicated
- Engine paper trades close when the signal reverses or returns to HOLD
- Clear counts for new trades, closed trades and duplicates prevented
- Research Wallet prints retained, closed, opened and rejected opportunities
- Wallet now targets eight positions and a 20% cash reserve for future opportunities
- Rejected opportunities are preserved for later opportunity-cost analysis
- Crypto Banter monitoring tries official YouTube RSS and then a public channel-page fallback
- New Engine Health tab inside Research Desk

### Existing wallet note

An existing wallet with ten positions will not forcibly sell two positions. It will
gradually move toward the new eight-position / 20% reserve policy as signals close.

### Upload

Use the safe full-update process:

1. Extract the ZIP.
2. Upload every extracted item over the existing GitHub repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.

Do not delete the existing data folder. The new engine-health file is created only if
missing, and all accumulated history remains protected.
