from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")

assert 'APP_VERSION = "11.1.3"' in app

# Performance Lab
assert 'TRADE_REVIEWS_FILE = Path(__file__).with_name("data") / "trade_reviews.json"' in app
start=app.index('elif selection=="Performance Lab":')
end=app.index('elif selection=="Settings":',start)
section=app[start:end]
load='trade_reviews=read_runtime_json(TRADE_REVIEWS_FILE,{"reviews":[],"summary":{}})'
use='trade_reviews.get("reviews")'
assert load in section
assert use in section
assert section.index(load) < section.index(use)

# Portfolio must be user reachable, not just dead code.
nav_start=app.index('st.sidebar.radio("Navigation"')
nav_end=app.index('label_visibility="collapsed")',nav_start)
nav=app[nav_start:nav_end]
assert '"Portfolio"' in nav
assert 'elif selection=="Portfolio":' in app

print(json.dumps({
  "status":"passed",
  "tests":[
    "TRADE_REVIEWS_FILE declared",
    "trade_reviews loaded before use",
    "Portfolio restored to navigation",
    "Portfolio page branch remains intact"
  ]
},indent=2))
