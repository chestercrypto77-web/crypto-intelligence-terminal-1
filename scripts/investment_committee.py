from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import copy
import json
import math
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

LATEST = DATA / "signals_latest.json"
RISK = DATA / "risk_guardian.json"
EXTERNAL_INBOX = DATA / "external_inbox.json"
EXTERNAL_CALLS = DATA / "external_calls.json"
CORE_WALLET = DATA / "core_wallet.json"
SWING_WALLET = DATA / "swing_wallet.json"
SCALP_WALLET = DATA / "scalp_wallet.json"
COMMITTEE_LATEST = DATA / "committee_latest.json"
COMMITTEE_HISTORY = DATA / "committee_history.json"
COMMITTEE_LEARNING = DATA / "committee_learning.json"
HEALTH = DATA / "engine_health.json"
OBSERVER = DATA / "observer_latest.json"
MARKET_SCHOOL = DATA / "market_school.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(path)


def number(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except Exception:
        return default


def vote(direction: str, strength: int, reasons: list[str], evidence: dict | None = None) -> dict:
    return {
        "direction": direction,
        "strength": max(0, min(3, int(strength))),
        "reasons": reasons,
        "evidence": evidence or {},
    }


def text_blob(item: dict) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("title", "summary", "content", "notes", "source_name", "source_id")
    ).lower()


def market_regime(signals: list[dict]) -> dict:
    by_symbol = {str(item.get("symbol") or "").upper(): item for item in signals}
    btc = by_symbol.get("BTC", {})
    eth = by_symbol.get("ETH", {})
    bullish = sum(1 for item in signals if "BUY" in str(item.get("signal") or "").upper())
    bearish = sum(1 for item in signals if "SELL" in str(item.get("signal") or "").upper())
    total = max(1, len(signals))
    breadth = (bullish - bearish) / total

    btc_4h = number(btc.get("return_4h"))
    btc_24h = number(btc.get("return_24h"))
    eth_4h = number(eth.get("return_4h"))
    risk_on_points = 0
    risk_off_points = 0

    if btc_4h > 0.5:
        risk_on_points += 1
    elif btc_4h < -0.5:
        risk_off_points += 1
    if btc_24h > 1.0:
        risk_on_points += 1
    elif btc_24h < -1.0:
        risk_off_points += 1
    if eth_4h > 0.5:
        risk_on_points += 1
    elif eth_4h < -0.5:
        risk_off_points += 1
    if breadth > 0.15:
        risk_on_points += 2
    elif breadth < -0.15:
        risk_off_points += 2

    if risk_on_points >= risk_off_points + 2:
        state = "RISK ON"
    elif risk_off_points >= risk_on_points + 2:
        state = "RISK OFF"
    else:
        state = "MIXED"

    return {
        "state": state,
        "btc_4h": btc_4h,
        "btc_24h": btc_24h,
        "eth_4h": eth_4h,
        "bullish_breadth": bullish / total * 100,
        "bearish_breadth": bearish / total * 100,
        "risk_on_points": risk_on_points,
        "risk_off_points": risk_off_points,
    }


def technical_analyst(item: dict) -> dict:
    signal = str(item.get("signal") or "HOLD").upper()
    r4 = number(item.get("return_4h"))
    r12 = number(item.get("return_12h"))
    r24 = number(item.get("return_24h"))
    bullish = number(item.get("bullish"))
    bearish = number(item.get("bearish"))
    spread = bullish - bearish

    long_reasons = []
    short_reasons = []
    if signal in {"BUY", "STRONG BUY"}:
        long_reasons.append(f"Hourly signal is {signal}")
    if signal in {"SELL", "STRONG SELL"}:
        short_reasons.append(f"Hourly signal is {signal}")
    if spread >= 5:
        long_reasons.append("Bullish conditions materially exceed bearish conditions")
    if spread <= -5:
        short_reasons.append("Bearish conditions materially exceed bullish conditions")
    if r4 > 0 and r12 > 0:
        long_reasons.append("Positive 4H and 12H structure")
    if r4 < 0 and r12 < 0:
        short_reasons.append("Negative 4H and 12H structure")
    if r24 > 12:
        long_reasons.append("Move is extended; entry timing risk elevated")
    if r24 < -12:
        short_reasons.append("Move is extended; short timing risk elevated")

    if len(long_reasons) >= 2 and len(short_reasons) == 0:
        return vote("LONG", min(3, len(long_reasons)), long_reasons, {"spread": spread, "r4": r4, "r12": r12, "r24": r24})
    if len(short_reasons) >= 2 and len(long_reasons) == 0:
        return vote("SHORT", min(3, len(short_reasons)), short_reasons, {"spread": spread, "r4": r4, "r12": r12, "r24": r24})
    return vote("NEUTRAL", 1, long_reasons + short_reasons or ["Technical structure is not decisive"], {"spread": spread, "r4": r4, "r12": r12, "r24": r24})


