# Crypto Intelligence Terminal V7.1.0

## Full UI update

This release keeps the hourly engine, paper-trade outcome tracking and Performance Lab,
while making the Sheldon workflow obvious and fixing the Research-page colours.

### Research colour fix

The Research page no longer relies on a standard dataframe for directional colours.
It now uses dedicated dark cards with reliable HTML styling:

- Green: positive direction / positive price-volume alignment
- Red: negative direction / selling pressure
- Blue: volume rising before price confirms
- Orange: price rising while volume fades
- Yellow: mixed or stable
- Data freshness is green, yellow or red according to age

### Paper Trading redesign

Paper Trading now has four clear tabs:

1. Our Engine Calls
2. Sheldon Calls
3. Add Sheldon / External Call
4. Signal Journal

The Sheldon section is no longer buried near the bottom of the page.

### Live data protection

The release ZIP deliberately does **not** contain the runtime JSON files inside `data/`.
Uploading this release will therefore preserve the signal history and paper trades already
being written by GitHub Actions.

### Upload

1. Extract the ZIP.
2. Drag every extracted item into GitHub **Add file → Upload files**.
3. Commit the replacements.
4. Reboot Streamlit.

Do not delete the existing `data` folder in GitHub. It contains your accumulated records.
The existing hourly GitHub Actions workflow remains active.
