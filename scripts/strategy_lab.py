from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import copy
import json
import math
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LATEST = DATA / "signals_latest.json"
REGISTRY = DATA / "strategy_registry.json"
LAB = DATA / "strategy_lab.json"
HEALTH = DATA / "engine_health.json"

DEFAULT_ASSUMPTIONS = {
    "position_size_pct": 10.0,
    "max_positions": 8,
    "minimum_cash_reserve_pct": 20.0,
    "fee_pct_per_side": 0.10,
    "slippage_pct_per_side": 0.05,
}


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


def side_from_signal(signal: str) -> str | None:
    signal = str(signal or "").upper()
    if signal in {"BUY", "STRONG BUY"}:
        return "LONG"
    if signal in {"SELL", "STRONG SELL"}:
        return "SHORT"
    return None


def directional_return(direction: str, entry: float, current: float) -> float:
    raw = (current / entry - 1.0) * 100
    return raw if direction == "LONG" else -raw


def round_trip_cost(assumptions: dict) -> float:
    return 2 * (
        float(assumptions.get("fee_pct_per_side", 0.10))
        + float(assumptions.get("slippage_pct_per_side", 0.05))
    )


def candle_closed(signal: dict) -> bool:
    try:
        candle_start = pd.Timestamp(signal.get("candle_time"))
        candle_start = (
            candle_start.tz_localize("UTC")
            if candle_start.tzinfo is None
            else candle_start.tz_convert("UTC")
        )
        return pd.Timestamp.now(tz="UTC") >= candle_start + pd.Timedelta(hours=4)
    except Exception:
        return False


def entry_call(strategy: dict, signal: dict, btc_signal: dict | None) -> str:
    """Apply challenger rules only to new entries."""
    base = str(signal.get("signal") or "HOLD").upper()
    rules = strategy.get("rules") or {}

    if strategy.get("role") == "CHAMPION":
        return base

    if rules.get("require_closed_candle") and not candle_closed(signal):
        return "HOLD"

    if rules.get("minimum_rvol_for_buy") is not None:
        minimum = float(rules["minimum_rvol_for_buy"])
        if "BUY" in base and float(signal.get("rvol") or 0) < minimum:
            return "HOLD"

    if rules.get("require_btc_confirmation"):
        btc_base = str((btc_signal or {}).get("signal") or "HOLD").upper()
        if "BUY" in base and "BUY" not in btc_base:
            return "HOLD"
        if "SELL" in base and "SELL" not in btc_base:
            return "HOLD"

    return base


def exit_decision(position: dict, live_signal: dict | None) -> tuple[bool, str]:
    """Exit only on base-engine reversal or HOLD, not when an entry filter stops passing."""
    if not live_signal:
        return False, ""
    base = str(live_signal.get("signal") or "HOLD").upper()
    side = side_from_signal(base)
    reverse = side is not None and side != position.get("direction")
    neutral = base == "HOLD"
    if reverse:
        return True, "Base signal reversal"
    if neutral:
        return True, "Base signal returned to HOLD"
    return False, ""


def empty_wallet(strategy: dict, starting_capital: float, assumptions: dict) -> dict:
    return {
        "strategy_id": strategy["strategy_id"],
        "name": strategy.get("name", strategy["strategy_id"]),
        "role": strategy.get("role", "CHALLENGER"),
        "version": strategy.get("version", "0.1.0"),
        "status": "COLLECTING EVIDENCE",
        "starting_capital": starting_capital,
        "cash": starting_capital,
        "equity": starting_capital,
        "previous_equity": starting_capital,
        "equity_change_this_run": 0.0,
        "realised_pnl": 0.0,
        "unrealised_pnl": 0.0,
        "open_positions": [],
        "closed_positions": [],
        "rejected_opportunities": [],
        "equity_history": [],
        "activity_journal": [],
        "heartbeat": {},
        "assumptions": copy.deepcopy(assumptions),
        "activity": {},
        "metrics": {},
    }