def volume_liquidity_analyst(item: dict) -> dict:
    rvol = number(item.get("rvol"))
    delta = number(item.get("rvol_delta"))
    r4 = number(item.get("return_4h"))
    reasons = []
    if rvol >= 1.5 and delta > 0.10:
        direction = "LONG" if r4 > 0 else "SHORT" if r4 < 0 else "NEUTRAL"
        reasons.append("Relative volume is high and accelerating")
        if direction != "NEUTRAL":
            reasons.append("Participation agrees with 4H price direction")
        return vote(direction, 3 if rvol >= 2 else 2, reasons, {"rvol": rvol, "rvol_delta": delta})
    if rvol >= 1.15:
        direction = "LONG" if r4 > 0 else "SHORT" if r4 < 0 else "NEUTRAL"
        reasons.append("Participation is above normal")
        if delta <= 0:
            reasons.append("Volume acceleration is not confirmed")
        return vote(direction, 1, reasons, {"rvol": rvol, "rvol_delta": delta})
    if rvol < 0.75:
        return vote("NEUTRAL", 2, ["Participation is too weak for a high-quality entry"], {"rvol": rvol, "rvol_delta": delta})
    return vote("NEUTRAL", 1, ["Volume is ordinary"], {"rvol": rvol, "rvol_delta": delta})


def momentum_analyst(item: dict) -> dict:
    r4 = number(item.get("return_4h"))
    r12 = number(item.get("return_12h"))
    r24 = number(item.get("return_24h"))
    acceleration = r4 - (r12 / 3 if r12 else 0)
    reasons = []
    if r4 > 0.8 and r12 > 0 and acceleration > 0:
        reasons.append("Positive momentum is accelerating")
        if r24 > 15:
            reasons.append("Momentum is extended and may require profit protection")
            return vote("LONG", 1, reasons, {"acceleration": acceleration})
        return vote("LONG", 2, reasons, {"acceleration": acceleration})
    if r4 < -0.8 and r12 < 0 and acceleration < 0:
        reasons.append("Negative momentum is accelerating")
        if r24 < -15:
            reasons.append("Downside is extended and short chasing risk is elevated")
            return vote("SHORT", 1, reasons, {"acceleration": acceleration})
        return vote("SHORT", 2, reasons, {"acceleration": acceleration})
    if r4 * r12 < 0:
        return vote("NEUTRAL", 2, ["4H and 12H momentum disagree"], {"acceleration": acceleration})
    return vote("NEUTRAL", 1, ["Momentum is not accelerating clearly"], {"acceleration": acceleration})


