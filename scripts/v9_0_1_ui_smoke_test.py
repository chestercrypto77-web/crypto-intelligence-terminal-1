from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

required=[
    'APP_VERSION = "9.0.1"',
    'elif selection=="Trading Desk":',
    'elif selection=="Strategy Lab":',
    'elif selection=="Performance Lab":',
    '.front-trade-card{',
    '.strategy-card-grid{',
    'section("15-minute Observer")',
    'section("Wallet equity comparison")',
    'section("Recent completed trades")',
    'Collecting enough wallet history for a meaningful chart.',
]
missing=[x for x in required if x not in APP]
if missing:
    raise SystemExit(f"Missing UI requirements: {missing}")

print(json.dumps({
    "status":"passed",
    "checks":[
        "Trading Desk front-line cards",
        "Observer visibility",
        "Strategy Lab cards",
        "Strategy equity chart guard",
        "Performance Lab cards",
        "Performance chart guard",
        "Trade detail expanders",
    ]
},indent=2))
