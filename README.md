# Crypto Intelligence Terminal V5.3.0

Complete replacement release based on V5.1.0.

## What changed

- Existing page layout and charcoal visual structure retained
- Strong green, blue, yellow, orange and red signal language retained
- Holdings moved out of `app.py` into `holdings.json`
- Accurate quantities added from all clearly visible portfolio screenshots
- Holdings classified as Core, Secondary or Legacy
- Core holdings receive highest intelligence priority
- Secondary holdings escalate when price, momentum or volume changes materially
- Legacy positions remain lightweight unless an unusual shift occurs
- Attention Score added
- Opportunity Score added
- Possible Buy, Buy Watch, Hold/Mixed, Possible Sell Watch and Defensive/Sell Review labels added
- Portfolio concentration and top-five weight added
- Narrative exposure now reflects the expanded portfolio
- ONDO and MANTRA added, along with all clearly visible smaller holdings

## Signal reference

- Green 80–100: Possible Buy / Strong Watch
- Blue 65–79: Watching / Buy Setup Forming
- Yellow 50–64: Hold / Mixed
- Orange 35–49: Declining / Possible Sell Watch
- Red 0–34: Defensive / Sell Review

These remain research prompts, not automatic trading instructions.

## Updating a holding

Open `holdings.json`, find the asset and change only its `tokens` number.

Example:

```json
{
  "symbol": "ONDO",
  "tokens": 848.8129832
}
```

Commit the change and reboot or refresh Streamlit. No Python editing is required.

## Installation

This is a full replacement package.

1. Delete the current repository contents.
2. Extract this ZIP.
3. Upload all extracted contents to the repository root.
4. Commit the files.
5. Reboot the Streamlit app.

Expected repository contents:

- `app.py`
- `holdings.json`
- `requirements.txt`
- `README.md`
- `.streamlit/config.toml`

Do not keep an old `pages/` directory.