def journal(wallet: dict, event: str, symbol: str = "", detail: str = "", **extra) -> None:
    wallet.setdefault("activity_journal", []).append({
        "recorded_at": now_iso(),
        "event": event,
        "symbol": symbol,
        "detail": detail,
        **extra,
    })
    wallet["activity_journal"] = wallet["activity_journal"][-20000:]


def update_strategy_wallet(
    wallet: dict,
    strategy: dict,
    signals: list[dict],
    btc_signal: dict | None,
    assumptions: dict,
    snapshot_time: str | None,
) -> dict:
    previous_equity = float(wallet.get("equity") or wallet.get("starting_capital") or 100000)
    activity = {
        "retained": 0,
        "closed": 0,
        "opened": 0,
        "rejected_capacity": 0,
        "rejected_cash_reserve": 0,
        "rejected_existing": 0,
        "filtered_by_strategy": 0,
        "signals_checked": len(signals),
        "positions_evaluated": len(wallet.get("open_positions", [])),
    }
    current_by_symbol = {str(s.get("symbol") or "").upper(): s for s in signals}

    keep = []
    for position in wallet.get("open_positions", []):
        symbol = position["symbol"]
        live_signal = current_by_symbol.get(symbol)
        if live_signal:
            current_price = float(live_signal.get("entry_price") or position.get("current_price") or position["entry_price"])
            position["current_price"] = current_price
            gross_return = directional_return(position["direction"], position["entry_price"], current_price)
            position["gross_return"] = gross_return
            position["unrealised_return"] = gross_return - round_trip_cost(assumptions)
            position["unrealised_pnl"] = position["allocated_cash"] * position["unrealised_return"] / 100

        should_close, reason = exit_decision(position, live_signal)
        if should_close:
            position["status"] = "CLOSED"
            position["exit_time"] = now_iso()
            position["exit_price"] = position["current_price"]
            position["exit_reason"] = reason
            position["realised_return"] = position["unrealised_return"]
            position["realised_pnl"] = position["unrealised_pnl"]
            wallet["cash"] += position["allocated_cash"] + position["realised_pnl"]
            wallet["realised_pnl"] += position["realised_pnl"]
            wallet.setdefault("closed_positions", []).append(position)
            activity["closed"] += 1
            journal(
                wallet, "CLOSED", symbol, reason,
                return_pct=position["realised_return"],
                pnl=position["realised_pnl"],
            )
        else:
            keep.append(position)
            activity["retained"] += 1
            journal(
                wallet, "RETAINED", symbol, "Position revalued",
                return_pct=position.get("unrealised_return"),
                current_price=position.get("current_price"),
            )

    wallet["open_positions"] = keep
    open_symbols = {p["symbol"] for p in keep}

    candidates = []
    for signal in signals:
        applied = entry_call(strategy, signal, btc_signal)
        side = side_from_signal(applied)
        if side is None:
            if str(signal.get("signal") or "HOLD").upper() != "HOLD":
                activity["filtered_by_strategy"] += 1
                journal(
                    wallet, "FILTERED", str(signal.get("symbol") or ""),
                    f'{strategy.get("name")} entry rule did not pass',
                    base_signal=signal.get("signal"),
                )
            continue
        candidates.append((signal, applied, side))

    candidates.sort(
        key=lambda item: (
            abs(float(item[0].get("bullish") or 0) - float(item[0].get("bearish") or 0)),
            float(item[0].get("rvol") or 0),
            abs(float(item[0].get("return_4h") or 0)),
        ),
        reverse=True,
    )

    reserve = wallet["starting_capital"] * float(assumptions["minimum_cash_reserve_pct"]) / 100
    target = wallet["starting_capital"] * float(assumptions["position_size_pct"]) / 100

    for signal, applied, side in candidates:
        symbol = str(signal.get("symbol") or "").upper()
        if symbol in open_symbols:
            activity["rejected_existing"] += 1
            continue
        if len(wallet["open_positions"]) >= int(assumptions["max_positions"]):
            activity["rejected_capacity"] += 1
            rejected = {
                "recorded_at": now_iso(), "symbol": symbol, "signal": applied,
                "reason": "WALLET CAPACITY", "entry_price": signal.get("entry_price"),
            }
            wallet.setdefault("rejected_opportunities", []).append(rejected)
            journal(wallet, "REJECTED", symbol, "Wallet capacity", signal=applied)
            continue

        market_entry = float(signal.get("entry_price") or 0)
        available = max(0.0, wallet["cash"] - reserve)
        allocation = min(available, target)
        if market_entry <= 0 or allocation <= 0:
            activity["rejected_cash_reserve"] += 1
            wallet.setdefault("rejected_opportunities", []).append({
                "recorded_at": now_iso(), "symbol": symbol, "signal": applied,
                "reason": "CASH RESERVE", "entry_price": signal.get("entry_price"),
            })
            journal(wallet, "REJECTED", symbol, "Cash reserve", signal=applied)
            continue

        slip = float(assumptions.get("slippage_pct_per_side", 0.05)) / 100
        effective_entry = market_entry * (1 + slip if side == "LONG" else 1 - slip)
        entry_fee = allocation * float(assumptions.get("fee_pct_per_side", 0.10)) / 100
        net_allocation = allocation - entry_fee
        position = {
            "position_id": f'{strategy["strategy_id"]}_{signal.get("signal_id")}',
            "strategy_id": strategy["strategy_id"],
            "symbol": symbol,
            "name": signal.get("name") or symbol,
            "narrative": signal.get("narrative") or "",
            "signal": applied,
            "direction": side,
            "entry_time": signal.get("recorded_at") or now_iso(),
            "entry_price": effective_entry,
            "market_entry_price": market_entry,
            "current_price": market_entry,
            "allocated_cash": allocation,
            "entry_fee": entry_fee,
            "units": net_allocation / effective_entry,
            "status": "OPEN",
            "gross_return": 0.0,
            "unrealised_return": -round_trip_cost(assumptions),
            "unrealised_pnl": -allocation * round_trip_cost(assumptions) / 100,
        }
        wallet["cash"] -= allocation
        wallet["open_positions"].append(position)
        open_symbols.add(symbol)
        activity["opened"] += 1
        journal(
            wallet, "OPENED", symbol, applied,
            direction=side, entry_price=effective_entry, allocated_cash=allocation,
        )

    wallet["rejected_opportunities"] = wallet.get("rejected_opportunities", [])[-10000:]
    wallet["closed_positions"] = wallet.get("closed_positions", [])[-10000:]
    wallet["unrealised_pnl"] = sum(float(p.get("unrealised_pnl") or 0) for p in wallet["open_positions"])
    wallet["equity"] = wallet["cash"] + sum(
        float(p.get("allocated_cash") or 0) + float(p.get("unrealised_pnl") or 0)
        for p in wallet["open_positions"]
    )
    wallet["previous_equity"] = previous_equity
    wallet["equity_change_this_run"] = wallet["equity"] - previous_equity
    wallet["activity"] = activity
    wallet["updated_at"] = now_iso()
    wallet["heartbeat"] = {
        "last_run": wallet["updated_at"],
        "market_snapshot": snapshot_time,
        "wallet_updated": True,
        "signals_checked": len(signals),
        "positions_evaluated": activity["positions_evaluated"],
        "database_saved": True,
    }
    wallet.setdefault("equity_history", []).append({
        "recorded_at": wallet["updated_at"],
        "equity": wallet["equity"],
        "previous_equity": previous_equity,
        "equity_change": wallet["equity_change_this_run"],
        "cash": wallet["cash"],
        "realised_pnl": wallet["realised_pnl"],
        "unrealised_pnl": wallet["unrealised_pnl"],
        "open_positions": len(wallet["open_positions"]),
    })
    wallet["equity_history"] = wallet["equity_history"][-20000:]
    calculate_metrics(wallet)
    return wallet


