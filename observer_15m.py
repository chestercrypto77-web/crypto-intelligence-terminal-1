from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import copy
import json
import math
import time
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BINANCE = "https://api.binance.com/api/v3/klines"
COINGECKO = "https://api.coingecko.com/api/v3"

LATEST = DATA / "observer_latest.json"
HISTORY = DATA / "observer_history.json"
WALLET = DATA / "observer_wallet.json"
TIMING = DATA / "signal_timing.json"
SCALP_WALLET = DATA / "scalp_wallet.json"
SCALP_CHECKPOINTS = DATA / "scalp_checkpoints.json"
SCALP_LEARNING = DATA / "scalp_learning.json"
HOURLY = DATA / "signals_latest.json"
HEALTH = DATA / "engine_health.json"

YAHOO_TICKERS = {
    "BTC":"BTC-USD","SOL":"SOL-USD","AVAX":"AVAX-USD","POL":"POL28321-USD","DOT":"DOT-USD",
    "ZIL":"ZIL-USD","COTI":"COTI-USD","NEAR":"NEAR-USD","SUI":"SUI20947-USD",
    "SUPER":"SUPER8290-USD","S":"S-USD","AIOZ":"AIOZ-USD","FIL":"FIL-USD","SEI":"SEI-USD",
    "ONDO":"ONDO-USD","OM":"OM-USD","RUNE":"RUNE-USD","SAND":"SAND-USD","ONE":"ONE-USD",
    "WIN":"WIN-USD","AR":"AR-USD","BEAM":"BEAM-USD","SHIB":"SHIB-USD","ENJ":"ENJ-USD",
    "IMX":"IMX10603-USD","VET":"VET-USD","SC":"SC-USD","BTT":"BTT-USD","TLM":"TLM-USD",
    "PYR":"PYR-USD","PAAL":"PAAL-USD","SKL":"SKL-USD","AERO":"AERO29270-USD","LUNC":"LUNC-USD",
    "GALA":"GALA-USD","UOS":"UOS-USD","UFO":"UFO-USD","DENT":"DENT-USD","MEW":"MEW-USD",
    "DOGE":"DOGE-USD","GRT":"GRT-USD","VRA":"VRA-USD","VTHO":"VTHO-USD","XTZ":"XTZ-USD",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def json_default(value: Any) -> Any:
    """Convert NumPy/Pandas values into JSON-safe native Python values."""
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (pd.Timestamp, datetime)):
        timestamp = pd.Timestamp(value)
        timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        return timestamp.isoformat()
    if value is pd.NA:
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def sanitise_json(value: Any) -> Any:
    """Recursively normalise nested structures before persistence."""
    if isinstance(value, dict):
        return {str(key): sanitise_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitise_json(item) for item in value]
    if isinstance(value, (np.bool_, np.integer, np.floating, np.ndarray, pd.Timestamp, datetime)):
        return json_default(value)
    if value is pd.NA:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    safe_payload = sanitise_json(payload)
    temp.write_text(
        json.dumps(safe_payload, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(path)


def binance_15m(symbol: str) -> pd.DataFrame:
    try:
        response = requests.get(
            BINANCE,
            params={"symbol": f"{symbol}USDT", "interval": "15m", "limit": 400},
            timeout=12,
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(
            rows,
            columns=["t","Open","High","Low","Close","Volume","ct","q","n","tb","tq","i"],
        )
        frame.index = pd.to_datetime(frame["t"], unit="ms", utc=True)
        for column in ["Open","High","Low","Close","Volume"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def yahoo_15m(ticker: str) -> pd.DataFrame:
    try:
        frame = yf.download(
            ticker, period="5d", interval="15m", auto_adjust=True,
            progress=False, threads=False,
        )
        if frame is None or frame.empty:
            return pd.DataFrame()
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        needed = ["Open","High","Low","Close","Volume"]
        if not all(column in frame.columns for column in needed):
            return pd.DataFrame()
        frame = frame[needed].dropna(subset=["Close"]).copy()
        frame.index = pd.to_datetime(frame.index, utc=True)
        return frame
    except Exception:
        return pd.DataFrame()


def coingecko_15m(coin_id: str | None) -> pd.DataFrame:
    # CoinGecko free history is not guaranteed to be exactly 15-minute data.
    # It is retained as a last-resort observer fallback and labelled accordingly.
    if not coin_id:
        return pd.DataFrame()
    try:
        response = requests.get(
            f"{COINGECKO}/coins/{coin_id}/market_chart",
            params={"vs_currency":"usd","days":"1"},
            headers={"User-Agent":"CryptoIntelligenceTerminal/8.9.0"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        prices = payload.get("prices") or []
        volumes = payload.get("total_volumes") or []
        if len(prices) < 30:
            return pd.DataFrame()
        price = pd.DataFrame(prices, columns=["timestamp","Close"])
        price["timestamp"] = pd.to_datetime(price["timestamp"], unit="ms", utc=True)
        price = price.set_index("timestamp")
        volume = pd.DataFrame(volumes, columns=["timestamp","Volume"])
        volume["timestamp"] = pd.to_datetime(volume["timestamp"], unit="ms", utc=True)
        volume = volume.set_index("timestamp")
        frame = price.join(volume, how="left").sort_index()
        frame["Volume"] = frame["Volume"].ffill().fillna(0)
        frame["Open"] = frame["Close"].shift(1).fillna(frame["Close"])
        frame["High"] = frame[["Open","Close"]].max(axis=1)
        frame["Low"] = frame[["Open","Close"]].min(axis=1)
        return frame[["Open","High","Low","Close","Volume"]].resample("15min").agg({
            "Open":"first","High":"max","Low":"min","Close":"last","Volume":"last"
        }).dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()


def fetch_15m(symbol: str, ticker: str, coin_id: str | None) -> tuple[str, pd.DataFrame, bool]:
    binance = binance_15m(symbol)
    if not binance.empty:
        return "Binance 15m", binance, False
    yahoo = yahoo_15m(ticker)
    if not yahoo.empty:
        return "Yahoo 15m", yahoo, False
    fallback = coingecko_15m(coin_id)
    if not fallback.empty:
        return "CoinGecko observer fallback", fallback, True
    return "", pd.DataFrame(), False


def enrich(frame: pd.DataFrame) -> pd.DataFrame:
    values = frame.copy()
    close = values["Close"].astype(float)
    volume = values["Volume"].fillna(0).astype(float)

    values["EMA9"] = close.ewm(span=9, adjust=False).mean()
    values["EMA21"] = close.ewm(span=21, adjust=False).mean()
    values["EMA55"] = close.ewm(span=55, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = (
        gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        / loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean().replace(0, np.nan)
    )
    values["RSI"] = 100 - 100 / (1 + rs)
    values["RSI_D"] = values["RSI"] - values["RSI"].shift(4)

    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    values["MACD_H"] = hist
    values["MACD_D"] = hist - hist.shift(4)

    values["RVOL"] = volume / volume.rolling(32).mean().replace(0, np.nan)
    values["RVOL_D"] = values["RVOL"] - values["RVOL"].shift(4)
    values["R15"] = close.pct_change() * 100
    values["R1H"] = close.pct_change(4) * 100
    values["R4H"] = close.pct_change(16) * 100
    values["R24H"] = close.pct_change(96) * 100
    values["GREEN8"] = (close > values["Open"]).rolling(8).sum()
    values["RED8"] = (close < values["Open"]).rolling(8).sum()
    values["PREV_HIGH"] = values["High"].shift(1).rolling(16).max()
    values["PREV_LOW"] = values["Low"].shift(1).rolling(16).min()
    values["BREAKOUT"] = close > values["PREV_HIGH"]
    values["BREAKDOWN"] = close < values["PREV_LOW"]
    return values


def observe(frame: pd.DataFrame) -> dict | None:
    values = enrich(frame).dropna(
        subset=["EMA9","EMA21","EMA55","RSI","MACD_H","RVOL","R1H","R4H"]
    )
    if values.empty:
        return None
    row = values.iloc[-1]
    close = float(row["Close"])

    bullish_checks = {
        "price_above_ema9": close > row["EMA9"],
        "ema9_above_ema21": row["EMA9"] > row["EMA21"],
        "macd_positive": row["MACD_H"] > 0,
        "macd_improving": row["MACD_D"] > 0,
        "rsi_improving": row["RSI_D"] > 0 and row["RSI"] >= 48,
        "rvol_active": row["RVOL"] >= 1.15,
        "rvol_rising": row["RVOL_D"] > 0.10,
        "one_hour_positive": row["R1H"] > 0,
        "four_hour_positive": row["R4H"] > 0,
        "breakout": bool(row["BREAKOUT"]),
    }
    bearish_checks = {
        "price_below_ema9": close < row["EMA9"],
        "ema9_below_ema21": row["EMA9"] < row["EMA21"],
        "macd_negative": row["MACD_H"] < 0,
        "macd_weakening": row["MACD_D"] < 0,
        "rsi_weakening": row["RSI_D"] < 0 and row["RSI"] <= 52,
        "rvol_low": row["RVOL"] < 0.70,
        "rvol_falling": row["RVOL_D"] < -0.10,
        "one_hour_negative": row["R1H"] < 0,
        "four_hour_negative": row["R4H"] < 0,
        "breakdown": bool(row["BREAKDOWN"]),
    }
    bull = sum(bool(v) for v in bullish_checks.values())
    bear = sum(bool(v) for v in bearish_checks.values())

    if bull >= 8 and bear <= 2:
        signal = "EARLY BUY"
        state = "FORMING"
    elif bull >= 6 and bear <= 4:
        signal = "BUY WATCH"
        state = "DETECTED"
    elif bear >= 8 and bull <= 2:
        signal = "EARLY SELL"
        state = "FORMING"
    elif bear >= 6 and bull <= 4:
        signal = "SELL WATCH"
        state = "DETECTED"
    elif abs(float(row["R15"])) >= 3 or (float(row["RVOL"]) >= 2.5 and abs(float(row["R1H"])) >= 2):
        signal = "VOLATILITY WATCH"
        state = "DETECTED"
    else:
        signal = "NEUTRAL"
        state = "NEUTRAL"

    timestamp = pd.Timestamp(values.index[-1])
    timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
    return {
        "signal": signal,
        "lifecycle_state": state,
        "price": close,
        "return_15m": float(row["R15"]),
        "return_1h": float(row["R1H"]),
        "return_4h": float(row["R4H"]),
        "return_24h": float(row["R24H"]) if pd.notna(row["R24H"]) else None,
        "rvol": float(row["RVOL"]),
        "rvol_delta": float(row["RVOL_D"]),
        "rsi": float(row["RSI"]),
        "rsi_delta": float(row["RSI_D"]),
        "macd_histogram": float(row["MACD_H"]),
        "macd_delta": float(row["MACD_D"]),
        "bullish_conditions": bull,
        "bearish_conditions": bear,
        "breakout": bool(row["BREAKOUT"]),
        "breakdown": bool(row["BREAKDOWN"]),
        "candle_time": timestamp.isoformat(),
        "checks": {
            "bullish": {key: bool(value) for key, value in bullish_checks.items()},
            "bearish": {key: bool(value) for key, value in bearish_checks.items()},
        },
    }


def side_from_observer(signal: str) -> str | None:
    signal = str(signal or "").upper()
    if signal == "EARLY BUY":
        return "LONG"
    if signal == "EARLY SELL":
        return "SHORT"
    return None

def reentry_side(item: dict) -> str | None:
    """A fresh setup after an exit must re-earn entry; no revenge trading."""
    signal=str(item.get("signal") or "").upper()
    direct=side_from_observer(signal)
    if direct: return direct
    bull=int(item.get("bullish_conditions") or 0); bear=int(item.get("bearish_conditions") or 0)
    rvol=float(item.get("rvol") or 0); rvold=float(item.get("rvol_delta") or 0); r1h=float(item.get("return_1h") or 0)
    if signal=="BUY WATCH" and bull-bear>=5 and rvol>=1.15 and rvold>0 and r1h>0: return "LONG"
    if signal=="SELL WATCH" and bear-bull>=5 and rvol>=1.15 and rvold>0 and r1h<0: return "SHORT"
    return None


def net_return(direction: str, entry: float, current: float, cost: float) -> float:
    raw = (current / entry - 1) * 100
    directional = raw if direction == "LONG" else -raw
    return directional - cost


def update_wallet(wallet: dict, signals: list[dict], timestamp: str) -> dict:
    wallet.setdefault("activity_journal", [])
    wallet.setdefault("rejected_opportunities", [])
    previous_equity = float(wallet.get("equity") or wallet.get("starting_cash") or 100000)
    current = {item["symbol"]: item for item in signals}
    round_trip_cost = 2 * (
        float(wallet.get("fee_pct_per_side", 0.10))
        + float(wallet.get("slippage_pct_per_side", 0.05))
    )
    activity = {"retained":0,"closed":0,"opened":0,"rejected":0}

    keep = []
    for position in wallet.get("open_positions", []):
        item = current.get(position["symbol"])
        if item:
            price = float(item["price"])
            position["current_price"] = price
            position["unrealised_return"] = net_return(
                position["direction"], position["entry_price"], price, round_trip_cost
            )
            position["unrealised_pnl"] = (
                position["allocated_cash"] * position["unrealised_return"] / 100
            )
            position["maximum_favourable_excursion_pct"]=max(float(position.get("maximum_favourable_excursion_pct") or 0),float(position["unrealised_return"]))
            position["maximum_adverse_excursion_pct"]=min(float(position.get("maximum_adverse_excursion_pct") or 0),float(position["unrealised_return"]))
            new_side=side_from_observer(item.get("signal"))
            reversed_side=new_side is not None and new_side!=position["direction"]
            invalidated=(position["direction"]=="LONG" and float(item.get("return_1h") or 0)<=-3) or (position["direction"]=="SHORT" and float(item.get("return_1h") or 0)>=3)
            hard_stop=float(position["unrealised_return"])<=-2.25
            mfe=float(position.get("maximum_favourable_excursion_pct") or 0)
            trail_floor=(mfe-3.5 if mfe>=10 else mfe-2.0 if mfe>=5 else 0.50 if mfe>=3 else None)
            profit_trail=trail_floor is not None and float(position["unrealised_return"])<=trail_floor
        else:
            reversed_side=invalidated=hard_stop=profit_trail=False

        # PYR lesson: NEUTRAL means no fresh edge; it is not proof the existing trade is invalid.
        if reversed_side or invalidated or hard_stop or profit_trail:
            position["status"]="CLOSED"
            position["exit_time"]=timestamp
            position["exit_price"]=position["current_price"]
            position["exit_reason"]=("Observer reversal" if reversed_side else "Observer invalidation" if invalidated else "HARD RISK STOP" if hard_stop else "PROFIT TRAIL")
            position["realised_return"] = position["unrealised_return"]
            position["realised_pnl"] = position["unrealised_pnl"]
            wallet["cash"] += position["allocated_cash"] + position["realised_pnl"]
            wallet["realised_pnl"] += position["realised_pnl"]
            wallet.setdefault("closed_positions", []).append(position)
            wallet["activity_journal"].append({
                "recorded_at": timestamp,
                "event": "CLOSED",
                "symbol": position["symbol"],
                "detail": position["exit_reason"],
                "return_pct": position["realised_return"],
                "pnl": position["realised_pnl"],
            })
            activity["closed"] += 1
        else:
            keep.append(position)
            activity["retained"] += 1

    wallet["open_positions"] = keep
    open_symbols = {p["symbol"] for p in keep}
    recent_closed={}
    for closed in reversed(wallet.get("closed_positions",[])):
        symbol=str(closed.get("symbol") or "").upper()
        if symbol in recent_closed: continue
        try: age_hours=(pd.Timestamp(timestamp)-pd.Timestamp(closed.get("exit_time"))).total_seconds()/3600
        except Exception: age_hours=999
        if age_hours<=48: recent_closed[symbol]=closed

    candidates=[]
    for raw in signals:
        item=dict(raw); symbol=str(item.get("symbol") or "").upper()
        direct=side_from_observer(item.get("signal"))
        fresh=reentry_side(item) if symbol in recent_closed else None
        if direct or fresh:
            item["_entry_side"]=direct or fresh
            item["_reentry"]=bool(fresh and not direct)
            candidates.append(item)
    candidates.sort(
        key=lambda item: (
            abs(int(item.get("bullish_conditions") or 0) - int(item.get("bearish_conditions") or 0)),
            float(item.get("rvol") or 0),
            abs(float(item.get("return_1h") or 0)),
        ),
        reverse=True,
    )

    reserve = float(wallet.get("starting_cash", 100000)) * float(
        wallet.get("minimum_cash_reserve_pct", 20)
    ) / 100
    # Shadow Observer positions are capped while the strategy is learning.
    target=float(wallet.get("starting_cash",100000))*min(float(wallet.get("position_size_pct",10)),2.5)/100

    for item in candidates:
        symbol = item["symbol"]
        if symbol in open_symbols:
            continue
        if len(wallet["open_positions"]) >= int(wallet.get("max_positions", 8)):
            wallet["rejected_opportunities"].append({
                "recorded_at": timestamp,
                "symbol": symbol,
                "signal": item["signal"],
                "reason": "WALLET CAPACITY",
                "price": item["price"],
            })
            activity["rejected"] += 1
            continue
        allocation_target=target*(0.50 if item.get("_reentry") else 1.0)
        allocation=min(allocation_target,max(0.0,wallet["cash"]-reserve))
        if allocation <= 0:
            wallet["rejected_opportunities"].append({
                "recorded_at": timestamp,
                "symbol": symbol,
                "signal": item["signal"],
                "reason": "CASH RESERVE",
                "price": item["price"],
            })
            activity["rejected"] += 1
            continue

        direction = item.get("_entry_side") or side_from_observer(item["signal"])
        slip = float(wallet.get("slippage_pct_per_side", 0.05)) / 100
        market_price = float(item["price"])
        entry = market_price * (1 + slip if direction == "LONG" else 1 - slip)
        fee = allocation * float(wallet.get("fee_pct_per_side", 0.10)) / 100
        position = {
            "position_id": f'OBSERVER_{symbol}_{item.get("candle_time")}',
            "symbol": symbol,
            "name": item.get("name") or symbol,
            "narrative": item.get("narrative") or "",
            "signal": item["signal"],
            "direction": direction,
            "entry_type": "RE-ENTRY" if item.get("_reentry") else "INITIAL",
            "entry_time": timestamp,
            "entry_price": entry,
            "market_entry_price": market_price,
            "current_price": market_price,
            "allocated_cash": allocation,
            "entry_fee": fee,
            "units": (allocation - fee) / entry,
            "status": "OPEN",
            "unrealised_return": -round_trip_cost,
            "unrealised_pnl": -allocation * round_trip_cost / 100,
            "maximum_favourable_excursion_pct": 0.0,
            "maximum_adverse_excursion_pct": -round_trip_cost,
            "observer_evidence": {
                "rvol": item.get("rvol"),
                "rsi": item.get("rsi"),
                "return_1h": item.get("return_1h"),
                "bullish_conditions": item.get("bullish_conditions"),
                "bearish_conditions": item.get("bearish_conditions"),
            },
        }
        wallet["cash"] -= allocation
        wallet["open_positions"].append(position)
        open_symbols.add(symbol)
        wallet["activity_journal"].append({
            "recorded_at": timestamp,
            "event": "OPENED",
            "symbol": symbol,
            "detail": item["signal"],
            "direction": direction,
            "entry_price": entry,
            "allocated_cash": allocation,
        })
        activity["opened"] += 1

    wallet["closed_positions"] = wallet.get("closed_positions", [])[-10000:]
    wallet["rejected_opportunities"] = wallet.get("rejected_opportunities", [])[-10000:]
    wallet["activity_journal"] = wallet.get("activity_journal", [])[-20000:]
    wallet["unrealised_pnl"] = sum(
        float(position.get("unrealised_pnl") or 0)
        for position in wallet["open_positions"]
    )
    wallet["equity"] = wallet["cash"] + sum(
        float(position.get("allocated_cash") or 0)
        + float(position.get("unrealised_pnl") or 0)
        for position in wallet["open_positions"]
    )
    wallet["previous_equity"] = previous_equity
    wallet["equity_change_this_run"] = wallet["equity"] - previous_equity
    wallet["updated_at"] = timestamp
    wallet["activity"] = activity
    wallet.setdefault("equity_history", []).append({
        "recorded_at": timestamp,
        "equity": wallet["equity"],
        "previous_equity": previous_equity,
        "equity_change": wallet["equity_change_this_run"],
        "cash": wallet["cash"],
        "realised_pnl": wallet["realised_pnl"],
        "unrealised_pnl": wallet["unrealised_pnl"],
        "open_positions": len(wallet["open_positions"]),
    })
    wallet["equity_history"] = wallet["equity_history"][-20000:]
    return wallet


def update_timing(timing: dict, observer_signals: list[dict], hourly: dict, timestamp: str) -> dict:
    timing.setdefault("assets", {})
    hourly_by_symbol = {
        str(item.get("symbol") or "").upper(): item
        for item in (hourly.get("signals") or [])
    }

    for item in observer_signals:
        symbol = item["symbol"]
        asset = timing["assets"].setdefault(symbol, {
            "symbol": symbol,
            "observer_events": [],
            "hourly_events": [],
            "comparisons": [],
        })
        observer_side = side_from_observer(item.get("signal"))
        if observer_side:
            key = f'{observer_side}:{item.get("candle_time")}'
            if not any(event.get("event_key") == key for event in asset["observer_events"]):
                asset["observer_events"].append({
                    "event_key": key,
                    "detected_at": timestamp,
                    "candle_time": item.get("candle_time"),
                    "direction": observer_side,
                    "signal": item.get("signal"),
                    "price": item.get("price"),
                    "rvol": item.get("rvol"),
                })

        hourly_item = hourly_by_symbol.get(symbol)
        hourly_signal = str((hourly_item or {}).get("signal") or "HOLD")
        hourly_side = "LONG" if "BUY" in hourly_signal else "SHORT" if "SELL" in hourly_signal else None
        if hourly_side:
            event_key = f'{hourly_side}:{hourly_item.get("candle_time")}'
            if not any(event.get("event_key") == event_key for event in asset["hourly_events"]):
                event = {
                    "event_key": event_key,
                    "detected_at": hourly_item.get("recorded_at"),
                    "candle_time": hourly_item.get("candle_time"),
                    "direction": hourly_side,
                    "signal": hourly_signal,
                    "price": hourly_item.get("entry_price"),
                }
                asset["hourly_events"].append(event)

                matching = [
                    observer_event
                    for observer_event in asset["observer_events"]
                    if observer_event.get("direction") == hourly_side
                ]
                if matching:
                    first = matching[0]
                    try:
                        lead_minutes = (
                            pd.Timestamp(event["detected_at"])
                            - pd.Timestamp(first["detected_at"])
                        ).total_seconds() / 60
                    except Exception:
                        lead_minutes = None
                    asset["comparisons"].append({
                        "compared_at": timestamp,
                        "direction": hourly_side,
                        "observer_detected_at": first.get("detected_at"),
                        "hourly_detected_at": event.get("detected_at"),
                        "observer_price": first.get("price"),
                        "hourly_price": event.get("price"),
                        "lead_minutes": lead_minutes,
                    })

        asset["observer_events"] = asset["observer_events"][-1000:]
        asset["hourly_events"] = asset["hourly_events"][-1000:]
        asset["comparisons"] = asset["comparisons"][-1000:]

    timing["updated_at"] = timestamp
    return timing



def scalp_side(value):
    value=str(value or '').upper()
    return 'LONG' if value=='EARLY BUY' else 'SHORT' if value=='EARLY SELL' else None

def scalp_cost(rules):
    return 2*(float(rules.get('fee_pct_per_side',.10))+float(rules.get('slippage_pct_per_side',.05)))

def direction_return(direction,entry,current):
    raw=(current/entry-1)*100 if entry else 0
    return raw if direction=='LONG' else -raw

def scalp_edge(item,rules):
    side=scalp_side(item.get('signal')); rvol=float(item.get('rvol') or 0); rvold=float(item.get('rvol_delta') or 0)
    agreement=abs(int(item.get('bullish_conditions') or 0)-int(item.get('bearish_conditions') or 0))
    gross=min(4.0,max(abs(float(item.get('return_1h') or 0))*.55,abs(float(item.get('return_4h') or 0))*.18,max(0,rvol-1)*.7,agreement*.12))
    net=gross-scalp_cost(rules); rr=net/float(rules.get('stop_loss_pct',1.25))
    reasons=[]
    if side is None: reasons.append('NO DECISIVE EARLY SIGNAL')
    if rvol<1.15: reasons.append('PARTICIPATION TOO LOW')
    if rvold<=0: reasons.append('VOLUME NOT ACCELERATING')
    if agreement<6: reasons.append('DIRECTIONAL AGREEMENT TOO WEAK')
    if net<float(rules.get('minimum_expected_net_move_pct',.60)): reasons.append('EXPECTED NET MOVE TOO SMALL')
    if rr<float(rules.get('minimum_reward_risk',1.5)): reasons.append('REWARD/RISK BELOW MINIMUM')
    return {'side':side,'estimated_net_move_pct':net,'estimated_reward_risk':rr,'eligible':not reasons,'reasons':reasons}

def scalp_drawdown(wallet):
    peak=float(wallet.get('starting_cash') or 100000); maximum=0
    for point in wallet.get('equity_history') or []:
        eq=float(point.get('equity') or 0); peak=max(peak,eq); maximum=max(maximum,(peak-eq)/peak*100 if peak else 0)
    return maximum

def update_scalp(wallet,checkpoints,signals,timestamp):
    if not wallet: wallet=copy.deepcopy({'wallet_id': 'SCALP_WALLET_V1', 'name': 'Profit-Driven Scalp Wallet', 'currency': 'USD', 'starting_cash': 100000.0, 'cash': 100000.0, 'equity': 100000.0, 'previous_equity': 100000.0, 'equity_change_this_run': 0.0, 'realised_pnl': 0.0, 'unrealised_pnl': 0.0, 'open_positions': [], 'closed_positions': [], 'rejected_opportunities': [], 'equity_history': [], 'activity_journal': [], 'session': {'date': None, 'starting_equity': 100000.0, 'realised_pnl': 0.0, 'consecutive_losses': 0, 'new_entries_frozen': False, 'freeze_reason': None}, 'rules': {'base_position_pct': 0.25, 'max_positions': 4, 'max_total_deployed_pct': 2.0, 'minimum_cash_reserve_pct': 95.0, 'fee_pct_per_side': 0.1, 'slippage_pct_per_side': 0.05, 'minimum_reward_risk': 1.5, 'minimum_expected_net_move_pct': 0.6, 'stop_loss_pct': 1.25, 'take_profit_pct': 2.25, 'maximum_hold_minutes': 180, 'daily_loss_limit_pct': 0.75, 'wallet_drawdown_freeze_pct': 3.0, 'consecutive_loss_pause': 3}})
    rules=wallet['rules']; date=str(timestamp)[:10]; session=wallet.setdefault('session',{})
    if session.get('date')!=date: session.update({'date':date,'starting_equity':float(wallet.get('equity') or 100000),'realised_pnl':0.0,'consecutive_losses':0,'new_entries_frozen':False,'freeze_reason':None})
    previous=float(wallet.get('equity') or 100000); current={str(x.get('symbol') or '').upper():x for x in signals}; keep=[]; activity={'retained':0,'closed':0,'opened':0,'rejected':0}
    cost=scalp_cost(rules)
    for p in wallet.get('open_positions') or []:
        item=current.get(p['symbol']); price=float((item or {}).get('price') or p.get('current_price') or p['entry_price']); p['current_price']=price
        net=direction_return(p['direction'],p['entry_price'],price)-cost; p['unrealised_return']=net; p['unrealised_pnl']=p['allocated_cash']*net/100
        p['maximum_favourable_excursion_pct']=max(float(p.get('maximum_favourable_excursion_pct') or 0),net); p['maximum_adverse_excursion_pct']=min(float(p.get('maximum_adverse_excursion_pct') or 0),net)
        try: minutes=(pd.Timestamp(timestamp)-pd.Timestamp(p['entry_time'])).total_seconds()/60
        except: minutes=0
        p['minutes_open']=minutes; side=scalp_side((item or {}).get('signal'))
        reason='TAKE PROFIT' if net>=float(rules['take_profit_pct']) else 'STOP LOSS' if net<=-float(rules['stop_loss_pct']) else 'OBSERVER REVERSAL' if side and side!=p['direction'] else 'TIME EXIT' if minutes>=float(rules['maximum_hold_minutes']) else None
        checkpoints.append({'recorded_at':timestamp,'position_id':p['position_id'],'symbol':p['symbol'],'status':'CLOSED' if reason else 'OPEN','price':price,'return_pct':net,'pnl':p['unrealised_pnl']})
        if reason:
            p.update({'status':'CLOSED','exit_time':timestamp,'exit_price':price,'exit_reason':reason,'realised_return':net,'realised_pnl':p['unrealised_pnl']}); wallet['cash']+=p['allocated_cash']+p['realised_pnl']; wallet['realised_pnl']+=p['realised_pnl']; wallet.setdefault('closed_positions',[]).append(p); session['realised_pnl']+=p['realised_pnl']; session['consecutive_losses']=session.get('consecutive_losses',0)+1 if p['realised_pnl']<0 else 0; activity['closed']+=1
        else: keep.append(p); activity['retained']+=1
    wallet['open_positions']=keep
    daily_loss=-session.get('realised_pnl',0)/session.get('starting_equity',100000)*100 if session.get('realised_pnl',0)<0 else 0
    if daily_loss>=float(rules['daily_loss_limit_pct']): session.update({'new_entries_frozen':True,'freeze_reason':'DAILY LOSS LIMIT'})
    if session.get('consecutive_losses',0)>=int(rules['consecutive_loss_pause']): session.update({'new_entries_frozen':True,'freeze_reason':'CONSECUTIVE LOSS PAUSE'})
    open_symbols={p['symbol'] for p in keep}; deployed=sum(p['allocated_cash'] for p in keep); max_deployed=wallet['starting_cash']*float(rules['max_total_deployed_pct'])/100; reserve=wallet['starting_cash']*float(rules['minimum_cash_reserve_pct'])/100; base=wallet['starting_cash']*float(rules['base_position_pct'])/100
    ranked=sorted([(x,scalp_edge(x,rules)) for x in signals],key=lambda pair:(pair[1]['eligible'],pair[1]['estimated_reward_risk']),reverse=True)
    for item,edge in ranked:
        symbol=str(item.get('symbol') or '').upper()
        if symbol in open_symbols or session.get('new_entries_frozen'): continue
        if not edge['eligible']:
            if item.get('signal') in {'EARLY BUY','EARLY SELL'}: wallet.setdefault('rejected_opportunities',[]).append({'recorded_at':timestamp,'symbol':symbol,'signal':item.get('signal'),'reason':' | '.join(edge['reasons']),'estimated_net_move_pct':edge['estimated_net_move_pct'],'estimated_reward_risk':edge['estimated_reward_risk']}); activity['rejected']+=1
            continue
        if len(wallet['open_positions'])>=int(rules['max_positions']): break
        allocation=min(base,max_deployed-deployed,max(0,wallet['cash']-reserve))
        if allocation<=0: break
        market=float(item.get('price') or 0); side=edge['side']; slip=float(rules['slippage_pct_per_side'])/100; entry=market*(1+slip if side=='LONG' else 1-slip); fee=allocation*float(rules['fee_pct_per_side'])/100
        p={'position_id':f'SCALP_{symbol}_{str(item.get("candle_time")).replace(":","")}','symbol':symbol,'name':item.get('name') or symbol,'narrative':item.get('narrative') or '','strategy':'PROFIT_SCALP_V1','signal':item.get('signal'),'direction':side,'entry_time':timestamp,'entry_price':entry,'market_entry_price':market,'current_price':market,'allocated_cash':allocation,'entry_fee':fee,'units':(allocation-fee)/entry,'status':'OPEN','unrealised_return':-cost,'unrealised_pnl':-allocation*cost/100,'maximum_favourable_excursion_pct':0.0,'maximum_adverse_excursion_pct':-cost,'minutes_open':0.0,'profit_objective':edge,'entry_evidence':{'rvol':item.get('rvol'),'rvol_delta':item.get('rvol_delta'),'rsi':item.get('rsi'),'return_1h':item.get('return_1h')}}
        wallet['cash']-=allocation; wallet['open_positions'].append(p); open_symbols.add(symbol); deployed+=allocation; activity['opened']+=1
    wallet['unrealised_pnl']=sum(float(p.get('unrealised_pnl') or 0) for p in wallet['open_positions']); wallet['equity']=wallet['cash']+sum(p['allocated_cash']+p['unrealised_pnl'] for p in wallet['open_positions']); wallet['previous_equity']=previous; wallet['equity_change_this_run']=wallet['equity']-previous; wallet['updated_at']=timestamp; wallet['activity']=activity
    wallet.setdefault('equity_history',[]).append({'recorded_at':timestamp,'equity':wallet['equity'],'cash':wallet['cash'],'realised_pnl':wallet['realised_pnl'],'unrealised_pnl':wallet['unrealised_pnl'],'open_positions':len(wallet['open_positions'])}); return wallet,checkpoints[-100000:]

def update_scalp_learning(wallet,timestamp):
    closed=wallet.get('closed_positions') or []; returns=[float(p.get('realised_return') or 0) for p in closed]; wins=[x for x in returns if x>0]; losses=[x for x in returns if x<0]; gp=sum(wins); gl=abs(sum(losses)); expectancy=sum(returns)/len(returns) if returns else 0; pf=gp/gl if gl else (999.0 if gp else 0.0)
    reasons=[]
    if len(closed)<50: reasons.append(f'Need 50 closed trades; currently {len(closed)}.')
    if expectancy<=0: reasons.append('Net expectancy is not positive.')
    if pf<1.25: reasons.append('Profit factor is below 1.25.')
    eligible=not reasons and len(closed)>=50
    return {'updated_at':timestamp,'objective':'Maximise net paper-wallet growth after fees and slippage while controlling drawdown.','setups':{},'global':{'closed_trades':len(closed),'wins':len(wins),'losses':len(losses),'win_rate':len(wins)/len(closed)*100 if closed else 0.0,'net_pnl':float(wallet.get('realised_pnl') or 0),'expectancy_pct':expectancy,'profit_factor':pf,'maximum_drawdown_pct':scalp_drawdown(wallet)},'promotion':{'stage':'POSITIVE EXPECTANCY ESTABLISHED' if eligible else 'INITIAL LEARNING','allocation_pct':0.50 if eligible else 0.25,'eligible':eligible,'reasons':reasons}}

def main() -> int:
    holdings = read_json(ROOT / "holdings.json", [])
    previous = read_json(LATEST, {"signals": []})
    previous_by_symbol = {
        str(item.get("symbol") or "").upper(): item
        for item in (previous.get("signals") or [])
    }
    history = read_json(HISTORY, [])
    wallet = read_json(WALLET, {})
    timing = read_json(TIMING, {"updated_at":None,"assets":{}})
    scalp_wallet = read_json(SCALP_WALLET, {})
    scalp_checkpoints = read_json(SCALP_CHECKPOINTS, [])
    hourly = read_json(HOURLY, {"signals":[]})
    health = read_json(HEALTH, {})

    timestamp = now_iso()
    signals = []
    unavailable = []
    fallback_assets = []
    provider_counts = {}
    new_events = 0

    # Fetch market data concurrently. Signal/wallet state updates remain sequential and deterministic.
    fetch_results = {}
    workers = min(8, max(2, len(holdings)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for holding in holdings:
            symbol = str(holding.get("symbol") or "").upper()
            futures[pool.submit(fetch_15m, symbol, YAHOO_TICKERS.get(symbol, f"{symbol}-USD"), holding.get("coin_id"))] = holding
        for fut in as_completed(futures):
            holding = futures[fut]
            symbol = str(holding.get("symbol") or "").upper()
            try:
                fetch_results[symbol] = fut.result()
            except Exception:
                fetch_results[symbol] = ("", pd.DataFrame(), False)

    for holding in holdings:
        symbol = str(holding.get("symbol") or "").upper()
        provider, frame, fallback = fetch_results.get(symbol, ("", pd.DataFrame(), False))
        if frame.empty:
            unavailable.append(symbol)
            continue
        observation = observe(frame)
        if not observation:
            unavailable.append(symbol)
            continue

        if fallback:
            fallback_assets.append(symbol)
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        old = previous_by_symbol.get(symbol, {})
        changed = old.get("signal") is not None and old.get("signal") != observation["signal"]
        record = {
            "observer_id": f'{symbol}_{observation["signal"].replace(" ","_")}_{observation["candle_time"]}',
            "recorded_at": timestamp,
            "symbol": symbol,
            "name": holding.get("name") or symbol,
            "narrative": holding.get("narrative") or "",
            "tier": holding.get("tier") or "",
            "data_source": provider,
            "previous_signal": old.get("signal"),
            "changed": changed,
            **observation,
        }
        signals.append(record)

        event_key = f'{record["observer_id"]}:{record["lifecycle_state"]}'
        if not any(item.get("event_key") == event_key for item in history):
            history.append({
                "event_key": event_key,
                **record,
            })
            new_events += 1
        time.sleep(0.03)

    wallet = update_wallet(wallet, signals, timestamp)
    timing = update_timing(timing, signals, hourly, timestamp)
    scalp_wallet, scalp_checkpoints = update_scalp(scalp_wallet, scalp_checkpoints, signals, timestamp)
    scalp_learning = update_scalp_learning(scalp_wallet, timestamp)

    latest_payload = {
        "generated_at": timestamp,
        "timeframe": "15m",
        "signals": signals,
        "health": {
            "assets_requested": len(holdings),
            "assets_analysed": len(signals),
            "unavailable_assets": unavailable,
            "fallback_assets": fallback_assets,
            "provider_counts": provider_counts,
            "new_history_events": new_events,
        },
    }
    write_json(LATEST, latest_payload)
    write_json(HISTORY, history[-50000:])
    write_json(WALLET, wallet)
    write_json(TIMING, timing)
    write_json(SCALP_WALLET, scalp_wallet)
    write_json(SCALP_CHECKPOINTS, scalp_checkpoints)
    write_json(SCALP_LEARNING, scalp_learning)

    health["observer_15m"] = {
        "generated_at": timestamp,
        "assets_analysed": len(signals),
        "unavailable_assets": unavailable,
        "fallback_assets": fallback_assets,
        "new_history_events": new_events,
        "wallet_equity": wallet.get("equity"),
        "wallet_previous_equity": wallet.get("previous_equity"),
        "wallet_change_this_run": wallet.get("equity_change_this_run"),
        "open_positions": len(wallet.get("open_positions") or []),
        "closed_positions": len(wallet.get("closed_positions") or []),
        "activity": wallet.get("activity"),
    }
    write_json(HEALTH, health)

    print("\n15-MINUTE OBSERVER")
    print(json.dumps({
        "generated_at": timestamp,
        "assets_requested": len(holdings),
        "assets_analysed": len(signals),
        "unavailable_assets": unavailable,
        "fallback_assets": fallback_assets,
        "new_history_events": new_events,
        "wallet_previous_equity": round(float(wallet.get("previous_equity") or 0), 2),
        "wallet_equity": round(float(wallet.get("equity") or 0), 2),
        "wallet_change_this_run": round(float(wallet.get("equity_change_this_run") or 0), 2),
        "open_positions": len(wallet.get("open_positions") or []),
        "closed_positions": len(wallet.get("closed_positions") or []),
        "activity": wallet.get("activity"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
