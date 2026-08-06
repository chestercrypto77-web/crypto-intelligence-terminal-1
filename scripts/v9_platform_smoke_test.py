from __future__ import annotations
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

EXPECTED=["Today","Markets","Watch","Trading Desk","Intelligence","Strategy Lab","Performance Lab","Settings"]

def check_navigation():
    match=re.search(r'st\.sidebar\.radio\("Navigation",\[(.*?)\],label_visibility="collapsed"\)',APP,re.S)
    assert match, "Navigation not found"
    entries=re.findall(r'"([^"]+)"',match.group(1))
    assert entries==EXPECTED, (entries,EXPECTED)
    title_block=APP[APP.index("titles = {"):APP.index("page_header(*titles[selection])")]
    for entry in EXPECTED:
        assert f'"{entry}":' in title_block, f"Missing title {entry}"
    handlers={"Today"}
    handlers.update(re.findall(r'(?:if|elif) selection=="([^"]+)"',APP))
    for entry in EXPECTED:
        assert entry in handlers, f"Missing handler {entry}"

def check_removed_navigation():
    for legacy in ["Paper Trading","Research Desk","Risk Guardian","External Intelligence","15M Observer","Research","Signal Lab"]:
        nav=APP[APP.index('selection = st.sidebar.radio'):APP.index('titles = {')]
        assert f'"{legacy}"' not in nav, f"Legacy page remains in nav: {legacy}"

def check_cards():
    for token in [".asset-front-card{",".trade-wallet-grid{",'elif selection=="Trading Desk":','elif selection=="Intelligence":','elif selection=="Settings":']:
        assert token in APP, token

def check_persistent_templates():
    contract=json.loads((ROOT/"config"/"persistent_data.json").read_text(encoding="utf-8"))
    for filename in contract["files"]:
        template=ROOT/"data"/"templates"/filename.replace(".json",".template.json")
        assert template.exists(), filename
        json.loads(template.read_text(encoding="utf-8"))

def main():
    check_navigation(); check_removed_navigation(); check_cards(); check_persistent_templates()
    print(json.dumps({"status":"passed","navigation":EXPECTED,"checks":["navigation","legacy page removal","card UI","persistent templates"]},indent=2))

if __name__=="__main__":
    main()