def calculate_metrics(wallet: dict) -> None:
    closed = wallet.get("closed_positions", [])
    returns = [float(p.get("realised_return") or 0) for p in closed]
    wins = [r for r in returns if r > 0.25]
    losses = [r for r in returns if r < -0.25]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity_points = [
        float(x.get("equity") or 0)
        for x in wallet.get("equity_history", [])
        if x.get("equity") is not None
    ]
    peak = 0.0
    max_drawdown = 0.0
    for value in equity_points:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100)

    wallet["metrics"] = {
        "return_pct": (wallet["equity"] / wallet["starting_capital"] - 1) * 100,
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(returns) * 100 if returns else 0.0,
        "average_return": sum(returns) / len(returns) if returns else 0.0,
        "average_winner": sum(wins) / len(wins) if wins else 0.0,
        "average_loser": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0),
        "max_drawdown": max_drawdown,
    }


def main() -> int:
    latest = read_json(LATEST, {"signals": []})
    registry = read_json(REGISTRY, {"champion_id": "conviction_v1", "strategies": []})
    lab = read_json(LAB, {
        "updated_at": None,
        "starting_capital": 100000.0,
        "assumptions": DEFAULT_ASSUMPTIONS,
        "strategies": {},
    })
    assumptions = {**DEFAULT_ASSUMPTIONS, **(lab.get("assumptions") or {})}
    starting_capital = float(lab.get("starting_capital") or 100000.0)
    signals = latest.get("signals") or []
    snapshot_time = latest.get("generated_at")
    btc_signal = next((s for s in signals if str(s.get("symbol")).upper() == "BTC"), None)

    lab.setdefault("strategies", {})
    for strategy in registry.get("strategies", []):
        if not strategy.get("enabled", True):
            continue
        strategy_id = strategy["strategy_id"]
        wallet = lab["strategies"].get(strategy_id)
        if not wallet:
            wallet = empty_wallet(strategy, starting_capital, assumptions)
        wallet["name"] = strategy.get("name", strategy_id)
        wallet["role"] = strategy.get("role", "CHALLENGER")
        wallet["version"] = strategy.get("version", "0.1.0")
        lab["strategies"][strategy_id] = update_strategy_wallet(
            wallet, strategy, signals, btc_signal, assumptions, snapshot_time
        )

    lab["updated_at"] = now_iso()
    lab["market_snapshot"] = snapshot_time
    lab["assumptions"] = assumptions
    lab["heartbeat"] = {
        "last_run": lab["updated_at"],
        "market_snapshot": snapshot_time,
        "strategies_expected": len([s for s in registry.get("strategies", []) if s.get("enabled", True)]),
        "strategies_updated": len(lab["strategies"]),
        "database_saved": True,
    }
    write_json(LAB, lab)

    health = read_json(HEALTH, {})
    health["strategy_lab"] = {
        "updated_at": lab["updated_at"],
        "market_snapshot": snapshot_time,
        "heartbeat": lab["heartbeat"],
        "strategies": {
            sid: {
                "name": wallet.get("name"),
                "role": wallet.get("role"),
                "equity": wallet.get("equity"),
                "previous_equity": wallet.get("previous_equity"),
                "equity_change_this_run": wallet.get("equity_change_this_run"),
                "return_pct": (wallet.get("metrics") or {}).get("return_pct"),
                "open_positions": len(wallet.get("open_positions", [])),
                "closed_positions": len(wallet.get("closed_positions", [])),
                "activity": wallet.get("activity"),
                "heartbeat": wallet.get("heartbeat"),
                "status": wallet.get("status"),
            }
            for sid, wallet in lab["strategies"].items()
        },
    }
    write_json(HEALTH, health)

    print("\nSTRATEGY LAB")
    print(json.dumps({"heartbeat": lab["heartbeat"]}, indent=2))
    for wallet in lab["strategies"].values():
        metrics = wallet.get("metrics") or {}
        print(json.dumps({
            "strategy": wallet.get("name"),
            "role": wallet.get("role"),
            "previous_equity": round(float(wallet.get("previous_equity") or 0), 2),
            "equity": round(float(wallet.get("equity") or 0), 2),
            "change_this_run": round(float(wallet.get("equity_change_this_run") or 0), 2),
            "return_pct": round(float(metrics.get("return_pct") or 0), 3),
            "open": len(wallet.get("open_positions", [])),
            "closed_total": len(wallet.get("closed_positions", [])),
            "activity": wallet.get("activity"),
            "heartbeat": wallet.get("heartbeat"),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
