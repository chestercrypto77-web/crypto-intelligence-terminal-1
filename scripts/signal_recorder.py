from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import time

import numpy as np
import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BINANCE = "https://api.binance.com/api/v3/klines"
COINGECKO = "https://api.coingecko.com/api/v3"
ACTIONABLE = {"STRONG BUY", "BUY", "BUY WATCH", "SELL WATCH", "SELL", "STRONG SELL"}
DECISIVE = {"STRONG BUY", "BUY", "SELL", "STRONG SELL"}

TICKERS = {
    "BTC":"BTC-USD","SOL":"SOL-USD","AVAX":"AVAX-USD","POL":"POL28321-USD","DOT":"DOT-USD",
    "ZIL":"ZIL-USD","COTI":"COTI-USD","NEAR":"NEAR-USD","SUI":"SUI20947-USD",
    "SUPER":"SUPER8290-USD","S":"S-USD","AIOZ":"AIOZ-USD","FIL":"FIL-USD","SEI":"SEI-USD",
    "ONDO":"ONDO-USD","OM":"OM-USD","RUNE":"RUNE-USD","SAND":"SAND-USD","ONE":"ONE-USD",
    "WIN":"WIN-USD","AR":"AR-USD","BEAM":"BEAM-USD","SHIB":"SHIB-USD","ENJ":"ENJ-USD",
    "IMX":"IMX10603-USD","VET":"VET-USD","SC":"SC-USD","BTT":"BTT-USD","TLM":"TLM-USD",
    "PYR":"PYR-USD","PAAL":"PAAL-USD","SKL":"SKL-USD","AERO":"AERO29270-USD","LUNC":"LUNC-USD",
    "GALA":"GALA-USD","UOS":"UOS-USD","UFO":"UFO-USD","DENT":"DENT-USD","MEW":"MEW-USD",
    "DOGE":"DOGE-USD","GRT":"GRT-USD","VRA":"VRA-USD","VTHO":"VTHO-USD","XTZ":"XTZ-USD",
    "USDT":"USDT-USD",
}


def read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def yahoo4h(ticker):
    try:
        frame = yf.download(
            ticker, period="30d", interval="1h", auto_adjust=True,
            progress=False, threads=False
        )
        if frame is None or frame.empty:
            return pd.DataFrame()
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        columns = ["Open", "High", "Low", "Close", "Volume"]
        if not all(column in frame.columns for column in columns):
            return pd.DataFrame()
        frame = frame[columns].dropna(subset=["Close"]).copy()
        frame.index = pd.to_datetime(frame.index, utc=True)
        return frame.resample("4h").agg({
            "Open":"first", "High":"max", "Low":"min",
            "Close":"last", "Volume":"sum"
        }).dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()


