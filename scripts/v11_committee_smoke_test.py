from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("committee", ROOT / "scripts" / "investment_committee.py")
committee = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(committee)


def base_signal(symbol="TEST", signal="STRONG BUY", r4=3.0, r12=4.0, r24=6.0, rvol=2.0, delta=0.5, bull=10, bear=1):
    return {
        "symbol": symbol,
        "name": symbol,
        "narrative": "Test",
        "signal": signal,
        "entry_price": 100.0,
        "return_4h": r4,
        "return_12h": r12,
        "return_24h": r24,
        "rvol": rvol,
        "rvol_delta": delta,
        "bullish": bull,
        "bearish": bear,
    }


def build_reports(item, regime, risk_state="NORMAL"):
    return {
        "technical": committee.technical_analyst(item),
        "volume_liquidity": committee.volume_liquidity_analyst(item),
        "momentum": committee.momentum_analyst(item),
        "news_fundamental": committee.vote("LONG", 2, ["Positive verified catalyst"]),
        "macro_regime": committee.macro_regime_analyst(item, regime),
        "risk_manager": committee.vote("VETO", 3, ["Risk veto"]) if risk_state == "VETO" else committee.vote("APPROVE", 2, ["Risk normal"]),
        "portfolio_fit": committee.vote("APPROVE", 1, ["Portfolio fit normal"]),
    }


def test_aligned_long():
    item = base_signal()
    regime = {"state": "RISK ON"}
    result = committee.aggregate_committee(item, build_reports(item, regime), regime)
    assert result["action"] == "BUY"
    assert result["direction"] == "LONG"
    assert result["book_permissions"]["CORE"] is True
    assert result["book_permissions"]["SWING"] is True


def test_risk_veto():
    item = base_signal()
    regime = {"state": "RISK ON"}
    result = committee.aggregate_committee(item, build_reports(item, regime, "VETO"), regime)
    assert result["action"] == "NO TRADE"
    assert not any(result["book_permissions"].values())


def test_conflict_wait():
    item = base_signal(signal="HOLD", r4=1.0, r12=-2.0, r24=-1.0, rvol=0.8, delta=-0.2, bull=5, bear=5)
    regime = {"state": "MIXED"}
    reports = {
        "technical": committee.vote("NEUTRAL", 2, ["Mixed"]),
        "volume_liquidity": committee.vote("NEUTRAL", 2, ["Weak"]),
        "momentum": committee.vote("NEUTRAL", 2, ["Mixed"]),
        "news_fundamental": committee.vote("LONG", 1, ["Minor positive"]),
        "macro_regime": committee.vote("SHORT", 1, ["Minor negative"]),
        "risk_manager": committee.vote("APPROVE", 2, ["Normal"]),
        "portfolio_fit": committee.vote("APPROVE", 1, ["Normal"]),
    }
    result = committee.aggregate_committee(item, reports, regime)
    assert result["action"] in {"WATCH", "NO TRADE"}
    assert result["book_permissions"]["CORE"] is False
    assert result["book_permissions"]["SWING"] is False


def test_short_swing():
    item = base_signal(signal="STRONG SELL", r4=-3.0, r12=-5.0, r24=-7.0, rvol=2.2, delta=0.6, bull=1, bear=10)
    regime = {"state": "RISK OFF"}
    reports = build_reports(item, regime)
    reports["news_fundamental"] = committee.vote("SHORT", 2, ["Negative catalyst"])
    result = committee.aggregate_committee(item, reports, regime)
    assert result["action"] == "SHORT"
    assert result["book_permissions"]["CORE"] is False
    assert result["book_permissions"]["SWING"] is True


def test_market_regime():
    signals = [
        base_signal("BTC", "STRONG BUY", 2, 3, 4, 1.5, .2, 9, 1),
        base_signal("ETH", "BUY", 1.5, 2, 3, 1.3, .2, 8, 2),
        base_signal("A", "BUY", 2, 2, 2, 1.2, .1, 8, 2),
        base_signal("B", "BUY", 2, 2, 2, 1.2, .1, 8, 2),
    ]
    regime = committee.market_regime(signals)
    assert regime["state"] == "RISK ON"


def test_json_write():
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "committee.json"
        committee.write_json(path, {"ok": True})
        assert json.loads(path.read_text())["ok"] is True


def main():
    test_aligned_long()
    test_risk_veto()
    test_conflict_wait()
    test_short_swing()
    test_market_regime()
    test_json_write()
    print(json.dumps({
        "status": "passed",
        "tests": [
            "aligned multi-analyst Long approval",
            "Risk Manager veto",
            "conflicted committee waits",
            "Short Swing approval",
            "broad market regime",
            "safe JSON persistence",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
