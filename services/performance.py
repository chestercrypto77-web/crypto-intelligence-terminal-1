from __future__ import annotations

from typing import Any
import math


def checkpoint_return(trade: dict[str, Any], key: str):
    value = (trade.get("returns") or {}).get(key)
    return value.get("return") if isinstance(value, dict) else value


def evaluated_return(trade: dict[str, Any]):
    if trade.get("status") == "CLOSED" and trade.get("final_return") is not None:
        return float(trade["final_return"])
    for key in ("7d", "3d", "1d", "12h", "4h", "1h"):
        value = checkpoint_return(trade, key)
        if value is not None:
            return float(value)
    value = trade.get("current_return")
    return float(value) if value is not None else None


def performance_summary(trades: list[dict[str, Any]]) -> dict[str, float]:
    results = [evaluated_return(trade) for trade in trades]
    results = [value for value in results if value is not None]
    wins = [value for value in results if value > 0.25]
    losses = [value for value in results if value < -0.25]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "calls": len(trades),
        "evaluated": len(results),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(results) * 100 if results else 0.0,
        "average_return": sum(results) / len(results) if results else 0.0,
        "average_winner": sum(wins) / len(wins) if wins else 0.0,
        "average_loser": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss
            else math.inf if gross_profit else 0.0
        ),
    }