def binance4h(symbol):
    try:
        response = requests.get(
            BINANCE,
            params={"symbol":f"{symbol}USDT", "interval":"4h", "limit":220},
            timeout=10,
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


def coingecko4h(coin_id):
    """Fallback market series using CoinGecko price and volume history by coin ID."""
    if not coin_id:
        return pd.DataFrame()
    try:
        response = requests.get(
            f"{COINGECKO}/coins/{coin_id}/market_chart",
            params={"vs_currency":"usd", "days":"30"},
            headers={"User-Agent":"CryptoIntelligenceTerminal/8.6.1"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        prices = payload.get("prices") or []
        volumes = payload.get("total_volumes") or []
        if len(prices) < 60:
            return pd.DataFrame()

        price_frame = pd.DataFrame(prices, columns=["timestamp", "Close"])
        price_frame["timestamp"] = pd.to_datetime(price_frame["timestamp"], unit="ms", utc=True)
        price_frame = price_frame.set_index("timestamp")
        volume_frame = pd.DataFrame(volumes, columns=["timestamp", "Volume"])
        volume_frame["timestamp"] = pd.to_datetime(volume_frame["timestamp"], unit="ms", utc=True)
        volume_frame = volume_frame.set_index("timestamp")

        frame = price_frame.join(volume_frame, how="left").sort_index()
        frame["Volume"] = frame["Volume"].ffill().fillna(0)
        frame["Open"] = frame["Close"].shift(1).fillna(frame["Close"])
        frame["High"] = frame[["Open", "Close"]].max(axis=1)
        frame["Low"] = frame[["Open", "Close"]].min(axis=1)
        return frame[["Open","High","Low","Close","Volume"]].resample("4h").agg({
            "Open":"first", "High":"max", "Low":"min",
            "Close":"last", "Volume":"last"
        }).dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()


def indicators(frame):
    values = frame.copy()
    close = values.Close.astype(float)
    high = values.High.astype(float)
    low = values.Low.astype(float)
    volume = values.Volume.fillna(0).astype(float)

    values["EMA9"] = close.ewm(span=9, adjust=False).mean()
    values["EMA21"] = close.ewm(span=21, adjust=False).mean()
    values["EMA55"] = close.ewm(span=55, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    relative_strength = (
        gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
        / loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean().replace(0, np.nan)
    )
    values["RSI"] = 100 - 100 / (1 + relative_strength)
    values["RSI_D"] = values.RSI - values.RSI.shift(3)

    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    histogram = macd - macd.ewm(span=9, adjust=False).mean()
    values["HIST"] = histogram
    values["HIST_D"] = histogram - histogram.shift(2)

    values["RVOL"] = volume / volume.rolling(20).mean().replace(0, np.nan)
    values["RVOL_D"] = values.RVOL - values.RVOL.shift(3)
    values["R1"] = close.pct_change() * 100
    values["R3"] = close.pct_change(3) * 100
    values["R6"] = close.pct_change(6) * 100
    values["G6"] = (close > values.Open).rolling(6).sum()
    values["D6"] = (close < values.Open).rolling(6).sum()
    values["PH"] = high.shift(1).rolling(6).max()
    values["PL"] = low.shift(1).rolling(6).min()
    values["BO"] = close > values.PH
    values["BD"] = close < values.PL
    values["HH"] = high.rolling(3).max() > high.shift(3).rolling(3).max()
    values["HL"] = low.rolling(3).min() > low.shift(3).rolling(3).min()
    values["LH"] = high.rolling(3).max() < high.shift(3).rolling(3).max()
    values["LL"] = low.rolling(3).min() < low.shift(3).rolling(3).min()
    return values


def evaluate(frame, btc24=0):
    values = indicators(frame).dropna(
        subset=["EMA9","EMA21","EMA55","RSI","HIST","RVOL","R3","R6"]
    )
    if values.empty:
        return None
    row = values.iloc[-1]
    close = float(row.Close)
    checks = [
        ("Price above EMA 9", close > row.EMA9, close < row.EMA9, "Trend"),
        ("EMA 9 above EMA 21", row.EMA9 > row.EMA21, row.EMA9 < row.EMA21, "Trend"),
        ("EMA 21 above EMA 55", row.EMA21 > row.EMA55, row.EMA21 < row.EMA55, "Trend"),
        ("MACD positive", row.HIST > 0, row.HIST < 0, "Momentum"),
        ("MACD accelerating", row.HIST_D > 0, row.HIST_D < 0, "Momentum"),
        ("RSI strengthening", 50 <= row.RSI <= 78 and row.RSI_D > 0, row.RSI < 45 and row.RSI_D < 0, "Momentum"),
        ("RVOL above normal", row.RVOL >= 1.15, row.RVOL < .70, "Volume"),
        ("RVOL increasing", row.RVOL_D > .10, row.RVOL_D < -.10, "Volume"),
        ("Most recent candles green", row.G6 >= 4, row.D6 >= 4, "Volume"),
        ("12-hour direction positive", row.R3 > 0, row.R3 < 0, "Structure"),
        ("Higher highs", bool(row.HH), bool(row.LH), "Structure"),
        ("Higher lows", bool(row.HL), bool(row.LL), "Structure"),
        ("Breakout", bool(row.BO), bool(row.BD), "Structure"),
        ("Outperforming Bitcoin", row.R6 > btc24 + 1, row.R6 < btc24 - 1, "Relative strength"),
    ]
    bullish = sum(bool(bull) for _, bull, _, _ in checks)
    bearish = sum(bool(bear) for _, _, bear, _ in checks)
    trend_bull = sum(bool(bull) for _, bull, _, group in checks if group == "Trend")
    trend_bear = sum(bool(bear) for _, _, bear, group in checks if group == "Trend")
    volume_bull = sum(bool(bull) for _, bull, _, group in checks if group == "Volume")
    volume_bear = sum(bool(bear) for _, _, bear, group in checks if group == "Volume")

    if bullish >= 10 and bearish <= 2 and trend_bull >= 2 and volume_bull >= 2:
        signal = "STRONG BUY"
    elif bullish >= 8 and bearish <= 3 and trend_bull >= 2:
        signal = "BUY"
    elif bullish >= 6 and bearish <= 4:
        signal = "BUY WATCH"
    elif bearish >= 10 and bullish <= 2 and trend_bear >= 2 and volume_bear >= 2:
        signal = "STRONG SELL"
    elif bearish >= 8 and bullish <= 3 and trend_bear >= 2:
        signal = "SELL"
    elif bearish >= 6 and bullish <= 4:
        signal = "SELL WATCH"
    else:
        signal = "HOLD"

    candle_time = pd.Timestamp(values.index[-1])
    candle_time = (
        candle_time.tz_localize("UTC")
        if candle_time.tzinfo is None
        else candle_time.tz_convert("UTC")
    )
    return {
        "signal":signal,
        "bullish":bullish,
        "bearish":bearish,
        "entry_price":close,
        "return_4h":float(row.R1),
        "return_12h":float(row.R3),
        "return_24h":float(row.R6),
        "rvol":float(row.RVOL),
        "rvol_delta":float(row.RVOL_D),
        "rsi":float(row.RSI),
        "checks":[
            {
                "name":name,
                "group":group,
                "state":"bull" if bull else "bear" if bear else "neutral",
            }
            for name, bull, bear, group in checks
        ],
        "candle_time":candle_time.isoformat(),
    }


def source(symbol, ticker, coin_id):
    choices = []
    yahoo = yahoo4h(ticker)
    if not yahoo.empty:
        choices.append(("Yahoo Finance", yahoo, False))
    binance = binance4h(symbol)
    if not binance.empty:
        choices.append(("Binance", binance, False))
    if not choices:
        fallback = coingecko4h(coin_id)
        if not fallback.empty:
            choices.append(("CoinGecko fallback", fallback, True))
    if not choices:
        return "", pd.DataFrame(), False
    choices.sort(key=lambda value: pd.Timestamp(value[1].index[-1]), reverse=True)
    return choices[0]


def signal_id(symbol, signal, candle):
    cleaned = candle.replace("-", "").replace(":", "").replace("+", "").replace("T", "_")
    return f"{symbol}_{signal.replace(' ', '_')}_{cleaned}"


def parse_time(value):
    try:
        timestamp = pd.Timestamp(value)
        return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
    except Exception:
        return None


def directional_return(direction, entry, current):
    if not entry or not current or float(entry) <= 0:
        return None
    raw = (float(current) / float(entry) - 1) * 100
    return raw if direction == "LONG" else -raw


def close_engine_trades_for_signal(trades, symbol, current_signal, current_price, now):
    closed = 0
    direction_now = "LONG" if "BUY" in current_signal else "SHORT" if "SELL" in current_signal else None
    for trade in trades:
        if (
            trade.get("source") != "OUR ENGINE"
            or trade.get("status") != "OPEN"
            or str(trade.get("symbol", "")).upper() != symbol
        ):
            continue
        reverse = direction_now is not None and trade.get("direction") != direction_now
        neutral = current_signal == "HOLD"
        if reverse or neutral:
            result = directional_return(trade.get("direction"), trade.get("entry_price"), current_price)
            trade["status"] = "CLOSED"
            trade["exit_time"] = now
            trade["exit_price"] = current_price
            trade["exit_reason"] = "Signal reversal" if reverse else "Signal returned to HOLD"
            trade["final_return"] = result
            trade["current_return"] = result
            trade["outcome"] = "WIN" if result is not None and result > .25 else "LOSS" if result is not None and result < -.25 else "FLAT"
            closed += 1
    return closed


def has_equivalent_open_trade(trades, symbol, direction):
    return any(
        trade.get("source") == "OUR ENGINE"
        and trade.get("status") == "OPEN"
        and str(trade.get("symbol", "")).upper() == symbol
        and trade.get("direction") == direction
        for trade in trades
    )


def update_trade_outcomes(trades, snapshots, now):
    now_timestamp = parse_time(now)
    checkpoints = [1, 4, 12, 24, 72, 168]
    for trade in trades:
        if trade.get("status") not in {"OPEN", "CLOSED"}:
            continue
        snapshot = snapshots.get(str(trade.get("symbol", "")).upper())
        if not snapshot:
            continue
        current = float(snapshot.get("price") or 0)
        entry = float(trade.get("entry_price") or 0)
        result = directional_return(trade.get("direction"), entry, current)
        if result is None:
            continue

        trade["current_price"] = current
        trade["current_return"] = result
        trade["last_updated"] = now
        trade["best_return"] = max(float(trade.get("best_return") or result), result)
        trade["worst_return"] = min(float(trade.get("worst_return") or result), result)
        trade.setdefault("returns", {})

        entered = parse_time(trade.get("entry_time"))
        if entered is None or now_timestamp is None:
            continue
        elapsed = max(0.0, (now_timestamp - entered).total_seconds() / 3600)
        trade["hours_open"] = elapsed
        for hours in checkpoints:
            key = f"{hours}h" if hours < 24 else f"{hours // 24}d"
            if elapsed >= hours and key not in trade["returns"]:
                trade["returns"][key] = {
                    "return":result,
                    "price":current,
                    "recorded_at":now,
                }
        if trade.get("status") == "OPEN" and elapsed >= 168:
            trade["status"] = "CLOSED"
            trade["exit_time"] = now
            trade["exit_price"] = current
            trade["exit_reason"] = "Automatic 7-day evaluation"
            trade["final_return"] = result
            trade["outcome"] = "WIN" if result > .25 else "LOSS" if result < -.25 else "FLAT"
    return trades


def ingest_external_calls(calls, trades, snapshots, now):
    existing = {str(trade.get("trade_id")) for trade in trades}
    added = 0
    for call in calls:
        if not isinstance(call, dict) or call.get("status", "ACTIVE") != "ACTIVE":
            continue
        call_id = str(call.get("call_id") or "").strip()
        symbol = str(call.get("symbol") or "").upper().strip()
        direction = str(call.get("direction") or "").upper().strip()
        if not call_id or not symbol or direction not in {"LONG", "SHORT"}:
            continue
        trade_id = f"EXTERNAL_{call_id}"
        if trade_id in existing:
            continue
        entry = float(call.get("entry_price") or snapshots.get(symbol, {}).get("price") or 0)
        if entry <= 0:
            continue
        trades.append({
            "trade_id":trade_id,
            "source":str(call.get("source") or "EXTERNAL"),
            "symbol":symbol,
            "name":str(call.get("name") or symbol),
            "narrative":str(call.get("narrative") or ""),
            "tier":"EXTERNAL",
            "direction":direction,
            "call":str(call.get("call") or ("BUY" if direction == "LONG" else "SELL")),
            "entry_time":str(call.get("entry_time") or now),
            "candle_time":str(call.get("entry_time") or now),
            "entry_price":entry,
            "status":"OPEN",
            "target_price":call.get("target_price"),
            "invalidation_price":call.get("invalidation_price"),
            "exit_time":None,
            "exit_price":None,
            "exit_reason":None,
            "bullish_conditions":None,
            "bearish_conditions":None,
            "checks":[],
            "source_data":str(call.get("source_link") or "Manual external call"),
            "notes":str(call.get("notes") or ""),
            "timeframe":str(call.get("timeframe") or ""),
            "returns":{},
            "best_return":0.0,
            "worst_return":0.0,
        })
        existing.add(trade_id)
        added += 1
    return added


def main():
    holdings = read(ROOT / "holdings.json", [])
    previous = read(DATA / "signals_latest.json", {"signals":[]})
    previous_by_symbol = {item.get("symbol"):item for item in previous.get("signals", [])}
    history = read(DATA / "signal_history.json", [])
    trades = read(DATA / "paper_trades.json", [])
    external_calls = read(DATA / "external_calls.json", [])
    external_status = read(DATA / "external_monitor_status.json", {})

    history = history if isinstance(history, list) else []
    trades = trades if isinstance(trades, list) else []
    external_calls = external_calls if isinstance(external_calls, list) else []
    seen_history = {item.get("signal_id") for item in history}

    bitcoin_holding = next((item for item in holdings if str(item.get("symbol")).upper() == "BTC"), {})
    _, bitcoin_frame, _ = source("BTC", TICKERS["BTC"], bitcoin_holding.get("coin_id"))
    bitcoin_evaluation = evaluate(bitcoin_frame, 0) if not bitcoin_frame.empty else None
    bitcoin_24h = bitcoin_evaluation["return_24h"] if bitcoin_evaluation else 0

    now = datetime.now(timezone.utc).isoformat()
    latest = []
    snapshots = {}
    unavailable = []
    fallback_assets = []
    provider_counts = {}
    new_history = 0
    new_trades = 0
    closed_trades = 0
    duplicate_trades_prevented = 0

    for holding in holdings:
        symbol = str(holding["symbol"]).upper()
        provider, frame, used_fallback = source(
            symbol,
            TICKERS.get(symbol, f"{symbol}-USD"),
            holding.get("coin_id"),
        )
        if frame.empty:
            unavailable.append(symbol)
            continue
        if used_fallback:
            fallback_assets.append(symbol)
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

        result = evaluate(frame, 0 if symbol == "BTC" else bitcoin_24h)
        if not result:
            unavailable.append(symbol)
            continue

        snapshots[symbol] = {
            "price":result["entry_price"],
            "source":provider,
            "recorded_at":now,
        }
        old_signal = previous_by_symbol.get(symbol, {}).get("signal")
        changed = old_signal is not None and old_signal != result["signal"]
        record = {
            "signal_id":signal_id(symbol, result["signal"], result["candle_time"]),
            "recorded_at":now,
            "symbol":symbol,
            "name":holding.get("name", symbol),
            "narrative":holding.get("narrative", ""),
            "tier":holding.get("tier", ""),
            "previous_signal":old_signal,
            "changed":changed,
            "data_source":provider,
            **result,
        }
        latest.append(record)

        if record["signal_id"] not in seen_history:
            history.append(record)
            seen_history.add(record["signal_id"])
            new_history += 1

        closed_trades += close_engine_trades_for_signal(
            trades, symbol, result["signal"], result["entry_price"], now
        )

        if result["signal"] in ACTIONABLE and result["signal"] != old_signal:
            direction = "LONG" if "BUY" in result["signal"] else "SHORT"
            if has_equivalent_open_trade(trades, symbol, direction):
                duplicate_trades_prevented += 1
            else:
                trades.append({
                    "trade_id":record["signal_id"],
                    "source":"OUR ENGINE",
                    "symbol":symbol,
                    "name":record["name"],
                    "narrative":record["narrative"],
                    "tier":record["tier"],
                    "direction":direction,
                    "call":result["signal"],
                    "entry_time":now,
                    "candle_time":result["candle_time"],
                    "entry_price":result["entry_price"],
                    "status":"OPEN",
                    "target_price":None,
                    "invalidation_price":None,
                    "exit_time":None,
                    "exit_price":None,
                    "exit_reason":None,
                    "bullish_conditions":result["bullish"],
                    "bearish_conditions":result["bearish"],
                    "checks":result["checks"],
                    "source_data":provider,
                    "returns":{},
                    "best_return":0.0,
                    "worst_return":0.0,
                })
                new_trades += 1
        time.sleep(.08)

    external_added = ingest_external_calls(external_calls, trades, snapshots, now)
    trades = update_trade_outcomes(trades, snapshots, now)

    health = {
        "generated_at":now,
        "overall_status":"PASS" if latest else "FAIL",
        "market_data":{
            "holdings_requested":len(holdings),
            "assets_analysed":len(latest),
            "fallback_successes":len(fallback_assets),
            "fallback_assets":fallback_assets,
            "unavailable_count":len(unavailable),
            "unavailable_assets":unavailable,
            "provider_counts":provider_counts,
        },
        "signals":{
            "current_signals":len(latest),
            "new_history_records":new_history,
            "signal_changes":sum(1 for item in latest if item.get("changed")),
        },
        "paper_trading":{
            "new_engine_trades":new_trades,
            "new_external_trades":external_added,
            "engine_trades_closed":closed_trades,
            "equivalent_duplicates_prevented":duplicate_trades_prevented,
            "open_engine_trades":sum(
                1 for trade in trades
                if trade.get("source") == "OUR ENGINE" and trade.get("status") == "OPEN"
            ),
            "total_trades":len(trades),
        },
        "external_intelligence":{
            "new_items":external_status.get("new_items", 0),
            "total_inbox":external_status.get("total_inbox", 0),
            "errors":external_status.get("errors", []),
            "sources":external_status.get("sources", []),
        },
        "research_wallet":{},
        "warnings":(
            ([f"Unavailable market data: {', '.join(unavailable)}"] if unavailable else [])
            + ([f"External source errors: {len(external_status.get('errors', []))}"] if external_status.get("errors") else [])
        ),
    }

    write(DATA / "signals_latest.json", {
        "generated_at":now,
        "scan_frequency":"hourly",
        "signal_timeframe":"4h",
        "btc_reference_return_24h":bitcoin_24h,
        "signals":latest,
        "new_history_records":new_history,
        "new_paper_trades":new_trades,
    })
    write(DATA / "signal_history.json", history[-20000:])
    write(DATA / "paper_trades.json", trades)
    write(DATA / "engine_health.json", health)

    print(json.dumps({
        "signals":len(latest),
        "new_history":new_history,
        "new_trades":new_trades,
        "closed_trades":closed_trades,
        "duplicates_prevented":duplicate_trades_prevented,
        "fallback_assets":fallback_assets,
        "unavailable_assets":unavailable,
    }, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