def market_memory_analyst(item: dict, observer_item: dict, school: dict) -> dict:
    """Independent historical analogue analyst.

    It only votes when the current pattern has repeated prior examples. It never sees
    future information from the current setup.
    """
    if not observer_item:
        return vote("NEUTRAL", 0, ["No 15M pattern snapshot is available"], {})
    signal=str(observer_item.get("signal") or "NEUTRAL").upper().replace(" ","_")
    rvol=number(observer_item.get("rvol"))
    rvb="RVOL_2PLUS" if rvol>=2 else "RVOL_1_5_2" if rvol>=1.5 else "RVOL_1_15_1_5" if rvol>=1.15 else "RVOL_WEAK" if rvol<0.75 else "RVOL_NORMAL"
    rsi=number(observer_item.get("rsi"),50)
    rsib="RSI_OVERBOUGHT" if rsi>=75 else "RSI_BULL" if rsi>=60 else "RSI_OVERSOLD" if rsi<=25 else "RSI_BEAR" if rsi<=40 else "RSI_MID"
    mh=number(observer_item.get("macd_histogram")); md=number(observer_item.get("macd_delta"))
    macd="MACD_UP" if mh>0 and md>=0 else "MACD_DOWN" if mh<0 and md<=0 else "MACD_MIXED"
    structure="BREAKOUT" if observer_item.get("breakout") else "BREAKDOWN" if observer_item.get("breakdown") else "RANGE"
    bull=number(observer_item.get("bullish_conditions")); bear=number(observer_item.get("bearish_conditions"))
    align="BULLISH" if bull-bear>=5 else "BEARISH" if bear-bull>=5 else "MIXED"
    key="|".join([signal,rvb,rsib,macd,structure,align])
    symbol=str(item.get("symbol") or "").upper()
    stats=((school.get("asset_patterns") or {}).get(symbol) or {}).get(key)
    source="asset"
    if not stats:
        stats=(school.get("global_patterns") or {}).get(key)
        source="global"
    p4=(stats or {}).get("4h") or {}
    samples=int(p4.get("samples") or 0)
    avg=number(p4.get("avg_return_pct")); up=number(p4.get("up_rate_pct")); down=number(p4.get("down_rate_pct"))
    evidence={"pattern":key,"source":source,"samples":samples,"avg_4h":avg,"up_rate":up,"down_rate":down}
    if samples<10:
        return vote("NEUTRAL",0,[f"Only {samples} historical pattern match(es); not enough evidence"],evidence)
    if samples>=20 and up>=65 and avg>0.5:
        return vote("LONG",2,[f"{samples} prior matches favour upside",f"Historical 4H average {avg:+.2f}%"],evidence)
    if samples>=20 and down>=65 and avg<-0.5:
        return vote("SHORT",2,[f"{samples} prior matches favour downside",f"Historical 4H average {avg:+.2f}%"],evidence)
    if up>=60 and avg>0:
        return vote("LONG",1,[f"Developing historical edge across {samples} matches"],evidence)
    if down>=60 and avg<0:
        return vote("SHORT",1,[f"Developing historical downside edge across {samples} matches"],evidence)
    return vote("NEUTRAL",1,[f"{samples} prior matches are not directionally decisive"],evidence)


def news_fundamental_analyst(item: dict, inbox: list[dict], calls: list[dict]) -> dict:
    symbol = str(item.get("symbol") or "").upper()
    name = str(item.get("name") or "").lower()
    tokens = {symbol.lower()}
    if name and len(name) >= 3:
        tokens.add(name)

    matches = []
    for row in inbox[-500:]:
        blob = text_blob(row)
        if any(re.search(rf"\b{re.escape(token)}\b", blob) for token in tokens):
            matches.append(row)

    active_calls = [
        row for row in calls
        if str(row.get("symbol") or "").upper() == symbol
        and str(row.get("status") or "ACTIVE").upper() == "ACTIVE"
    ]

    positive_words = ("launch", "partnership", "upgrade", "adoption", "approval", "integration", "growth", "listing")
    negative_words = ("exploit", "hack", "delay", "lawsuit", "delist", "unlock", "outage", "investigation")
    positive = 0
    negative = 0
    for row in matches:
        blob = text_blob(row)
        positive += sum(1 for word in positive_words if word in blob)
        negative += sum(1 for word in negative_words if word in blob)

    for row in active_calls:
        call = str(row.get("call") or row.get("direction") or "").upper()
        if "BUY" in call or "LONG" in call:
            positive += 1
        elif "SELL" in call or "SHORT" in call:
            negative += 1

    reasons = [f"{len(matches)} recent matched research item(s)", f"{len(active_calls)} active reviewed external call(s)"]
    if positive >= negative + 2:
        reasons.append("Matched developments lean positive")
        return vote("LONG", min(2, positive - negative), reasons, {"positive_mentions": positive, "negative_mentions": negative})
    if negative >= positive + 2:
        reasons.append("Matched developments lean negative")
        return vote("SHORT", min(2, negative - positive), reasons, {"positive_mentions": positive, "negative_mentions": negative})
    reasons.append("No decisive verified catalyst alignment")
    return vote("NEUTRAL", 1, reasons, {"positive_mentions": positive, "negative_mentions": negative})


