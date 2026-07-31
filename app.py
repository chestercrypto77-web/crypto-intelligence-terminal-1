from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import json
import html
import math

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf


APP_NAME = "Crypto Intelligence Terminal"
APP_VERSION = "5.4.0"
CURRENCY = "aud"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

HOLDINGS_FILE = Path(__file__).with_name("holdings.json")


def load_holdings() -> list[dict]:
    try:
        data = json.loads(HOLDINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            raise ValueError("holdings.json must contain a non-empty list")
        required = {"symbol", "name", "coin_id", "tokens", "tier", "narrative", "conviction"}
        for item in data:
            if not required.issubset(item):
                raise ValueError(f"Missing fields for {item.get('symbol', 'unknown asset')}")
        return data
    except Exception as exc:
        st.error(f"Could not load holdings.json: {exc}")
        st.stop()


PORTFOLIO = load_holdings()

CRYPTO_TICKERS = {
    "BTC":"BTC-USD","SOL":"SOL-USD","AVAX":"AVAX-USD","POL":"POL-USD","DOT":"DOT-USD",
    "ZIL":"ZIL-USD","COTI":"COTI-USD","NEAR":"NEAR-USD","SUI":"SUI20947-USD",
    "SUPER":"SUPER-USD","S":"S-USD","AIOZ":"AIOZ-USD","FIL":"FIL-USD","SEI":"SEI-USD",
    "ONDO":"ONDO-USD",
    "OM":"OM-USD",
    "RUNE":"RUNE-USD",
    "SAND":"SAND-USD",
    "ONE":"ONE-USD",
    "WIN":"WIN-USD",
    "AR":"AR-USD",
    "BEAM":"BEAM-USD",
    "SHIB":"SHIB-USD",
    "ENJ":"ENJ-USD",
    "IMX":"IMX-USD",
    "VET":"VET-USD",
    "SC":"SC-USD",
    "BTT":"BTT-USD",
    "TLM":"TLM-USD",
    "PYR":"PYR-USD",
    "PAAL":"PAAL-USD",
    "SKL":"SKL-USD",
    "AERO":"AERO-USD",
    "LUNC":"LUNC-USD",
    "GALA":"GALA-USD",
    "UOS":"UOS-USD",
    "UFO":"UFO-USD",
    "DENT":"DENT-USD",
    "MEW":"MEW-USD",
    "DOGE":"DOGE-USD",
    "GRT":"GRT-USD",
    "VRA":"VRA-USD",
    "VTHO":"VTHO-USD",
    "XTZ":"XTZ-USD",
    "USDT":"USDT-USD",
}

FALLBACK = {
    "bitcoin":(178500.0,1.4,3.8,58200000000),"solana":(285.0,3.2,8.1,8200000000),
    "avalanche-2":(42.0,-0.8,2.4,590000000),"polygon-ecosystem-token":(0.42,1.1,-1.5,210000000),
    "polkadot":(5.40,-0.4,1.8,185000000),"zilliqa":(0.016,-1.9,-4.3,11000000),
    "coti":(0.091,8.4,16.0,38400000),"near":(4.15,2.6,6.2,240000000),
    "sui":(5.05,5.3,12.4,1680000000),"superfarm":(0.84,1.8,4.6,24000000),
    "sonic-3":(0.54,3.1,7.0,92000000),"aioz-network":(0.69,4.5,10.2,31000000),
    "filecoin":(3.75,-0.7,0.8,145000000),"sei-network":(0.36,2.0,5.1,118000000),
}

CSS = """
<style>
:root{--bg:#15181d;--panel:#20242b;--panel2:#262b33;--line:#363d47;--text:#f4f6f8;--muted:#98a2ad;--blue:#63a4ff;--green:#53d38a;--red:#ff7272;--amber:#f3c765}
.stApp{background:var(--bg);color:var(--text)}
[data-testid="stSidebar"]{background:#191d23;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:#e9edf2!important}
.block-container{max-width:1450px;padding-top:1.4rem;padding-bottom:3rem}
.desk-kicker{color:var(--blue);font-size:.72rem;letter-spacing:.18em;font-weight:800;text-transform:uppercase}
.desk-title{font-size:2.15rem;font-weight:760;margin:.18rem 0 .25rem}
.desk-subtitle{color:var(--muted);margin-bottom:1.3rem}
.section-title{color:#dce3eb;font-size:.77rem;letter-spacing:.14em;font-weight:800;text-transform:uppercase;margin:1.5rem 0 .65rem}
.brief-card,.metric-card,.asset-card,.attention-card,.future-card,.signal-card{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);border-radius:14px;padding:1rem 1.05rem;box-shadow:0 7px 20px rgba(0,0,0,.14);height:100%}
.metric-label{color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.09em}
.metric-value{color:var(--text);font-size:1.72rem;font-weight:760;margin:.22rem 0 .12rem}
.metric-note{color:var(--muted);font-size:.82rem}
.asset-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem}
.asset-symbol{font-size:1.18rem;font-weight:800}.asset-name{color:var(--muted);font-size:.76rem}
.score{font-size:1.15rem;font-weight:800;color:var(--blue)}
.data-row{display:flex;justify-content:space-between;gap:1rem;border-top:1px solid rgba(255,255,255,.065);padding:.42rem 0;font-size:.85rem}
.data-row span:first-child{color:var(--muted)}.positive{color:var(--green);font-weight:700}.negative{color:var(--red);font-weight:700}.neutral{color:#dce3eb;font-weight:700}
.badge{display:inline-block;border:1px solid var(--line);background:#1a1e24;border-radius:999px;padding:.17rem .48rem;font-size:.69rem;color:#dce3eb}
.badge-green{border-color:#315c46;color:#8ce8ae}.badge-red{border-color:#6a3838;color:#ff9b9b}.badge-amber{border-color:#695d36;color:#f5d882}
.summary-box{background:#1b1f25;border-left:3px solid var(--blue);border-radius:9px;padding:.85rem 1rem;color:#dce3eb;line-height:1.55}
.small-muted{color:var(--muted);font-size:.78rem}
.progress-track{background:#171a1f;border-radius:999px;height:7px;overflow:hidden;margin:.45rem 0}
.progress-fill{background:linear-gradient(90deg,#63a4ff,#8fc1ff);height:100%;border-radius:999px}
div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden}

.signal-hero{border-radius:16px;padding:1.2rem 1.25rem;border:1px solid var(--line);margin-bottom:1rem}
.signal-hero.green{background:linear-gradient(135deg,#173524,#1f4930);border-color:#3d7c54}
.signal-hero.blue{background:linear-gradient(135deg,#182d46,#21466b);border-color:#4b79a9}
.signal-hero.yellow{background:linear-gradient(135deg,#403814,#5a4e1b);border-color:#8b7a2e}
.signal-hero.orange{background:linear-gradient(135deg,#4b2e18,#653b1f);border-color:#975e35}
.signal-hero.red{background:linear-gradient(135deg,#431d22,#60272f);border-color:#94424e}
.signal-label{font-size:.76rem;text-transform:uppercase;letter-spacing:.12em;font-weight:800;opacity:.82}
.signal-main{font-size:1.8rem;font-weight:850;margin:.18rem 0}
.signal-score{font-size:2.7rem;font-weight:900;line-height:1}
.signal-caption{font-size:.84rem;opacity:.86;margin-top:.35rem}
.score-key{display:grid;grid-template-columns:repeat(5,1fr);gap:.5rem}
.score-key div{border-radius:10px;padding:.65rem;text-align:center;border:1px solid var(--line);font-size:.76rem}
.score-green{background:#173524}.score-blue{background:#182d46}.score-yellow{background:#403814}.score-orange{background:#4b2e18}.score-red{background:#431d22}
.explain-card{background:#1b1f25;border:1px solid var(--line);border-radius:12px;padding:.9rem 1rem;margin:.45rem 0}
.explain-title{font-weight:800}.explain-meaning{color:var(--muted);font-size:.82rem;margin-top:.28rem;line-height:1.45}
.component-score{display:flex;justify-content:space-between;align-items:center;margin:.4rem 0;padding:.55rem .65rem;background:#1a1e24;border-radius:9px}

.rank-row{display:grid;grid-template-columns:42px 1.4fr .8fr .8fr .8fr 1.2fr;gap:.55rem;align-items:center;
background:#1b1f25;border:1px solid var(--line);border-radius:10px;padding:.58rem .7rem;margin:.34rem 0;font-size:.82rem}
.rank-num{font-size:1rem;font-weight:850;color:var(--blue)}
.rank-name{font-weight:800}.rank-sub{color:var(--muted);font-size:.72rem}
.change-pill{border-radius:999px;padding:.18rem .42rem;text-align:center;font-weight:750}
.change-pill.pos{background:#173524;color:#8ce8ae}.change-pill.neg{background:#431d22;color:#ff9b9b}
.change-pill.mix{background:#403814;color:#f5d882}
</style>


"""


def esc(value) -> str:
    return html.escape(str(value))


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def signed(value: float) -> str:
    arrow = "▲" if value > 0 else "▼" if value < 0 else "—"
    return f"{arrow} {value:+.2f}%" if value else "— 0.00%"


def money(value: float, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{esc(title)}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="desk-kicker">Personal Intelligence Desk</div>'
        f'<div class="desk-title">{esc(title)}</div>'
        f'<div class="desk-subtitle">{esc(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def metric(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{esc(label)}</div>'
        f'<div class="metric-value">{esc(value)}</div>'
        f'<div class="metric-note">{esc(note)}</div></div>',
        unsafe_allow_html=True,
    )


def progress(label: str, value: float, note: str = "") -> None:
    width = clamp(value)
    st.markdown(
        f'<div class="brief-card"><div class="asset-head"><b>{esc(label)}</b><b>{value:.0f}</b></div>'
        f'<div class="progress-track"><div class="progress-fill" style="width:{width}%"></div></div>'
        f'<div class="small-muted">{esc(note)}</div></div>',
        unsafe_allow_html=True,
    )


def asset_card(item: dict) -> None:
    cls24 = "positive" if item["change_24h"] > 0 else "negative" if item["change_24h"] < 0 else "neutral"
    cls7 = "positive" if item["change_7d"] > 0 else "negative" if item["change_7d"] < 0 else "neutral"
    st.markdown(
        '<div class="asset-card">'
        f'<div class="asset-head"><div><div class="asset-symbol">{esc(item["symbol"])}</div>'
        f'<div class="asset-name">{esc(item["name"])}</div></div><div class="score">{item["score"]:.0f}</div></div>'
        f'<div class="data-row"><span>Value</span><b>{money(item["value"])}</b></div>'
        f'<div class="data-row"><span>Weight</span><b>{item["weight"]:.1f}%</b></div>'
        f'<div class="data-row"><span>24h</span><span class="{cls24}">{signed(item["change_24h"])}</span></div>'
        f'<div class="data-row"><span>7 day</span><span class="{cls7}">{signed(item["change_7d"])}</span></div>'
        f'<div class="data-row"><span>Momentum</span><b>{esc(item["momentum"])}</b></div>'
        f'<div class="data-row"><span>Volume</span><b>{esc(item["volume_label"])} · {item["rvol"]:.2f}×</b></div>'
        f'<div class="data-row"><span>Risk</span><span class="badge">{esc(item["risk"])}</span></div>'
        f'<div class="data-row"><span>Action</span><b>{esc(item["action"])}</b></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def intelligence_card(item: dict, score_key: str, title: str) -> None:
    score = float(item[score_key])
    _, colour, _ = score_band(score)
    st.markdown(
        f'<div class="signal-hero {colour}" style="padding:.9rem 1rem">'
        f'<div class="signal-label">{esc(title)} · {esc(item.get("tier", ""))}</div>'
        f'<div class="asset-head"><div><div class="asset-symbol">{esc(item["symbol"])}</div>'
        f'<div class="asset-name">{esc(item["signal_label"])}</div></div>'
        f'<div class="signal-score" style="font-size:2rem">{score:.0f}</div></div>'
        f'<div class="signal-caption">{esc(item["momentum"])} · {item["rvol"]:.2f}× volume · '
        f'{item["weight"]:.1f}% portfolio weight</div></div>',
        unsafe_allow_html=True,
    )


def attention_card(item: dict) -> None:
    reason = f"Participation is {item['volume_label'].lower()} at {item['rvol']:.2f}× while 24-hour price is {signed(item['change_24h'])}."
    st.markdown(
        '<div class="attention-card">'
        f'<div class="asset-head"><div><div class="asset-symbol">{esc(item["symbol"])}</div>'
        f'<div class="asset-name">{esc(item["narrative"])}</div></div><span class="badge">{esc(item["action"])}</span></div>'
        f'<div class="data-row"><span>Momentum</span><b>{esc(item["momentum"])}</b></div>'
        f'<div class="data-row"><span>Market strength</span><b>{item["score"]:.0f}/100</b></div>'
        f'<div class="small-muted" style="margin-top:.7rem">{esc(reason)}</div></div>',
        unsafe_allow_html=True,
    )



def score_band(score: float) -> tuple[str, str, str]:
    if score >= 80:
        return "STRONG SETUP", "green", "Broad positive agreement. Investigate promptly, but still confirm fundamentals and risk."
    if score >= 65:
        return "BUY WATCH", "blue", "Positive evidence is building. Worth deeper investigation before acting."
    if score >= 50:
        return "NEUTRAL / MIXED", "yellow", "Evidence is balanced or incomplete. Wait for confirmation."
    if score >= 35:
        return "RISK INCREASING", "orange", "The setup is weakening. Review what has changed and watch risk."
    return "DEFENSIVE REVIEW", "red", "Several indicators are negative. Prioritise capital protection and investigation."


def render_score_key() -> None:
    st.markdown(
        '<div class="score-key">'
        '<div class="score-green"><b>80–100</b><br>Possible buy</div>'
        '<div class="score-blue"><b>65–79</b><br>Buy watch</div>'
        '<div class="score-yellow"><b>50–64</b><br>Mixed</div>'
        '<div class="score-orange"><b>35–49</b><br>Sell watch</div>'
        '<div class="score-red"><b>0–34</b><br>Sell review</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_signal_hero(score: float, label: str, confidence: str) -> None:
    _, colour, meaning = score_band(score)
    st.markdown(
        f'<div class="signal-hero {colour}">'
        '<div class="signal-label">Current research signal</div>'
        f'<div class="signal-main">{esc(label)}</div>'
        f'<div class="signal-score">{score:.0f}<span style="font-size:1rem">/100</span></div>'
        f'<div class="signal-caption">Confidence: <b>{esc(confidence)}</b> · {esc(meaning)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_indicator_explanation(name: str, value: str, status: str, meaning: str, colour: str = "neutral") -> None:
    css_class = "positive" if colour == "positive" else "negative" if colour == "negative" else "neutral"
    st.markdown(
        f'<div class="explain-card"><div class="asset-head">'
        f'<div class="explain-title">{esc(name)}</div><span class="{css_class}">{esc(value)} · {esc(status)}</span>'
        f'</div><div class="explain-meaning">{esc(meaning)}</div></div>',
        unsafe_allow_html=True,
    )


def render_component_breakdown(components: dict[str, float]) -> None:
    for name, value in components.items():
        st.markdown(
            f'<div class="component-score"><span>{esc(name)}</span><b>{value:.0f}/100</b></div>',
            unsafe_allow_html=True,
        )


def fallback_rows() -> list[dict]:
    rows = []
    for holding in PORTFOLIO:
        price, ch24, ch7, volume = FALLBACK.get(holding["coin_id"], (0.0, 0.0, 0.0, 0.0))
        rows.append({"id":holding["coin_id"],"current_price":price,"price_change_percentage_24h":ch24,
                     "price_change_percentage_7d_in_currency":ch7,"total_volume":volume,
                     "market_cap":price*10_000_000})
    return rows


@st.cache_data(ttl=300, show_spinner=False)
def get_market_rows():
    params = {"vs_currency":CURRENCY,"ids":",".join(x["coin_id"] for x in PORTFOLIO),
              "price_change_percentage":"1h,24h,7d","sparkline":"false"}
    try:
        r = requests.get(COINGECKO_URL, params=params, timeout=15,
                         headers={"User-Agent":"Crypto-Intelligence-Terminal/4.3"})
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list) or len(rows) < 7:
            raise RuntimeError("Incomplete market response")
        return rows, "Live CoinGecko"
    except Exception:
        return fallback_rows(), "Snapshot fallback"


def build_portfolio(rows: list[dict]) -> dict:
    row_map = {str(row.get("id")): row for row in rows}
    items, total = [], 0.0
    for holding in PORTFOLIO:
        row = row_map.get(holding["coin_id"], {})
        price = float(row.get("current_price") or 0)
        ch24 = float(row.get("price_change_percentage_24h") or 0)
        ch7 = float(row.get("price_change_percentage_7d_in_currency") or ch24)
        volume = float(row.get("total_volume") or 0)
        market_cap = float(row.get("market_cap") or 1)
        rvol = clamp(.70 + (volume/max(market_cap,1))*8 + abs(ch24)/25, .35, 3.0)
        value = price * float(holding["tokens"])
        total += value
        momentum_score = clamp(50 + ch24*3.1 + ch7*1.25)
        volume_score = clamp(35 + rvol*29)
        risk_score = clamp(58 - holding["conviction"]*.30 + abs(ch24)*1.8)
        risk = "HIGH" if risk_score >= 68 else "MEDIUM" if risk_score >= 42 else "LOW"
        score = clamp(momentum_score*.34 + volume_score*.27 + holding["conviction"]*.25 + (100-risk_score)*.14)
        contribution = value*ch24/(100+ch24) if ch24 > -99 else 0
        m = ch24*.55 + ch7*.45
        momentum = "Accelerating" if m>=7 else "Building" if m>=2 else "Breaking down" if m<=-7 else "Weakening" if m<=-2 else "Stable"
        volume_label = "Extreme" if rvol>=2.2 else "High" if rvol>=1.5 else "Elevated" if rvol>=1.15 else "Quiet" if rvol<.7 else "Normal"
        action = "Review" if risk=="HIGH" or score<55 else "Watch closely" if score>=78 else "Hold"
        tier_multiplier = {"Core": 1.0, "Secondary": 0.72, "Legacy": 0.38}.get(holding.get("tier"), 0.5)
        shift_strength = clamp(abs(ch24) * 4 + abs(ch7) * 1.5 + rvol * 18)
        attention_score = clamp(
            score * 0.28
            + shift_strength * 0.32
            + holding["conviction"] * 0.18
            + tier_multiplier * 22
        )
        opportunity_score = clamp(
            momentum_score * 0.36
            + volume_score * 0.27
            + holding["conviction"] * 0.22
            + (100 - risk_score) * 0.15
        )
        signal_label = (
            "POSSIBLE BUY / STRONG WATCH" if score >= 80 else
            "WATCHING / BUY SETUP FORMING" if score >= 65 else
            "HOLD / MIXED" if score >= 50 else
            "DECLINING / POSSIBLE SELL WATCH" if score >= 35 else
            "DEFENSIVE / SELL REVIEW"
        )
        items.append({**holding,"price":price,"value":value,"change_24h":ch24,"change_7d":ch7,
                      "volume":volume,"rvol":rvol,"momentum":momentum,"momentum_score":momentum_score,
                      "volume_score":volume_score,"risk_score":risk_score,"risk":risk,"score":score,
                      "attention_score":attention_score,"opportunity_score":opportunity_score,
                      "signal_label":signal_label,"contribution":contribution,
                      "volume_label":volume_label,"action":action})
    for item in items:
        item["weight"] = item["value"]/total*100 if total else 0
    daily_change = sum(x["contribution"] for x in items)
    previous_total = total-daily_change
    daily_pct = daily_change/previous_total*100 if previous_total else 0
    weighted_score = sum(x["score"]*x["weight"] for x in items)/100 if total else 0
    weighted_risk = sum(x["risk_score"]*x["weight"] for x in items)/100 if total else 0
    health = clamp(weighted_score*.70 + (100-weighted_risk)*.30)
    narratives = defaultdict(lambda:{"value":0.0,"weighted_change":0.0})
    for item in items:
        for n in [x.strip() for x in item["narrative"].split("/")]:
            narratives[n]["value"] += item["value"]
            narratives[n]["weighted_change"] += item["value"]*item["change_24h"]
    themes = []
    for name,data in narratives.items():
        change = data["weighted_change"]/data["value"] if data["value"] else 0
        themes.append({"name":name,"value":data["value"],"change":change,"strength":clamp(50+change*5)})
    themes.sort(key=lambda x:x["strength"], reverse=True)
    items.sort(key=lambda x:x["value"], reverse=True)
    attention = sorted(items, key=lambda x:x["attention_score"], reverse=True)[:6]
    opportunities = sorted(items, key=lambda x:x["opportunity_score"], reverse=True)[:6]
    concentration = sum(x["weight"] ** 2 for x in items) / 100
    top5_weight = sum(x["weight"] for x in sorted(items, key=lambda x:x["weight"], reverse=True)[:5])
    tier_values = defaultdict(float)
    for item in items:
        tier_values[item.get("tier", "Other")] += item["value"]
    return {"items":items,"total":total,"daily_change":daily_change,"daily_pct":daily_pct,"health":health,
            "risk":"HIGH" if weighted_risk>=64 else "MEDIUM" if weighted_risk>=40 else "LOW",
            "themes":themes,"attention":attention,"opportunities":opportunities,
            "concentration":concentration,"top5_weight":top5_weight,"tier_values":dict(tier_values)}



def category_members(items: list[dict], category: str) -> list[dict]:
    aliases = {
        "RWA / Tokenisation": ["RWA", "Tokenisation", "Enterprise"],
        "AI": ["AI", "Data"],
        "DePIN / Storage": ["DePIN", "Storage", "Telecom"],
        "Layer 1": ["Layer 1", "Legacy Layer 1"],
        "Layer 2": ["Layer 2", "Scaling"],
        "DeFi / DEX": ["DeFi", "DEX", "Trading"],
        "Gaming": ["Gaming", "Metaverse"],
        "Interoperability": ["Interoperability", "Oracle"],
        "Privacy / Payments": ["Privacy", "Payments"],
        "Meme": ["Meme"],
    }
    terms = aliases.get(category, [category])
    matched = []
    for item in items:
        narrative = item.get("narrative", "")
        if any(term.lower() in narrative.lower() for term in terms):
            matched.append(item)
    return sorted(
        matched,
        key=lambda x: (
            x["opportunity_score"] * 0.45
            + x["score"] * 0.30
            + x["attention_score"] * 0.15
            + x["weight"] * 0.10
        ),
        reverse=True,
    )[:5]


def render_rank_row(rank: int, item: dict) -> None:
    change_class = "pos" if item["change_24h"] > 0 else "neg" if item["change_24h"] < 0 else "mix"
    st.markdown(
        f'<div class="rank-row">'
        f'<div class="rank-num">{rank}</div>'
        f'<div><div class="rank-name">{esc(item["symbol"])} · {esc(item["name"])}</div>'
        f'<div class="rank-sub">{esc(item["tier"])} · {esc(item["signal_label"])}</div></div>'
        f'<div><span class="change-pill {change_class}">{signed(item["change_24h"])}</span></div>'
        f'<div><b>{item["rvol"]:.2f}×</b><div class="rank-sub">RVOL</div></div>'
        f'<div><b>{item["opportunity_score"]:.0f}</b><div class="rank-sub">Opportunity</div></div>'
        f'<div><b>{esc(item["momentum"])}</b><div class="rank-sub">{item["weight"]:.1f}% portfolio</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def selected_portfolio_item(portfolio: dict, symbol: str) -> dict:
    return next(item for item in portfolio["items"] if item["symbol"] == symbol)


def research_summary(item: dict) -> str:
    if item["score"] >= 80:
        direction = "has broad positive agreement and deserves possible-buy investigation"
    elif item["score"] >= 65:
        direction = "is improving and belongs on the buy watchlist"
    elif item["score"] >= 50:
        direction = "has mixed evidence and currently supports a hold-and-monitor approach"
    elif item["score"] >= 35:
        direction = "is declining and deserves possible-sell monitoring"
    else:
        direction = "has broad negative agreement and deserves defensive review"
    return (
        f'{item["symbol"]} {direction}. Its portfolio weight is {item["weight"]:.1f}%, '
        f'relative volume is {item["rvol"]:.2f}×, and the current momentum state is '
        f'{item["momentum"].lower()}. Attention is {item["attention_score"]:.0f}/100 and '
        f'opportunity is {item["opportunity_score"]:.0f}/100.'
    )


def executive_brief(portfolio: dict) -> str:
    leaders = sorted(portfolio["items"],key=lambda x:x["contribution"],reverse=True)
    strongest = max(portfolio["items"],key=lambda x:x["score"])
    active = max(portfolio["items"],key=lambda x:x["rvol"])
    direction = "gained" if portfolio["daily_change"]>=0 else "declined"
    ending = "No urgent defensive action is indicated." if portfolio["risk"]!="HIGH" else "Review the highest-risk positions."
    return f"Your portfolio {direction} today. {leaders[0]['symbol']} and {leaders[1]['symbol']} are the largest positive contributors. {strongest['symbol']} has the strongest combined intelligence score, while {active['symbol']} shows the highest participation signal. Overall portfolio health is {portfolio['health']:.0f}/100 with {portfolio['risk'].lower()} risk. {ending}"


# ---------- Signal Lab calculations ----------

@st.cache_data(ttl=900, show_spinner=False)
def load_history(ticker: str, period: str) -> pd.DataFrame:
    frame = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
    if frame is None or frame.empty:
        return pd.DataFrame()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    needed = ["Open","High","Low","Close","Volume"]
    if not all(col in frame.columns for col in needed):
        return pd.DataFrame()
    frame = frame[needed].dropna(subset=["Close"]).copy()
    return frame


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close, high, low, volume = x["Close"], x["High"], x["Low"], x["Volume"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x["RSI"] = 100 - (100 / (1 + rs))

    x["EMA20"] = close.ewm(span=20, adjust=False).mean()
    x["EMA50"] = close.ewm(span=50, adjust=False).mean()
    x["EMA200"] = close.ewm(span=200, adjust=False).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["MACD_SIGNAL"] = x["MACD"].ewm(span=9, adjust=False).mean()
    x["MACD_HIST"] = x["MACD"] - x["MACD_SIGNAL"]

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    x["BB_MID"] = mid
    x["BB_UPPER"] = mid + 2*std
    x["BB_LOWER"] = mid - 2*std
    x["BB_POS"] = (close - x["BB_LOWER"]) / (x["BB_UPPER"] - x["BB_LOWER"]).replace(0,np.nan)

    prev_close = close.shift(1)
    tr = pd.concat([(high-low).abs(),(high-prev_close).abs(),(low-prev_close).abs()],axis=1).max(axis=1)
    x["ATR"] = tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x["ATR_PCT"] = x["ATR"]/close*100

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr14 = tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    plus_di = 100*(plus_dm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr14.replace(0,np.nan))
    minus_di = 100*(minus_dm.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr14.replace(0,np.nan))
    dx = 100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)
    x["ADX"] = dx.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    x["PLUS_DI"], x["MINUS_DI"] = plus_di, minus_di

    direction = np.sign(close.diff()).fillna(0)
    x["OBV"] = (direction*volume.fillna(0)).cumsum()
    x["OBV_EMA20"] = x["OBV"].ewm(span=20,adjust=False).mean()

    x["RVOL20"] = volume / volume.rolling(20).mean().replace(0,np.nan)
    x["RET5"] = close.pct_change(5)*100
    x["RET20"] = close.pct_change(20)*100
    return x



@st.cache_data(ttl=600, show_spinner=False)
def load_intraday_history(ticker: str, days: int = 30) -> pd.DataFrame:
    period = "1mo" if days <= 30 else "60d"
    frame = yf.download(ticker, period=period, interval="1h", auto_adjust=True, progress=False, threads=False)
    if frame is None or frame.empty:
        return pd.DataFrame()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    needed = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in frame.columns for col in needed):
        return pd.DataFrame()
    return frame[needed].dropna(subset=["Close"]).copy()


def add_short_shift_indicators(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    close = x["Close"]
    volume = x["Volume"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/9, adjust=False, min_periods=9).mean()
    avg_loss = loss.ewm(alpha=1/9, adjust=False, min_periods=9).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x["RSI9"] = 100 - (100 / (1 + rs))

    x["EMA9"] = close.ewm(span=9, adjust=False).mean()
    x["EMA21"] = close.ewm(span=21, adjust=False).mean()
    x["EMA55"] = close.ewm(span=55, adjust=False).mean()

    ema6 = close.ewm(span=6, adjust=False).mean()
    ema13 = close.ewm(span=13, adjust=False).mean()
    x["FAST_MACD"] = ema6 - ema13
    x["FAST_SIGNAL"] = x["FAST_MACD"].ewm(span=5, adjust=False).mean()
    x["FAST_HIST"] = x["FAST_MACD"] - x["FAST_SIGNAL"]

    x["RVOL20"] = volume / volume.rolling(20).mean().replace(0, np.nan)
    x["RET6H"] = close.pct_change(6) * 100
    x["RET24H"] = close.pct_change(24) * 100
    x["RET7D"] = close.pct_change(168) * 100
    x["RSI_DELTA6"] = x["RSI9"] - x["RSI9"].shift(6)
    x["RVOL_DELTA6"] = x["RVOL20"] - x["RVOL20"].shift(6)
    return x


def short_shift_result(df: pd.DataFrame) -> dict | None:
    valid = df.dropna(subset=["RSI9", "EMA21", "EMA55", "FAST_HIST", "RVOL20", "RET6H", "RET24H"])
    if valid.empty:
        return None

    row = valid.iloc[-1]
    close = float(row["Close"])
    score = 50.0
    evidence, cautions = [], []

    if close > row["EMA9"] > row["EMA21"]:
        score += 14
        evidence.append("Price is above the fast 9- and 21-hour trend.")
    elif close < row["EMA9"] < row["EMA21"]:
        score -= 14
        cautions.append("Price is below the fast 9- and 21-hour trend.")

    if row["EMA21"] > row["EMA55"]:
        score += 8
        evidence.append("The short trend is above the broader 55-hour trend.")
    else:
        score -= 8
        cautions.append("The short trend remains below the broader 55-hour trend.")

    if row["FAST_HIST"] > 0:
        score += 10
        evidence.append("Fast MACD momentum is positive.")
    else:
        score -= 10
        cautions.append("Fast MACD momentum is negative.")

    if 48 <= row["RSI9"] <= 72 and row["RSI_DELTA6"] > 0:
        score += 10
        evidence.append(f"RSI 9 is strengthening at {row['RSI9']:.1f}.")
    elif row["RSI9"] >= 78:
        score -= 5
        cautions.append(f"RSI 9 is stretched at {row['RSI9']:.1f}.")
    elif row["RSI9"] < 42:
        score -= 8
        cautions.append(f"RSI 9 remains weak at {row['RSI9']:.1f}.")

    if row["RVOL20"] >= 1.5:
        score += 10 if row["RET6H"] >= 0 else -7
        target = evidence if row["RET6H"] >= 0 else cautions
        target.append(f"Relative volume is elevated at {row['RVOL20']:.2f}×.")
    elif row["RVOL20"] < .70:
        score -= 3
        cautions.append("Participation remains below normal.")

    if row["RET6H"] > 0 and row["RET24H"] > 0:
        score += 8
        evidence.append("Both 6-hour and 24-hour returns are positive.")
    elif row["RET6H"] < 0 and row["RET24H"] < 0:
        score -= 8
        cautions.append("Both 6-hour and 24-hour returns are negative.")

    score = clamp(score)
    label = (
        "RAPID POSITIVE SHIFT" if score >= 80 else
        "EARLY POSITIVE SHIFT" if score >= 65 else
        "MIXED / FORMING" if score >= 50 else
        "SHORT-TERM WEAKENING" if score >= 35 else
        "RAPID NEGATIVE SHIFT"
    )

    return {
        "score": score,
        "label": label,
        "rsi": float(row["RSI9"]),
        "rsi_delta": float(row["RSI_DELTA6"]),
        "rvol": float(row["RVOL20"]),
        "rvol_delta": float(row["RVOL_DELTA6"]) if pd.notna(row["RVOL_DELTA6"]) else 0.0,
        "ret6": float(row["RET6H"]),
        "ret24": float(row["RET24H"]),
        "ret7d": float(row["RET7D"]) if pd.notna(row["RET7D"]) else np.nan,
        "evidence": evidence[:5],
        "cautions": cautions[:5],
        "chart": valid[["Close", "EMA9", "EMA21", "EMA55"]].tail(240),
    }


def signal_score_row(row: pd.Series, prev: pd.Series | None = None) -> dict:
    score = 50.0
    evidence, cautions = [], []

    close = float(row["Close"])
    ema20, ema50, ema200 = float(row["EMA20"]), float(row["EMA50"]), float(row["EMA200"])
    rsi = float(row["RSI"])
    macd_hist = float(row["MACD_HIST"])
    adx = float(row["ADX"])
    plus_di, minus_di = float(row["PLUS_DI"]), float(row["MINUS_DI"])
    rvol = float(row["RVOL20"]) if pd.notna(row["RVOL20"]) else 1.0
    bb_pos = float(row["BB_POS"]) if pd.notna(row["BB_POS"]) else .5
    obv = float(row["OBV"])
    obv_ema = float(row["OBV_EMA20"])

    if close > ema20 > ema50:
        score += 12; evidence.append("Price is above the 20- and 50-day trend.")
    elif close < ema20 < ema50:
        score -= 12; cautions.append("Price is below the 20- and 50-day trend.")

    if pd.notna(ema200):
        if close > ema200:
            score += 7; evidence.append("Price remains above the 200-day trend.")
        else:
            score -= 7; cautions.append("Price is below the 200-day trend.")

    rsi_delta = 0.0
    if prev is not None and pd.notna(prev.get("RSI")):
        rsi_delta = rsi - float(prev["RSI"])
    if 48 <= rsi <= 68 and rsi_delta > 0:
        score += 10; evidence.append(f"RSI is strengthening without being extreme ({rsi:.1f}).")
    elif rsi >= 75:
        score -= 5; cautions.append(f"RSI is extended ({rsi:.1f}); pullback risk is higher.")
    elif rsi <= 30:
        score -= 4; cautions.append(f"RSI is oversold ({rsi:.1f}) but still needs confirmation.")
    elif rsi < 45 and rsi_delta < 0:
        score -= 8; cautions.append(f"RSI is weakening ({rsi:.1f}).")

    if macd_hist > 0:
        score += 8; evidence.append("MACD momentum is positive.")
    else:
        score -= 8; cautions.append("MACD momentum is negative.")

    if adx >= 25:
        if plus_di > minus_di:
            score += 8; evidence.append(f"ADX confirms a strengthening positive trend ({adx:.1f}).")
        else:
            score -= 8; cautions.append(f"ADX confirms a strengthening negative trend ({adx:.1f}).")
    else:
        cautions.append(f"Trend strength is limited (ADX {adx:.1f}).")

    if rvol >= 1.5:
        score += 8 if close >= ema20 else -5
        (evidence if close >= ema20 else cautions).append(f"Relative volume is elevated at {rvol:.2f}×.")
    elif rvol < .75:
        score -= 2; cautions.append(f"Participation is quiet at {rvol:.2f}× normal.")

    if obv > obv_ema:
        score += 5; evidence.append("OBV suggests accumulation is stronger than its recent trend.")
    else:
        score -= 5; cautions.append("OBV is below its recent trend.")

    if bb_pos > 1.05:
        score -= 3; cautions.append("Price is stretched above the upper Bollinger Band.")
    elif bb_pos < -.05:
        score -= 2; cautions.append("Price is below the lower Bollinger Band.")
    elif .45 <= bb_pos <= .9:
        score += 3

    score = clamp(score)
    if score >= 82:
        label, badge = "STRONG SETUP", "badge-green"
    elif score >= 70:
        label, badge = "BUY WATCH", "badge-green"
    elif score >= 56:
        label, badge = "HOLD / TREND HEALTHY", "badge"
    elif score >= 44:
        label, badge = "NEUTRAL", "badge"
    elif score >= 30:
        label, badge = "RISK INCREASING", "badge-amber"
    else:
        label, badge = "DEFENSIVE REVIEW", "badge-red"

    trend_component = clamp(
        50
        + (12 if close > ema20 > ema50 else -12 if close < ema20 < ema50 else 0)
        + (7 if pd.notna(ema200) and close > ema200 else -7 if pd.notna(ema200) else 0)
    )
    momentum_component = clamp(
        50
        + (10 if 48 <= rsi <= 68 and rsi_delta > 0 else -8 if rsi < 45 and rsi_delta < 0 else -5 if rsi >= 75 else 0)
        + (8 if macd_hist > 0 else -8)
    )
    volume_component = clamp(
        50
        + (18 if rvol >= 1.5 and close >= ema20 else -8 if rvol < .75 else 4)
        + (8 if obv > obv_ema else -8)
    )
    risk_component = clamp(
        100
        - (float(row["ATR_PCT"]) if pd.notna(row["ATR_PCT"]) else 5) * 8
        - (8 if rsi >= 75 else 0)
    )
    components = {
        "Trend": trend_component,
        "Momentum": momentum_component,
        "Volume": volume_component,
        "Risk quality": risk_component,
    }
    agreement = sum(value >= 60 for value in components.values()) / len(components) * 100

    return {
        "score": score,
        "label": label,
        "badge": badge,
        "evidence": evidence[:5],
        "cautions": cautions[:5],
        "rsi": rsi,
        "rsi_delta": rsi_delta,
        "macd_hist": macd_hist,
        "adx": adx,
        "rvol": rvol,
        "atr_pct": float(row["ATR_PCT"]) if pd.notna(row["ATR_PCT"]) else np.nan,
        "agreement": agreement,
        "components": components,
    }


def backtest_signals(df: pd.DataFrame) -> dict:
    work = df.dropna(subset=["RSI","EMA50","MACD_HIST","ADX","RVOL20"]).copy()
    if len(work) < 80:
        return {"count":0}
    scores = []
    prev = None
    for _, row in work.iterrows():
        result = signal_score_row(row, prev)
        scores.append(result["score"])
        prev = row
    work["SIGNAL_SCORE"] = scores
    work["FWD5"] = work["Close"].shift(-5)/work["Close"]-1
    work["FWD20"] = work["Close"].shift(-20)/work["Close"]-1
    events = work[(work["SIGNAL_SCORE"] >= 70) & (work["SIGNAL_SCORE"].shift(1) < 70)].dropna(subset=["FWD5","FWD20"])
    if events.empty:
        return {"count":0}
    return {
        "count":int(len(events)),
        "win5":float((events["FWD5"]>0).mean()*100),
        "avg5":float(events["FWD5"].mean()*100),
        "median5":float(events["FWD5"].median()*100),
        "win20":float((events["FWD20"]>0).mean()*100),
        "avg20":float(events["FWD20"].mean()*100),
        "worst20":float(events["FWD20"].min()*100),
    }


def resolve_ticker(raw: str, market: str) -> str:
    t = raw.strip().upper()
    if market == "Crypto":
        return CRYPTO_TICKERS.get(t, t if t.endswith("-USD") else f"{t}-USD")
    return t


st.set_page_config(page_title=APP_NAME,page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown(CSS,unsafe_allow_html=True)
market_rows, source = get_market_rows()
portfolio = build_portfolio(market_rows)

st.sidebar.markdown("## ◈ Intelligence Desk")
st.sidebar.caption(f"Version {APP_VERSION}")
st.sidebar.markdown("---")
selection = st.sidebar.radio("Navigation",["Today","Portfolio","Markets","Watch","Research","4H Intelligence","Signal Lab"],label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption(f"{source} · refreshes every 5 minutes")

titles = {
    "Today":("Good morning, Mark","Your portfolio briefing in under five minutes."),
    "Portfolio":("My Portfolio","How am I doing, and which holdings matter most today?"),
    "Markets":("Market Themes","Where is capital moving, and how is your portfolio exposed?"),
    "Watch":("Needs Attention","Only the holdings with the most meaningful changes."),
    "Research":("Research","Investigate one holding and understand exactly why it matters."),
    "4H Intelligence":("4H Intelligence","Detect short-term behavioural shifts before the daily trend fully turns."),
    "Signal Lab":("Signal Lab","Manually test any crypto, stock or ETF against the broader trend."),
}
page_header(*titles[selection])

if selection == "Today":
    cols=st.columns(4)
    with cols[0]: metric("Portfolio value",money(portfolio["total"]),signed(portfolio["daily_pct"])+" today")
    with cols[1]: metric("Today's P/L",money(portfolio["daily_change"]),"Portfolio contribution")
    with cols[2]: metric("Portfolio health",f'{portfolio["health"]:.0f}/100',f'{portfolio["risk"]} risk')
    wc=sum(1 for x in portfolio["attention"] if x["action"]!="Hold")
    workload="LOW" if wc<=1 else "MEDIUM" if wc<=3 else "HIGH"
    with cols[3]: metric("Today's workload",workload,f"{wc} holdings deserve attention")
    left,right=st.columns([1.45,1])
    with left:
        section("Executive brief")
        st.markdown(f'<div class="summary-box">{executive_brief(portfolio)}</div>',unsafe_allow_html=True)
    with right:
        section("Portfolio health")
        progress("Overall intelligence",portfolio["health"],"Momentum, participation, conviction and risk")
    section("Today's attention")
    cols=st.columns(3)
    for col,item in zip(cols,portfolio["attention"][:3]):
        with col: intelligence_card(item, "attention_score", "Attention score")

    section("Possible opportunities")
    cols=st.columns(3)
    for col,item in zip(cols,portfolio["opportunities"][:3]):
        with col: intelligence_card(item, "opportunity_score", "Opportunity score")
    section("What drove the portfolio")
    leaders=sorted(portfolio["items"],key=lambda x:x["contribution"],reverse=True)
    cols=st.columns(4)
    for col,item in zip(cols,leaders[:4]):
        with col: metric(item["symbol"],money(item["contribution"]),f'{signed(item["change_24h"])} · {item["weight"]:.1f}% weight')
    section("Money flow")
    cols=st.columns(4)
    for col,theme in zip(cols,portfolio["themes"][:4]):
        with col: progress(theme["name"],theme["strength"],f'{signed(theme["change"])} portfolio-weighted')

elif selection=="Portfolio":
    cols=st.columns(4)
    with cols[0]: metric("Total value",money(portfolio["total"]),signed(portfolio["daily_pct"])+" today")
    with cols[1]: metric("Daily contribution",money(portfolio["daily_change"]),"Across all holdings")
    with cols[2]: metric("Health",f'{portfolio["health"]:.0f}/100',f'{portfolio["risk"]} risk')
    with cols[3]: metric("Largest position",portfolio["items"][0]["symbol"],f'{portfolio["items"][0]["weight"]:.1f}% of portfolio')
    section("Portfolio structure")
    tier_cols = st.columns(4)
    with tier_cols[0]: metric("Core holdings", money(portfolio["tier_values"].get("Core",0)), "Full intelligence coverage")
    with tier_cols[1]: metric("Secondary", money(portfolio["tier_values"].get("Secondary",0)), "Escalates when shifts matter")
    with tier_cols[2]: metric("Legacy / small", money(portfolio["tier_values"].get("Legacy",0)), "Lightweight monitoring")
    with tier_cols[3]: metric("Top-five concentration", f'{portfolio["top5_weight"]:.1f}%', "Share held in five largest positions")

    for tier in ["Core","Secondary","Legacy"]:
        section(f"{tier} holdings")
        tier_items = [x for x in portfolio["items"] if x.get("tier") == tier]
        with st.expander(f"Show {len(tier_items)} {tier.lower()} positions", expanded=(tier=="Core")):
            for start in range(0,len(tier_items),3):
                cols=st.columns(3)
                for col,item in zip(cols,tier_items[start:start+3]):
                    with col: asset_card(item)
                st.write("")

elif selection=="Markets":
    section("Market pulse")
    strongest_theme = max(portfolio["themes"], key=lambda x:x["strength"]) if portfolio["themes"] else None
    weakest_theme = min(portfolio["themes"], key=lambda x:x["strength"]) if portfolio["themes"] else None
    pulse_cols = st.columns(4)
    with pulse_cols[0]: metric("Leading narrative", strongest_theme["name"] if strongest_theme else "—", f'{strongest_theme["strength"]:.0f}/100' if strongest_theme else "No data")
    with pulse_cols[1]: metric("Weakest narrative", weakest_theme["name"] if weakest_theme else "—", f'{weakest_theme["strength"]:.0f}/100' if weakest_theme else "No data")
    with pulse_cols[2]: metric("Portfolio themes", str(len(portfolio["themes"])), "Narratives represented")
    with pulse_cols[3]: metric("Top-five concentration", f'{portfolio["top5_weight"]:.1f}%', "Largest five positions")

    section("Narrative strength")
    for start_idx in range(0,min(8,len(portfolio["themes"])),4):
        cols=st.columns(4)
        for col,theme in zip(cols,portfolio["themes"][start_idx:start_idx+4]):
            with col: progress(theme["name"],theme["strength"],f'{signed(theme["change"])} today')

    categories = [
        "RWA / Tokenisation","AI","DePIN / Storage","Layer 1","Layer 2",
        "DeFi / DEX","Gaming","Interoperability","Privacy / Payments","Meme"
    ]
    section("Top five by category")
    for category in categories:
        members = category_members(portfolio["items"], category)
        if not members:
            continue
        with st.expander(f"{category} · Top {len(members)}", expanded=category in ["RWA / Tokenisation","Layer 1","AI"]):
            header_cols = st.columns([.5,1.7,.8,.8,.8,1.2])
            header_cols[0].caption("Rank")
            header_cols[1].caption("Asset")
            header_cols[2].caption("24h")
            header_cols[3].caption("RVOL")
            header_cols[4].caption("Opportunity")
            header_cols[5].caption("Momentum")
            for rank,item in enumerate(members,1):
                render_rank_row(rank,item)

    section("Portfolio exposure")
    themes=sorted(portfolio["themes"],key=lambda x:x["value"],reverse=True)
    for start_idx in range(0,min(8,len(themes)),4):
        cols=st.columns(4)
        for col,theme in zip(cols,themes[start_idx:start_idx+4]):
            with col: metric(theme["name"],f'{theme["value"]/portfolio["total"]*100:.1f}%',money(theme["value"]))

elif selection=="Watch":
    section("Priority watchlist")
    watch_items = sorted(
        portfolio["items"],
        key=lambda x: (
            x["attention_score"] * .50
            + abs(x["change_24h"]) * 2.5
            + x["rvol"] * 8
            + (12 if x["tier"] == "Core" else 5 if x["tier"] == "Secondary" else 0)
        ),
        reverse=True,
    )[:10]

    watch_cols = st.columns(4)
    possible_buys = sum(item["score"] >= 65 for item in watch_items)
    sell_watches = sum(item["score"] < 50 for item in watch_items)
    promoted = sum(item["tier"] != "Core" and item["attention_score"] >= 65 for item in watch_items)
    with watch_cols[0]: metric("Items requiring attention",str(len(watch_items)),"Ranked by impact and signal change")
    with watch_cols[1]: metric("Possible buy watches",str(possible_buys),"Blue or green signals")
    with watch_cols[2]: metric("Declining / sell watches",str(sell_watches),"Orange or red signals")
    with watch_cols[3]: metric("Secondary promotions",str(promoted),"Smaller holdings showing unusual activity")

    for item in watch_items:
        with st.expander(
            f'{item["symbol"]} · {item["signal_label"]} · Attention {item["attention_score"]:.0f}',
            expanded=item["attention_score"] >= 75,
        ):
            top = st.columns(4)
            with top[0]: metric("Portfolio impact",f'{item["weight"]:.1f}%',money(item["value"]))
            with top[1]: metric("Attention",f'{item["attention_score"]:.0f}/100',item["tier"])
            with top[2]: metric("Opportunity",f'{item["opportunity_score"]:.0f}/100',item["momentum"])
            with top[3]: metric("Relative volume",f'{item["rvol"]:.2f}×',item["volume_label"])

            left,right = st.columns(2)
            with left:
                st.markdown("**Why it matters**")
                reasons = [
                    f'24-hour movement is {signed(item["change_24h"])}.',
                    f'7-day movement is {signed(item["change_7d"])}.',
                    f'Current signal is {item["signal_label"].lower()}.',
                    f'Portfolio exposure is {item["weight"]:.1f}%.',
                ]
                for reason in reasons:
                    st.markdown(f"• {reason}")
            with right:
                st.markdown("**What still needs confirmation**")
                confirmations = []
                if item["rvol"] < 1.15:
                    confirmations.append("Volume participation is not yet elevated.")
                if item["score"] < 65:
                    confirmations.append("The overall evidence score has not reached buy-watch territory.")
                if item["risk"] == "HIGH":
                    confirmations.append("Risk remains high despite any improving momentum.")
                if not confirmations:
                    confirmations.append("No major confirmation gap is currently visible.")
                for confirmation in confirmations:
                    st.markdown(f"• {confirmation}")

    section("Purpose of this page")
    st.markdown(
        '<div class="summary-box">Watch is the triage desk. It only surfaces holdings where portfolio impact, '
        'price movement, volume, momentum or signal quality has changed enough to deserve your attention.</div>',
        unsafe_allow_html=True,
    )

elif selection=="Research":
    section("Select a portfolio asset")
    symbols = [item["symbol"] for item in sorted(portfolio["items"], key=lambda x:(x["tier"]!="Core",-x["value"]))]
    selected_symbol = st.selectbox("Holding", symbols)
    item = selected_portfolio_item(portfolio, selected_symbol)

    render_signal_hero(
        item["score"],
        item["signal_label"],
        "HIGH" if item["score"] >= 75 or item["score"] <= 25 else "MEDIUM",
    )

    cols = st.columns(4)
    with cols[0]: metric("Current value",money(item["value"]),f'{item["weight"]:.1f}% of portfolio')
    with cols[1]: metric("Attention",f'{item["attention_score"]:.0f}/100',item["tier"])
    with cols[2]: metric("Opportunity",f'{item["opportunity_score"]:.0f}/100',item["narrative"])
    with cols[3]: metric("Risk",item["risk"],f'{item["risk_score"]:.0f}/100 risk score')

    section("Research conclusion")
    st.markdown(f'<div class="summary-box">{esc(research_summary(item))}</div>',unsafe_allow_html=True)

    left,right = st.columns(2)
    with left:
        section("Supporting evidence")
        support = []
        if item["change_24h"] > 0: support.append(f'Price is positive over 24 hours at {signed(item["change_24h"])}.')
        if item["change_7d"] > 0: support.append(f'Price is positive over seven days at {signed(item["change_7d"])}.')
        if item["rvol"] >= 1.15: support.append(f'Participation is elevated at {item["rvol"]:.2f}×.')
        if item["momentum_score"] >= 60: support.append(f'Momentum score is constructive at {item["momentum_score"]:.0f}/100.')
        if item["score"] >= 65: support.append("The combined evidence score is in possible-buy territory.")
        if not support: support.append("No strong positive agreement is currently present.")
        for line in support: st.markdown(f"✓ {line}")

    with right:
        section("Contrary evidence")
        caution = []
        if item["change_24h"] < 0: caution.append(f'Price is negative over 24 hours at {signed(item["change_24h"])}.')
        if item["change_7d"] < 0: caution.append(f'Price is negative over seven days at {signed(item["change_7d"])}.')
        if item["rvol"] < .75: caution.append(f'Participation is quiet at {item["rvol"]:.2f}×.')
        if item["risk"] == "HIGH": caution.append("Risk is elevated.")
        if item["score"] < 50: caution.append("The combined evidence score is in declining or defensive territory.")
        if not caution: caution.append("No major contrary evidence is currently present.")
        for line in caution: st.markdown(f"• {line}")

    section("Score breakdown")
    score_cols = st.columns(4)
    with score_cols[0]: progress("Overall intelligence",item["score"],item["signal_label"])
    with score_cols[1]: progress("Momentum",item["momentum_score"],item["momentum"])
    with score_cols[2]: progress("Participation",item["volume_score"],f'{item["rvol"]:.2f}× relative volume')
    with score_cols[3]: progress("Risk quality",100-item["risk_score"],f'{item["risk"]} risk')

    section("Portfolio context")
    context_cols = st.columns(4)
    with context_cols[0]: metric("Tier",item["tier"],"Monitoring priority")
    with context_cols[1]: metric("Narrative",item["narrative"],"Market exposure")
    with context_cols[2]: metric("Tokens",f'{item["tokens"]:,.6f}',"From holdings.json")
    with context_cols[3]: metric("Live price",money(item["price"],6 if item["price"] < 1 else 2),source)

    section("Full portfolio matrix")
    with st.expander("Open comparison table"):
        rows=[]
        for row_item in sorted(portfolio["items"],key=lambda x:x["attention_score"],reverse=True):
            rows.append({"Asset":row_item["symbol"],"Tier":row_item["tier"],"Signal":row_item["signal_label"],
                         "Score":round(row_item["score"]),"Attention":round(row_item["attention_score"]),
                         "Opportunity":round(row_item["opportunity_score"]),"RVOL":round(row_item["rvol"],2),
                         "24h":signed(row_item["change_24h"]),"7d":signed(row_item["change_7d"]),
                         "Weight":f'{row_item["weight"]:.1f}%',"Narrative":row_item["narrative"]})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif selection=="4H Intelligence":
    st.markdown('<div class="summary-box"><b>Signature feature.</b> This page looks for behavioural change on hourly data before the broader daily trend fully confirms.</div>',unsafe_allow_html=True)

    section("Portfolio 4H scanner")
    core_symbols = [item["symbol"] for item in portfolio["items"] if item["tier"]=="Core"]
    selected_4h = st.selectbox("Core holding", core_symbols, index=core_symbols.index("COTI") if "COTI" in core_symbols else 0)
    ticker = resolve_ticker(selected_4h,"Crypto")
    short_window = st.selectbox("Research window",["30-day hourly view","60-day hourly view"],index=0)
    short_days = 30 if short_window.startswith("30") else 60

    with st.spinner(f"Scanning {selected_4h} across the 4-hour research framework..."):
        intraday = load_intraday_history(ticker, short_days)
        short_data = add_short_shift_indicators(intraday) if not intraday.empty else pd.DataFrame()
        short_result = short_shift_result(short_data) if not short_data.empty else None

    if short_result is None:
        st.error("Hourly market history was unavailable for this asset.")
    else:
        confidence = (
            "HIGH" if short_result["score"] >= 78 or short_result["score"] <= 22
            else "MEDIUM" if short_result["score"] >= 62 or short_result["score"] <= 38
            else "LOW"
        )
        render_signal_hero(short_result["score"],short_result["label"],confidence)
        render_score_key()

        metric_cols = st.columns(4)
        with metric_cols[0]: metric("6-hour shift",signed(short_result["ret6"]),"Fast direction")
        with metric_cols[1]: metric("24-hour shift",signed(short_result["ret24"]),"Current behaviour")
        with metric_cols[2]: metric("RSI 9",f'{short_result["rsi"]:.1f}',f'6-hour change {short_result["rsi_delta"]:+.1f}')
        with metric_cols[3]: metric("Hourly RVOL",f'{short_result["rvol"]:.2f}×',f'6-hour change {short_result["rvol_delta"]:+.2f}×')

        left,right = st.columns(2)
        with left:
            section("Why the signal improved")
            if short_result["evidence"]:
                for line in short_result["evidence"]: st.markdown(f"✓ {line}")
            else:
                st.markdown("No strong positive short-term agreement yet.")
        with right:
            section("What still needs confirmation")
            if short_result["cautions"]:
                for line in short_result["cautions"]: st.markdown(f"• {line}")
            else:
                st.markdown("No major short-term cautions are present.")

        section("4H trend structure")
        st.line_chart(short_result["chart"],use_container_width=True)
        st.caption("The 4H Intelligence score combines hourly EMA 9/21/55 structure, RSI 9 direction, fast MACD, relative volume and 6-hour/24-hour price confirmation. It is an early-warning research signal, not an automatic trade instruction.")

    section("Core portfolio snapshot")
    core_ranked = sorted([x for x in portfolio["items"] if x["tier"]=="Core"],key=lambda x:x["attention_score"],reverse=True)[:8]
    cols=st.columns(4)
    for idx,item in enumerate(core_ranked):
        with cols[idx%4]:
            intelligence_card(item,"attention_score","Portfolio attention")

elif selection=="Signal Lab":
    st.markdown('<div class="summary-box"><b>Manual research tool.</b> Use Signal Lab for broader daily trend analysis and historical testing on any crypto, stock or ETF.</div>',unsafe_allow_html=True)

    section("Investigate an asset")
    c1,c2,c3=st.columns([1,1,1])
    with c1:
        market=st.selectbox("Market",["Crypto","Stock / ETF"],key="signal_market")
    with c2:
        default_ticker="SOL" if market=="Crypto" else "AAPL"
        raw=st.text_input("Ticker",value=default_ticker,key="signal_ticker")
    with c3:
        period=st.selectbox("History",["1y","2y","5y"],index=1,key="signal_period")
    ticker=resolve_ticker(raw,market)

    section("Broader trend research")
    with st.spinner(f"Loading {ticker} daily history..."):
        history=load_history(ticker,period)

    if history.empty or len(history)<80:
        st.error("Not enough market history was returned. Check the ticker and try again.")
    else:
        enriched=add_indicators(history)
        valid=enriched.dropna(subset=["RSI","EMA50","MACD_HIST","ADX","RVOL20"])
        if valid.empty:
            st.error("The available history is insufficient to calculate the indicator set.")
        else:
            latest=valid.iloc[-1]
            previous=valid.iloc[-2] if len(valid)>1 else None
            result=signal_score_row(latest,previous)
            bt=backtest_signals(enriched)

            section("Current signal brief")
            confidence = "HIGH" if result["agreement"] >= 75 else "MEDIUM" if result["agreement"] >= 50 else "LOW"
            render_signal_hero(result["score"], result["label"], confidence)
            render_score_key()

            cols=st.columns(4)
            with cols[0]: metric("Ticker",ticker,f'Close {money(float(latest["Close"]),2)}')
            with cols[1]: metric("Indicator agreement",f'{result["agreement"]:.0f}%',"Major evidence groups aligned")
            with cols[2]: metric("Relative volume",f'{result["rvol"]:.2f}×',"Compared with 20-day average")
            with cols[3]: metric("Volatility",f'{result["atr_pct"]:.1f}% ATR',"Typical daily range")

            left,right=st.columns(2)
            with left:
                st.markdown('<div class="signal-card"><div class="asset-head"><b>Supporting evidence</b><span class="badge badge-green">Positive</span></div>',unsafe_allow_html=True)
                if result["evidence"]:
                    for item in result["evidence"]:
                        st.markdown(f"✓ {item}")
                else:
                    st.markdown("No strong positive agreement is present.")
                st.markdown("</div>",unsafe_allow_html=True)
            with right:
                st.markdown('<div class="signal-card"><div class="asset-head"><b>Contrary evidence</b><span class="badge badge-amber">Check</span></div>',unsafe_allow_html=True)
                if result["cautions"]:
                    for item in result["cautions"]:
                        st.markdown(f"• {item}")
                else:
                    st.markdown("No major contrary evidence is present.")
                st.markdown("</div>",unsafe_allow_html=True)

            section("Why this score?")
            why_left, why_right = st.columns([1,1.15])
            with why_left:
                render_component_breakdown(result["components"])
                st.caption("Component scores are normalised to 0–100. The final score also includes indicator-level adjustments.")
            with why_right:
                rsi_status = "Healthy" if 48 <= result["rsi"] <= 68 and result["rsi_delta"] > 0 else "Extended" if result["rsi"] >= 75 else "Weak" if result["rsi"] < 45 else "Mixed"
                rsi_meaning = (
                    "Momentum is strengthening without yet being overbought."
                    if rsi_status == "Healthy"
                    else "Momentum is stretched and pullback risk is higher."
                    if rsi_status == "Extended"
                    else "Momentum is soft and needs improvement."
                    if rsi_status == "Weak"
                    else "RSI is not giving a decisive signal."
                )
                render_indicator_explanation(
                    "RSI 14",
                    f'{result["rsi"]:.1f}',
                    rsi_status,
                    rsi_meaning,
                    "positive" if rsi_status == "Healthy" else "negative" if rsi_status in ["Extended","Weak"] else "neutral",
                )

                render_indicator_explanation(
                    "MACD histogram",
                    f'{result["macd_hist"]:.4f}',
                    "Positive" if result["macd_hist"] > 0 else "Negative",
                    "Momentum is above its signal line." if result["macd_hist"] > 0 else "Momentum is below its signal line.",
                    "positive" if result["macd_hist"] > 0 else "negative",
                )

                render_indicator_explanation(
                    "ADX 14",
                    f'{result["adx"]:.1f}',
                    "Strong trend" if result["adx"] >= 25 else "Weak trend",
                    "The current trend has enough strength to be considered established."
                    if result["adx"] >= 25
                    else "Price direction may be less reliable because trend strength is limited.",
                    "positive" if result["adx"] >= 25 else "neutral",
                )

                render_indicator_explanation(
                    "Relative volume",
                    f'{result["rvol"]:.2f}×',
                    "High participation" if result["rvol"] >= 1.5 else "Normal" if result["rvol"] >= .75 else "Quiet",
                    "Trading activity is well above the recent 20-day average."
                    if result["rvol"] >= 1.5
                    else "Participation is near its recent norm."
                    if result["rvol"] >= .75
                    else "Participation is below normal, so price moves may have less confirmation.",
                    "positive" if result["rvol"] >= 1.5 else "negative" if result["rvol"] < .75 else "neutral",
                )

            section("Historical signal test")
            if bt.get("count",0)>0:
                cols=st.columns(4)
                with cols[0]: metric("Similar setups",str(bt["count"]),"Score crossed above 70")
                with cols[1]: metric("5-day win rate",f'{bt["win5"]:.1f}%',f'Average {bt["avg5"]:+.2f}%')
                with cols[2]: metric("20-day win rate",f'{bt["win20"]:.1f}%',f'Average {bt["avg20"]:+.2f}%')
                with cols[3]: metric("Worst 20-day result",f'{bt["worst20"]:+.2f}%',"Observed sample")
                st.caption("This is an exploratory historical test, not a validated trading strategy. It excludes fees, slippage, taxes and position-sizing rules.")
            else:
                st.info("No comparable score-crossing events were available in the selected history.")

            section("Price and trend")
            chart_df=enriched[["Close","EMA20","EMA50","EMA200"]].dropna(how="all").tail(250)
            st.line_chart(chart_df,use_container_width=True)
