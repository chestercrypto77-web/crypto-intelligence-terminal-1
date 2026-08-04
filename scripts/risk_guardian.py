from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import copy
import json
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

LATEST = DATA / "signals_latest.json"
HEALTH = DATA / "engine_health.json"
WALLET = DATA / "research_wallet.json"
LAB = DATA / "strategy_lab.json"
RISK = DATA / "risk_guardian.json"
HISTORY = DATA / "risk_history.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def age_minutes(value: str | None) -> float | None:
    if not value:
        return None
    try:
        timestamp = pd.Timestamp(value)
        timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        return max(0.0, (pd.Timestamp.now(tz="UTC") - timestamp).total_seconds() / 60)
    except Exception:
        return None


def asset_risk(signal: dict) -> dict:
    symbol = str(signal.get("symbol") or "").upper()
    call = str(signal.get("signal") or "HOLD").upper()
    ret4 = float(signal.get("return_4h") or 0)
    ret12 = float(signal.get("return_12h") or 0)
    ret24 = float(signal.get("return_24h") or 0)
    rvol = float(signal.get("rvol") or 0)
    rvol_delta = float(signal.get("rvol_delta") or 0)
    bullish = int(signal.get("bullish") or 0)
    bearish = int(signal.get("bearish") or 0)
    age = age_minutes(signal.get("recorded_at"))

    warnings = []
    state = "NORMAL"
    veto = False

    if age is None or age > 120:
        warnings.append("STALE DATA")
        state = "DATA UNRELIABLE"
        veto = True

    if abs(ret4) >= 8 or abs(ret12) >= 12:
        warnings.append("VOLATILITY SHOCK")
        state = "CAUTION" if state == "NORMAL" else state

    if rvol >= 3.0 and abs(ret4) >= 4:
        warnings.append("VOLUME SHOCK")
        state = "CAUTION" if state == "NORMAL" else state

    if "BUY" in call and ret4 < -3 and bearish >= bullish:
        warnings.append("BULLISH CALL UNDER PRESSURE")
        state = "CAUTION"
    if "SELL" in call and ret4 > 3 and bullish >= bearish:
        warnings.append("BEARISH CALL UNDER PRESSURE")
        state = "CAUTION"

    if "BUY" in call and ret12 < -6:
        warnings.append("LONG INVALIDATION RISK")
        state = "INVALIDATION RISK"
        veto = True
    if "SELL" in call and ret12 > 6:
        warnings.append("SHORT INVALIDATION RISK")
        state = "INVALIDATION RISK"
        veto = True

    if rvol < 0.35:
        warnings.append("LIQUIDITY / PARTICIPATION LOW")
        state = "CAUTION" if state == "NORMAL" else state

    return {
        "symbol": symbol,
        "signal": call,
        "state": state,
        "veto_new_entry": veto,
        "warnings": warnings,
        "return_4h": ret4,
        "return_12h": ret12,
        "return_24h": ret24,
        "rvol": rvol,
        "rvol_delta": rvol_delta,
        "bullish": bullish,
        "bearish": bearish,
        "age_minutes": age,
        "data_source": signal.get("data_source"),
    }


def max_drawdown_pct(history: list[dict]) -> float:
    peak = 0.0
    maximum = 0.0
    for point in history:
        value = float(point.get("equity") or 0)
        peak = max(peak, value)
        if peak > 0:
            maximum = max(maximum, (peak - value) / peak * 100)
    return maximum


def main() -> int:
    latest = read_json(LATEST, {"signals": []})
    health = read_json(HEALTH, {})
    wallet = read_json(WALLET, {})
    lab = read_json(LAB, {"strategies": {}})
    history = read_json(HISTORY, [])

    signals = latest.get("signals") or []
    asset_checks = [asset_risk(signal) for signal in signals]

    unavailable = ((health.get("market_data") or {}).get("unavailable_assets") or [])
    external_errors = ((health.get("external_intelligence") or {}).get("errors") or [])
    generated_age = age_minutes(latest.get("generated_at"))

    market_checks = {
        "signal_snapshot_age_minutes": generated_age,
        "unavailable_assets": unavailable,
        "external_source_errors": len(external_errors),
        "wallet_drawdown_pct": max_drawdown_pct(wallet.get("equity_history") or []),
        "wallet_cash": wallet.get("cash"),
        "wallet_equity": wallet.get("equity"),
        "open_positions": len(wallet.get("open_positions") or []),
    }

    portfolio_actions = []
    overall_state = "NORMAL"
    new_calls_allowed = True

    if generated_age is None or generated_age > 120:
        overall_state = "DATA UNRELIABLE"
        new_calls_allowed = False
        portfolio_actions.append("FREEZE NEW CALLS — signal snapshot is stale.")

    if len(unavailable) >= 5:
        overall_state = "DATA UNRELIABLE"
        new_calls_allowed = False
        portfolio_actions.append("FREEZE NEW CALLS — too many unavailable assets.")

    if market_checks["wallet_drawdown_pct"] >= 8:
        overall_state = "DRAWDOWN CAUTION"
        new_calls_allowed = False
        portfolio_actions.append("FREEZE NEW CALLS — research wallet drawdown exceeded 8%.")

    severe_assets = [
        item for item in asset_checks
        if item["state"] in {"INVALIDATION RISK", "DATA UNRELIABLE"}
    ]
    caution_assets = [
        item for item in asset_checks
        if item["state"] == "CAUTION"
    ]

    if severe_assets and overall_state == "NORMAL":
        overall_state = "CAUTION"
    if caution_assets and overall_state == "NORMAL":
        overall_state = "CAUTION"

    if external_errors:
        portfolio_actions.append("External-source warning — review failed feeds before relying on consensus.")

    for item in severe_assets:
        portfolio_actions.append(
            f'{item["symbol"]}: {item["state"]} — ' + ", ".join(item["warnings"])
        )

    summary = {
        "assets_checked": len(asset_checks),
        "normal_assets": sum(1 for x in asset_checks if x["state"] == "NORMAL"),
        "caution_assets": len(caution_assets),
        "severe_assets": len(severe_assets),
        "vetoed_assets": sum(1 for x in asset_checks if x["veto_new_entry"]),
        "new_calls_allowed": new_calls_allowed,
    }

    payload = {
        "generated_at": now_iso(),
        "overall_state": overall_state,
        "new_calls_allowed": new_calls_allowed,
        "portfolio_actions": portfolio_actions,
        "market_checks": market_checks,
        "asset_checks": asset_checks,
        "summary": summary,
    }

    history.append({
        "generated_at": payload["generated_at"],
        "overall_state": overall_state,
        "new_calls_allowed": new_calls_allowed,
        "summary": summary,
        "portfolio_actions": portfolio_actions,
    })

    write_json(RISK, payload)
    write_json(HISTORY, history[-20000:])

    health["risk_guardian"] = payload
    if not new_calls_allowed:
        health["overall_status"] = "PASS WITH RISK VETO"
    elif overall_state != "NORMAL" and health.get("overall_status") == "PASS":
        health["overall_status"] = "PASS WITH WARNINGS"
    write_json(HEALTH, health)

    print("\nRISK GUARDIAN")
    print(json.dumps({
        "overall_state": overall_state,
        "new_calls_allowed": new_calls_allowed,
        "assets_checked": summary["assets_checked"],
        "caution_assets": summary["caution_assets"],
        "severe_assets": summary["severe_assets"],
        "vetoed_assets": summary["vetoed_assets"],
        "actions": portfolio_actions,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