def macro_regime_analyst(item: dict, regime: dict) -> dict:
    symbol = str(item.get("symbol") or "").upper()
    r4 = number(item.get("return_4h"))
    state = regime.get("state", "MIXED")
    reasons = [f"Broad market regime is {state}"]
    if symbol == "BTC":
        return vote("LONG" if r4 > 0 else "SHORT" if r4 < 0 else "NEUTRAL", 2, reasons + ["BTC defines much of the crypto risk regime"])
    if state == "RISK ON" and r4 > 0:
        return vote("LONG", 2, reasons + ["Asset direction agrees with broad risk appetite"])
    if state == "RISK OFF" and r4 < 0:
        return vote("SHORT", 2, reasons + ["Asset direction agrees with broad risk reduction"])
    if state == "MIXED":
        return vote("NEUTRAL", 1, reasons + ["Broad context offers little assistance"])
    return vote("NEUTRAL", 2, reasons + ["Asset direction conflicts with broad market regime"])


def risk_manager(item: dict, risk_map: dict[str, dict], wallets: list[dict]) -> dict:
    symbol = str(item.get("symbol") or "").upper()
    risk = risk_map.get(symbol) or {}
    state = str(risk.get("state") or "NORMAL").upper()
    exposure = 0.0
    open_books = []
    for wallet in wallets:
        for position in wallet.get("open_positions") or []:
            if str(position.get("symbol") or "").upper() == symbol:
                exposure += number(position.get("allocated_cash"))
                open_books.append(str(position.get("book") or wallet.get("name") or "WALLET"))

    reasons = [f"Risk Guardian state is {state}"]
    if open_books:
        reasons.append(f"Existing exposure in {', '.join(open_books)}")
    if state in {"INVALIDATION RISK", "DATA UNRELIABLE", "SEVERE"}:
        return vote("VETO", 3, reasons, {"existing_exposure": exposure, "risk_state": state})
    if state == "CAUTION":
        return vote("CAUTION", 2, reasons, {"existing_exposure": exposure, "risk_state": state})
    return vote("APPROVE", 2, reasons, {"existing_exposure": exposure, "risk_state": state})


def portfolio_fit_analyst(item: dict, wallets: list[dict]) -> dict:
    symbol = str(item.get("symbol") or "").upper()
    narrative = str(item.get("narrative") or "Unknown")
    current_positions = []
    same_narrative = 0
    for wallet in wallets:
        for position in wallet.get("open_positions") or []:
            current_positions.append(position)
            if str(position.get("narrative") or "") == narrative:
                same_narrative += 1

    existing = [p for p in current_positions if str(p.get("symbol") or "").upper() == symbol]
    reasons = []
    if existing:
        reasons.append("Asset is already held in another active book")
    if same_narrative >= 3:
        reasons.append("Narrative concentration is elevated")
    if existing or same_narrative >= 3:
        return vote("CAUTION", 2, reasons, {"same_narrative_positions": same_narrative})
    return vote("APPROVE", 1, ["No obvious portfolio concentration conflict"], {"same_narrative_positions": same_narrative})


