from pathlib import Path
import re, json
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")
start=app.index('elif selection=="Performance Lab":')
end=app.index('elif selection=="Settings":',start)
section=app[start:end]
load_match=re.search(r'trade_reviews\s*=\s*read_runtime_json\(TRADE_REVIEWS_FILE,\{"reviews":\[\],"summary":\{\}\}\)',section)
use_match=re.search(r'trade_reviews\.get\("reviews"\)',section)
assert load_match, "Performance Lab does not load trade_reviews"
assert use_match, "Performance Lab does not use trade_reviews"
assert load_match.start() < use_match.start(), "trade_reviews is used before it is loaded"
assert 'APP_VERSION = "11.1.1"' in app
print(json.dumps({"status":"passed","tests":["trade_reviews loaded","load occurs before use","version 11.1.1"]},indent=2))
