from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/"app.py").read_text(encoding="utf-8")

assert 'APP_VERSION = "13.0.0"' in app

m=re.search(r'st\.sidebar\.radio\("Navigation",\[(.*?)\],label_visibility="collapsed"\)',app,re.S)
assert m, "Navigation missing"
nav=m.group(1)

assert '"Portfolio"' in nav
assert '"Intelligence"' not in nav
assert '"Performance Lab"' in nav
assert '"Watch"' in nav

# The intelligence implementation may remain dormant for code safety,
# but it must not be reachable from the normal user navigation.
print(json.dumps({
  "status":"passed",
  "tests":[
    "Portfolio visible",
    "Intelligence removed from navigation",
    "Performance Lab retained",
    "Watch retained",
    "V11.1.3"
  ]
},indent=2))