def aggregate_committee(item: dict, reports: dict, regime: dict) -> dict:
    risk = reports["risk_manager"]["direction"]
    fit = reports["portfolio_fit"]["direction"]
    if risk == "VETO":
        return {
            "action": "NO TRADE",
            "direction": "NEUTRAL",
            "quality": "REJECTED",
            "book_permissions": {"CORE": False, "SWING": False, "SCALP": False},
            "reasons": ["Risk Manager vetoed the setup"],
            "agreement": {},
        }

    long_votes = 0
    short_votes = 0
    neutral_votes = 0
    independent_long = []
    independent_short = []
    for name in ("technical", "volume_liquidity", "momentum", "market_memory", "news_fundamental", "macro_regime"):
        report = reports.get(name) or vote("NEUTRAL", 0, [f"{name} report unavailable"], {})
        strength = int(report.get("strength") or 0)
        direction = report.get("direction")
        if direction == "LONG":
            long_votes += strength
            independent_long.append(name)
        elif direction == "SHORT":
            short_votes += strength
            independent_short.append(name)
        else:
            neutral_votes += strength

    direction = "LONG" if long_votes > short_votes else "SHORT" if short_votes > long_votes else "NEUTRAL"
    winning_votes = max(long_votes, short_votes)
    losing_votes = min(long_votes, short_votes)
    independent_count = len(independent_long if direction == "LONG" else independent_short)

    conflicts = []
    if long_votes and short_votes:
        conflicts.append("Committee contains directional disagreement")
    if fit == "CAUTION":
        conflicts.append("Portfolio Fit requests reduced or no additional exposure")
    if risk == "CAUTION":
        conflicts.append("Risk Manager requests caution")

    decisive = direction != "NEUTRAL" and winning_votes >= 6 and winning_votes >= losing_votes + 3 and independent_count >= 3
    high_quality = decisive and winning_votes >= 8 and independent_count >= 4 and not conflicts
    core_allowed = direction == "LONG" and high_quality and regime.get("state") != "RISK OFF"
    swing_allowed = decisive and risk != "VETO" and fit != "CAUTION"
    scalp_allowed = decisive and reports["volume_liquidity"]["strength"] >= 2 and reports["momentum"]["strength"] >= 2

    if high_quality:
        quality = "HIGH QUALITY"
    elif decisive:
        quality = "QUALIFIED"
    elif direction != "NEUTRAL":
        quality = "BUILDING"
    else:
        quality = "NO EDGE"

    if decisive:
        action = "BUY" if direction == "LONG" else "SHORT"
    else:
        action = "WATCH" if direction != "NEUTRAL" else "NO TRADE"

    reasons = [
        f"Long votes {long_votes}; Short votes {short_votes}; Neutral weight {neutral_votes}",
        f"{independent_count} independent analyst groups support {direction}",
    ] + conflicts

    return {
        "action": action,
        "direction": direction,
        "quality": quality,
        "book_permissions": {
            "CORE": core_allowed,
            "SWING": swing_allowed,
            "SCALP": scalp_allowed,
        },
        "reasons": reasons,
        "agreement": {
            "long_votes": long_votes,
            "short_votes": short_votes,
            "neutral_weight": neutral_votes,
            "independent_support": independent_count,
            "conflicts": conflicts,
        },
    }


def build_learning(core: dict, swing: dict, scalp: dict, history: list[dict]) -> dict:
    reviewed = []
    for book, wallet in (("CORE", core), ("SWING", swing), ("SCALP", scalp)):
        for position in wallet.get("closed_positions") or []:
            committee = position.get("committee_snapshot") or {}
            if committee:
                reviewed.append((book, position, committee))

    conditions: dict[str, dict] = {}
    books: dict[str, dict] = {}
    for book, position, snapshot in reviewed:
        pnl = number(position.get("realised_pnl"))
        ret = number(position.get("realised_return"))
        b = books.setdefault(book, {"trades": 0, "wins": 0, "net_pnl": 0.0, "returns": []})
        b["trades"] += 1
        b["wins"] += 1 if pnl > 0 else 0
        b["net_pnl"] += pnl
        b["returns"].append(ret)

        for analyst, report in (snapshot.get("reports") or {}).items():
            key = f"{analyst}:{report.get('direction')}:{report.get('strength')}"
            c = conditions.setdefault(key, {"trades": 0, "wins": 0, "net_pnl": 0.0, "returns": []})
            c["trades"] += 1
            c["wins"] += 1 if pnl > 0 else 0
            c["net_pnl"] += pnl
            c["returns"].append(ret)

    for group in (conditions, books):
        for row in group.values():
            row["win_rate"] = row["wins"] / row["trades"] * 100 if row["trades"] else 0.0
            row["expectancy_pct"] = sum(row["returns"]) / row["trades"] if row["trades"] else 0.0
            row.pop("returns", None)

    return {
        "updated_at": now_iso(),
        "closed_trades_reviewed": len(reviewed),
        "conditions": conditions,
        "book_results": books,
        "notes": [
            "Committee weights are not changed automatically.",
            "A condition should have a meaningful sample and positive net expectancy before becoming a candidate rule.",
        ],
    }


def main() -> int:
    latest = read_json(LATEST, {"signals": []})
    signals = latest.get("signals") or []
    risk_payload = read_json(RISK, {"asset_checks": []})
    risk_map = {
        str(item.get("symbol") or "").upper(): item
        for item in risk_payload.get("asset_checks") or []
    }
    inbox = read_json(EXTERNAL_INBOX, [])
    calls = read_json(EXTERNAL_CALLS, [])
    observer_payload = read_json(OBSERVER, {"signals":[]})
    observer_map = {str(x.get("symbol") or "").upper():x for x in observer_payload.get("signals") or []}
    market_school = read_json(MARKET_SCHOOL, {})
    core = read_json(CORE_WALLET, {})
    swing = read_json(SWING_WALLET, {})
    scalp = read_json(SCALP_WALLET, {})
    wallets = [core, swing, scalp]
    history = read_json(COMMITTEE_HISTORY, [])

    regime = market_regime(signals)
    timestamp = now_iso()
    assets = []
    for item in signals:
        reports = {
            "technical": technical_analyst(item),
            "volume_liquidity": volume_liquidity_analyst(item),
            "momentum": momentum_analyst(item),
            "market_memory": market_memory_analyst(item, observer_map.get(str(item.get("symbol") or "").upper(),{}), market_school),
            "news_fundamental": news_fundamental_analyst(item, inbox, calls),
            "macro_regime": macro_regime_analyst(item, regime),
            "risk_manager": risk_manager(item, risk_map, wallets),
            "portfolio_fit": portfolio_fit_analyst(item, wallets),
        }
        decision = aggregate_committee(item, reports, regime)
        record = {
            "recorded_at": timestamp,
            "symbol": str(item.get("symbol") or "").upper(),
            "name": item.get("name"),
            "narrative": item.get("narrative"),
            "price": item.get("entry_price"),
            "signal": item.get("signal"),
            "reports": reports,
            "decision": decision,
        }
        assets.append(record)

    payload = {
        "generated_at": timestamp,
        "objective": "Allocate capital only when independent evidence aligns and expected value justifies risk.",
        "market_regime": regime,
        "assets": assets,
        "health": {
            "assets_checked": len(assets),
            "qualified_core": sum(1 for row in assets if row["decision"]["book_permissions"]["CORE"]),
            "qualified_swing": sum(1 for row in assets if row["decision"]["book_permissions"]["SWING"]),
            "qualified_scalp": sum(1 for row in assets if row["decision"]["book_permissions"]["SCALP"]),
            "no_trade": sum(1 for row in assets if row["decision"]["action"] == "NO TRADE"),
            "watch": sum(1 for row in assets if row["decision"]["action"] == "WATCH"),
        },
    }

    history.extend(assets)
    history = history[-100000:]
    learning = build_learning(core, swing, scalp, history)

    write_json(COMMITTEE_LATEST, payload)
    write_json(COMMITTEE_HISTORY, history)
    write_json(COMMITTEE_LEARNING, learning)

    health = read_json(HEALTH, {})
    health["investment_committee"] = {
        "updated_at": timestamp,
        **payload["health"],
        "market_regime": regime.get("state"),
        "closed_trades_reviewed": learning.get("closed_trades_reviewed"),
    }
    write_json(HEALTH, health)

    print(json.dumps({
        "investment_committee": payload["health"],
        "market_regime": regime,
        "learning": {
            "closed_trades_reviewed": learning.get("closed_trades_reviewed"),
            "conditions_tracked": len(learning.get("conditions") or {}),
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
