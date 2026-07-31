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
APP_VERSION = "5.4.1"
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

.fourh-grid{display:grid;grid-template-columns:1.35fr .62fr .72fr .72fr .86fr;gap:.55rem;align-items:center;
background:#1b1f25;border:1px solid var(--line);border-radius:11px;padding:.66rem .75rem;margin:.38rem 0}
.fourh-grid:hover{border-color:#5a6777;background:#20252c}
.fourh-asset{font-weight:850;font-size:.92rem}.fourh-name{color:var(--muted);font-size:.72rem}
.fourh-score{font-size:1.2rem;font-weight:900}.fourh-delta{font-size:.74rem;font-weight:750}
.fourh-pill{display:inline-block;border-radius:999px;padding:.2rem .5rem;font-size:.7rem;font-weight:800}
.fourh-green{background:#173524;color:#8ce8ae}.fourh-blue{background:#182d46;color:#9bc8ff}
.fourh-yellow{background:#403814;color:#f5d882}.fourh-orange{background:#4b2e18;color:#ffbf83}
.fourh-red{background:#431d22;color:#ff9b9b}
.narrative-note{color:var(--muted);font-size:.78rem;margin:-.25rem 0 .65rem}
.scan-status{background:#1b1f25;border:1px solid var(--line);border-radius:12px;padding:.8rem 1rem}


.flow-arrow{font-size:1.25rem;font-weight:900;line-height:1}
.flow-up{color:#5ee58d}.flow-down{color:#ff7373}.flow-watch{color:#79b8ff}
.flow-flat{color:#f0d46d}.flow-fade{color:#ffab68}.flow-muted{color:#9aa4b2}
.objective-card{background:#1b1f25;border:1px solid var(--line);border-radius:12px;padding:.85rem 1rem;height:100%}
.objective-title{font-size:.74rem;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}
.objective-main{font-size:1.35rem;font-weight:900;margin:.15rem 0}
.objective-row{display:flex;justify-content:space-between;gap:.75rem;border-top:1px solid var(--line);padding:.48rem 0;font-size:.8rem}
.objective-row:first-of-type{border-top:0}
.fourh-grid{grid-template-columns:1.35fr .72fr .72fr .72fr .72fr}

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
        f'<div class="data-row"><span>Relative volume</span><b>{item["rvol"]:.2f}×</b></div>'
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


def executive_brief(portfolio: dict) -> str:
    leaders = sorted(portfolio["items"],key=lambda x:x["contribution"],reverse=True)
    strongest = max(portfolio["items"],key=lambda x:x["score"])
    active = max(portfolio["items"],key=lambda x:x["rvol"])
    direction = "gained" if portfolio["daily_change"]>=0 else "declined"
    ending = "No urgent defensive action is indicated." if portfolio["risk"]!="HIGH" else "Review the highest-risk positions."
    return f"Your portfolio {direction} today. {leaders[0]['symbol']} and {leaders[1]['symbol']} are the largest positive contributors. {active['symbol']} currently has the highest relative-volume reading. {ending}"



# ---------- 4H Intelligence universe ----------

FOUR_HOUR_UNIVERSE = {
    "RWA / Tokenisation": [
        ("ONDO", "Ondo", "ONDO-USD"), ("LINK", "Chainlink", "LINK-USD"),
        ("POLYX", "Polymesh", "POLYX-USD"), ("MPL", "Maple Finance", "MPL-USD"),
    ],
    "AI": [
        ("FET", "Artificial Superintelligence Alliance", "FET-USD"),
        ("RENDER", "Render", "RENDER-USD"), ("TAO", "Bittensor", "TAO22974-USD"),
        ("NEAR", "NEAR Protocol", "NEAR-USD"),
    ],
    "Layer 1": [
        ("SOL", "Solana", "SOL-USD"), ("SUI", "Sui", "SUI20947-USD"),
        ("AVAX", "Avalanche", "AVAX-USD"), ("SEI", "Sei", "SEI-USD"),
    ],
    "Layer 2 / Scaling": [
        ("POL", "Polygon", "POL-USD"), ("ARB", "Arbitrum", "ARB11841-USD"),
        ("OP", "Optimism", "OP-USD"), ("IMX", "Immutable", "IMX10603-USD"),
    ],
    "DeFi / DEX": [
        ("AAVE", "Aave", "AAVE-USD"), ("UNI", "Uniswap", "UNI7083-USD"),
        ("RUNE", "THORChain", "RUNE-USD"), ("AERO", "Aerodrome", "AERO29270-USD"),
    ],
    "DePIN / Storage": [
        ("FIL", "Filecoin", "FIL-USD"), ("AR", "Arweave", "AR-USD"),
        ("AIOZ", "AIOZ Network", "AIOZ-USD"), ("HNT", "Helium", "HNT-USD"),
    ],
    "Gaming / Metaverse": [
        ("IMX", "Immutable", "IMX10603-USD"), ("SUPER", "SuperVerse", "SUPER-USD"),
        ("GALA", "Gala", "GALA-USD"), ("SAND", "The Sandbox", "SAND-USD"),
    ],
    "Privacy / Payments": [
        ("COTI", "COTI", "COTI-USD"), ("XMR", "Monero", "XMR-USD"),
        ("ZEC", "Zcash", "ZEC-USD"), ("XLM", "Stellar", "XLM-USD"),
    ],
}


def direction_arrow(value: float, threshold: float = 0.15) -> tuple[str, str]:
    if value > threshold:
        return "↑", "up"
    if value < -threshold:
        return "↓", "down"
    return "→", "flat"


def volume_flow(ret6: float, rvol_delta: float, rvol: float) -> dict:
    price_up = ret6 > 0.20
    price_down = ret6 < -0.20
    volume_up = rvol_delta > 0.10
    volume_down = rvol_delta < -0.10

    if volume_up and price_up:
        return {"label": "Positive flow", "arrow": "↑", "colour": "up", "rank": 5}
    if volume_up and price_down:
        return {"label": "Negative flow", "arrow": "↓", "colour": "down", "rank": 1}
    if volume_up:
        return {"label": "Volume rising", "arrow": "↑", "colour": "watch", "rank": 4}
    if volume_down and price_up:
        return {"label": "Volume fading", "arrow": "↓", "colour": "fade", "rank": 2}
    if volume_down:
        return {"label": "Volume falling", "arrow": "↓", "colour": "flat", "rank": 2}
    if rvol >= 1.25:
        return {"label": "Above normal", "arrow": "→", "colour": "watch", "rank": 3}
    return {"label": "Stable", "arrow": "→", "colour": "muted", "rank": 3}


def trend_direction(item: dict) -> dict:
    chart = item.get("chart")
    if isinstance(chart, pd.DataFrame) and not chart.empty:
        last = chart.iloc[-1]
        if last["Close"] > last["EMA9"] > last["EMA21"]:
            return {"label": "Up", "arrow": "↑", "colour": "up"}
        if last["Close"] < last["EMA9"] < last["EMA21"]:
            return {"label": "Down", "arrow": "↓", "colour": "down"}
    return {"label": "Mixed", "arrow": "→", "colour": "flat"}


@st.cache_data(ttl=900, show_spinner=False)
def load_fourh_universe() -> dict[str, pd.DataFrame]:
    tickers = sorted({ticker for assets in FOUR_HOUR_UNIVERSE.values() for _, _, ticker in assets})
    try:
        raw = yf.download(
            tickers, period="1mo", interval="1h", auto_adjust=True,
            progress=False, threads=True, group_by="ticker",
        )
    except Exception:
        return {}

    output = {}
    for ticker in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                if ticker in raw.columns.get_level_values(0):
                    frame = raw[ticker].copy()
                elif ticker in raw.columns.get_level_values(-1):
                    frame = raw.xs(ticker, axis=1, level=-1).copy()
                else:
                    continue
            else:
                if len(tickers) != 1:
                    continue
                frame = raw.copy()
            needed = ["Open", "High", "Low", "Close", "Volume"]
            if all(col in frame.columns for col in needed):
                clean = frame[needed].dropna(subset=["Close"]).copy()
                if len(clean) >= 60:
                    output[ticker] = clean
        except Exception:
            continue
    return output


def scan_fourh_universe(portfolio: dict) -> tuple[dict[str, list[dict]], list[dict]]:
    history_map = load_fourh_universe()
    portfolio_map = {item["symbol"]: item for item in portfolio["items"]}
    grouped, all_results = {}, []

    for narrative, assets in FOUR_HOUR_UNIVERSE.items():
        narrative_results = []
        for symbol, name, ticker in assets:
            history = history_map.get(ticker)
            result = None
            if history is not None and not history.empty:
                result = short_shift_result(add_short_shift_indicators(history))

            if result is None:
                holding = portfolio_map.get(symbol)
                if holding is None:
                    continue
                result = {
                    "rsi": float("nan"), "rsi_delta": 0.0,
                    "rvol": holding["rvol"], "rvol_delta": 0.0,
                    "ret6": holding["change_24h"] / 4,
                    "ret24": holding["change_24h"], "ret7d": holding["change_7d"],
                    "chart": pd.DataFrame(),
                }

            item = {
                **result, "symbol": symbol, "name": name, "ticker": ticker,
                "narrative": narrative, "in_portfolio": symbol in portfolio_map,
                "portfolio_weight": portfolio_map.get(symbol, {}).get("weight", 0.0),
            }
            item["flow"] = volume_flow(item["ret6"], item["rvol_delta"], item["rvol"])
            item["trend"] = trend_direction(item)
            narrative_results.append(item)
            all_results.append(item)

        grouped[narrative] = sorted(
            narrative_results,
            key=lambda x: (x["flow"]["rank"], x["rvol_delta"], x["rvol"], x["ret6"]),
            reverse=True,
        )

    all_results = sorted(
        all_results,
        key=lambda x: (x["flow"]["rank"], x["rvol_delta"], x["rvol"], x["ret6"]),
        reverse=True,
    )
    return grouped, all_results


def narrative_flow_summary(items: list[dict]) -> tuple[str, str, str]:
    positive = sum(1 for x in items if x["flow"]["label"] == "Positive flow")
    negative = sum(1 for x in items if x["flow"]["label"] == "Negative flow")
    if positive > negative:
        return "Positive", "↑", "up"
    if negative > positive:
        return "Negative", "↓", "down"
    return "Mixed", "→", "flat"


def render_flow_arrow(flow: dict) -> str:
    return f'<span class="flow-arrow flow-{flow["colour"]}">{flow["arrow"]}</span>'


def render_fourh_scan_row(rank: int, item: dict) -> None:
    portfolio_marker = f' · Held {item["portfolio_weight"]:.1f}%' if item["in_portfolio"] else ""
    price_arrow, price_colour = direction_arrow(item["ret6"])
    volume_arrow, volume_colour = direction_arrow(item["rvol_delta"], 0.10)
    st.markdown(
        f'<div class="fourh-grid">'
        f'<div><div class="fourh-asset">{rank}. {esc(item["symbol"])} · {esc(item["name"])}</div>'
        f'<div class="fourh-name">{esc(item["narrative"])}{portfolio_marker}</div></div>'
        f'<div><span class="flow-arrow flow-{price_colour}">{price_arrow}</span> '
        f'<b>{signed(item["ret6"])}</b><div class="fourh-name">6-hour price</div></div>'
        f'<div><span class="flow-arrow flow-{volume_colour}">{volume_arrow}</span> '
        f'<b>{item["rvol_delta"]:+.2f}×</b><div class="fourh-name">RVOL change</div></div>'
        f'<div><b>{item["rvol"]:.2f}×</b><div class="fourh-name">Current RVOL</div></div>'
        f'<div>{render_flow_arrow(item["flow"])} <b>{esc(item["flow"]["label"])}</b>'
        f'<div class="fourh-name">Volume flow</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_objective_card(item: dict, title: str) -> None:
    flow = volume_flow(item["change_24h"], item["rvol"] - 1.0, item["rvol"])
    price_arrow, price_colour = direction_arrow(item["change_24h"])
    st.markdown(
        f'<div class="objective-card"><div class="objective-title">{esc(title)}</div>'
        f'<div class="objective-main">{esc(item["symbol"])} '
        f'<span class="flow-arrow flow-{price_colour}">{price_arrow}</span></div>'
        f'<div class="objective-row"><span>24-hour price</span><b>{signed(item["change_24h"])}</b></div>'
        f'<div class="objective-row"><span>7-day price</span><b>{signed(item["change_7d"])}</b></div>'
        f'<div class="objective-row"><span>Relative volume</span><b>{item["rvol"]:.2f}×</b></div>'
        f'<div class="objective-row"><span>Volume flow</span><b>{render_flow_arrow(flow)} {esc(flow["label"])}</b></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


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
    "Research":("Research","The evidence beneath the daily briefing."),
    "4H Intelligence":("4H Intelligence","Emerging four-hour trends by narrative, followed by a detailed project investigation."),
    "Signal Lab":("Signal Lab","Capture fast shifts early, then confirm them against the broader trend."),
}
page_header(*titles[selection])

if selection == "Today":
    cols=st.columns(4)
    with cols[0]: metric("Portfolio value",money(portfolio["total"]),signed(portfolio["daily_pct"])+" today")
    with cols[1]: metric("Today's P/L",money(portfolio["daily_change"]),"Portfolio contribution")
    with cols[2]: metric("Portfolio direction", signed(portfolio["daily_pct"]), "24-hour weighted move")
    wc=sum(1 for x in portfolio["attention"] if x["action"]!="Hold")
    workload="LOW" if wc<=1 else "MEDIUM" if wc<=3 else "HIGH"
    with cols[3]: metric("Today's workload",workload,f"{wc} holdings deserve attention")
    left,right=st.columns([1.45,1])
    with left:
        section("Executive brief")
        st.markdown(f'<div class="summary-box">{executive_brief(portfolio)}</div>',unsafe_allow_html=True)
    with right:
        section("Portfolio direction")
        st.markdown(
            f'<div class="summary-box"><b>24-hour move:</b> {signed(portfolio["daily_pct"])}<br>'
            f'<b>Daily contribution:</b> {money(portfolio["daily_change"])}</div>',
            unsafe_allow_html=True,
        )
    section("Today's attention")
    cols=st.columns(3)
    for col,item in zip(cols,portfolio["attention"][:3]):
        with col: render_objective_card(item, "Attention")

    section("Possible opportunities")
    cols=st.columns(3)
    for col,item in zip(cols,portfolio["opportunities"][:3]):
        with col: render_objective_card(item, "Market movement")
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
    with cols[2]: metric("24-hour direction", signed(portfolio["daily_pct"]), "Portfolio-weighted move")
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
    section("Capital rotation")
    for start in range(0,min(8,len(portfolio["themes"])),4):
        cols=st.columns(4)
        for col,theme in zip(cols,portfolio["themes"][start:start+4]):
            with col: progress(theme["name"],theme["strength"],f'{signed(theme["change"])} today')
    section("Portfolio exposure")
    themes=sorted(portfolio["themes"],key=lambda x:x["value"],reverse=True)
    cols=st.columns(4)
    for col,theme in zip(cols,themes[:4]):
        with col: metric(theme["name"],f'{theme["value"]/portfolio["total"]*100:.1f}%',money(theme["value"]))

elif selection=="Watch":
    section("Priority briefs")
    for start in range(0,len(portfolio["attention"]),2):
        cols=st.columns(2)
        for col,item in zip(cols,portfolio["attention"][start:start+2]):
            with col: attention_card(item)
    section("Interpretation")
    st.markdown('<div class="summary-box">A watch item is not automatically a buy or sell signal. It means price, participation, risk or momentum has changed enough to deserve closer investigation.</div>',unsafe_allow_html=True)

elif selection=="Research":
    section("Observable market data")
    rows=[]
    for item in sorted(portfolio["items"], key=lambda x:(x["rvol"], abs(x["change_24h"])), reverse=True):
        flow = volume_flow(item["change_24h"], item["rvol"]-1.0, item["rvol"])
        price_arrow, _ = direction_arrow(item["change_24h"])
        rows.append({
            "Asset":item["symbol"],
            "24h direction":price_arrow,
            "24h":signed(item["change_24h"]),
            "7d":signed(item["change_7d"]),
            "RVOL":round(item["rvol"],2),
            "Volume flow":f'{flow["arrow"]} {flow["label"]}',
            "Momentum":item["momentum"],
            "Portfolio weight":f'{item["weight"]:.1f}%',
            "Narrative":item["narrative"],
        })
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    section("Display rules")
    st.markdown(
        '<div class="summary-box">'
        '<b>Green ↑</b> price and volume are rising together. '
        '<b>Red ↓</b> volume is rising while price is falling. '
        '<b>Blue ↑</b> volume is rising before price direction is clear. '
        '<b>Orange ↓</b> price is rising while volume fades. '
        '<b>Yellow/Grey →</b> mixed or stable conditions.'
        '</div>',
        unsafe_allow_html=True,
    )


elif selection=="4H Intelligence":
    st.markdown(
        '<div class="summary-box"><b>Purpose:</b> Compare observable four-hour price and volume direction '
        'across narratives. No confidence percentage or 0–100 prediction score is used.</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Scanning hourly market data..."):
        narrative_results, all_fourh_results = scan_fourh_universe(portfolio)

    if not all_fourh_results:
        st.error("The four-hour market scan could not retrieve enough hourly data. Try refreshing later.")
    else:
        positive_flows = [x for x in all_fourh_results if x["flow"]["label"] == "Positive flow"]
        negative_flows = [x for x in all_fourh_results if x["flow"]["label"] == "Negative flow"]
        active_volume = sorted(all_fourh_results, key=lambda x:(x["rvol_delta"], x["rvol"]), reverse=True)

        narrative_order = []
        for narrative, items in narrative_results.items():
            if items:
                pos = sum(1 for x in items if x["flow"]["label"] == "Positive flow")
                neg = sum(1 for x in items if x["flow"]["label"] == "Negative flow")
                avg_delta = sum(x["rvol_delta"] for x in items) / len(items)
                narrative_order.append((narrative, pos-neg, avg_delta))
        narrative_order.sort(key=lambda x:(x[1],x[2]), reverse=True)

        summary_cols = st.columns(4)
        with summary_cols[0]:
            metric("Positive volume flow", str(len(positive_flows)), "Price ↑ and volume ↑")
        with summary_cols[1]:
            metric("Negative volume flow", str(len(negative_flows)), "Price ↓ and volume ↑")
        with summary_cols[2]:
            metric("Largest volume increase", active_volume[0]["symbol"], f'{active_volume[0]["rvol_delta"]:+.2f}× RVOL')
        with summary_cols[3]:
            metric("Universe scanned", str(len(all_fourh_results)), "Refreshes every 15 minutes")

        section("Largest four-hour volume changes")
        priority_cols = st.columns(3)
        for col, item in zip(priority_cols, active_volume[:3]):
            with col:
                price_arrow, price_colour = direction_arrow(item["ret6"])
                volume_arrow, volume_colour = direction_arrow(item["rvol_delta"], .10)
                st.markdown(
                    f'<div class="objective-card"><div class="objective-title">{esc(item["narrative"])}</div>'
                    f'<div class="objective-main">{esc(item["symbol"])}</div>'
                    f'<div class="objective-row"><span>6-hour price</span>'
                    f'<b><span class="flow-arrow flow-{price_colour}">{price_arrow}</span> {signed(item["ret6"])}</b></div>'
                    f'<div class="objective-row"><span>RVOL change</span>'
                    f'<b><span class="flow-arrow flow-{volume_colour}">{volume_arrow}</span> {item["rvol_delta"]:+.2f}×</b></div>'
                    f'<div class="objective-row"><span>Current RVOL</span><b>{item["rvol"]:.2f}×</b></div>'
                    f'<div class="objective-row"><span>Volume flow</span>'
                    f'<b>{render_flow_arrow(item["flow"])} {esc(item["flow"]["label"])}</b></div></div>',
                    unsafe_allow_html=True,
                )

        section("Coins by narrative")
        st.caption("Categories are ordered by positive minus negative volume-flow signals, then by average RVOL change.")
        for index, (narrative, _, _) in enumerate(narrative_order):
            items = narrative_results[narrative]
            label, arrow, colour = narrative_flow_summary(items)
            with st.expander(
                f'{narrative} · {arrow} {label} volume flow · {len(items)} projects',
                expanded=index < 3,
            ):
                for rank, item in enumerate(items, 1):
                    render_fourh_scan_row(rank, item)

        section("Open an individual project")
        option_map = {
            f'{item["symbol"]} · {item["name"]} · {item["narrative"]}': item
            for item in all_fourh_results
        }
        selected = option_map[st.selectbox("Project or coin", list(option_map.keys()), index=0)]

        flow = selected["flow"]
        trend = selected["trend"]
        price_arrow, price_colour = direction_arrow(selected["ret6"])
        volume_arrow, volume_colour = direction_arrow(selected["rvol_delta"], .10)

        header_cols = st.columns([1.15,1,1])
        with header_cols[0]:
            st.markdown(
                f'<div class="objective-card"><div class="objective-title">{esc(selected["narrative"])}</div>'
                f'<div class="objective-main">{esc(selected["symbol"])} · {esc(selected["name"])}</div>'
                f'<div class="objective-row"><span>Volume flow</span>'
                f'<b>{render_flow_arrow(flow)} {esc(flow["label"])}</b></div></div>',
                unsafe_allow_html=True,
            )
        with header_cols[1]:
            st.markdown(
                f'<div class="objective-card"><div class="objective-title">Price direction</div>'
                f'<div class="objective-main"><span class="flow-arrow flow-{price_colour}">{price_arrow}</span> '
                f'{signed(selected["ret6"])}</div>'
                f'<div class="objective-row"><span>24-hour price</span><b>{signed(selected["ret24"])}</b></div>'
                f'<div class="objective-row"><span>Trend</span><b>'
                f'<span class="flow-arrow flow-{trend["colour"]}">{trend["arrow"]}</span> {trend["label"]}</b></div></div>',
                unsafe_allow_html=True,
            )
        with header_cols[2]:
            st.markdown(
                f'<div class="objective-card"><div class="objective-title">Volume</div>'
                f'<div class="objective-main"><span class="flow-arrow flow-{volume_colour}">{volume_arrow}</span> '
                f'{selected["rvol_delta"]:+.2f}×</div>'
                f'<div class="objective-row"><span>Current RVOL</span><b>{selected["rvol"]:.2f}×</b></div>'
                f'<div class="objective-row"><span>Portfolio</span><b>'
                f'{"Held " + format(selected["portfolio_weight"], ".1f") + "%" if selected["in_portfolio"] else "Not held"}</b></div></div>',
                unsafe_allow_html=True,
            )

        detail_cols = st.columns(3)
        with detail_cols[0]:
            metric("RSI 9", f'{selected["rsi"]:.1f}' if pd.notna(selected["rsi"]) else "—",
                   f'{selected["rsi_delta"]:+.1f} change' if pd.notna(selected["rsi"]) else "No hourly reading")
        with detail_cols[1]:
            metric("6-hour price", signed(selected["ret6"]), "Observed return")
        with detail_cols[2]:
            metric("24-hour price", signed(selected["ret24"]), "Observed return")

        section("Four-hour trend structure")
        if isinstance(selected["chart"], pd.DataFrame) and not selected["chart"].empty:
            st.line_chart(selected["chart"], use_container_width=True)
            st.caption("Hourly close with EMA 9, EMA 21 and EMA 55. No predictive score is applied.")
        else:
            st.info("A live hourly trend chart was unavailable for this project.")

        section("Arrow rules")
        st.markdown(
            '<div class="summary-box">'
            '<b>Green ↑:</b> price and volume are both rising. '
            '<b>Red ↓:</b> volume is rising while price falls. '
            '<b>Blue ↑:</b> volume is rising while price is mostly flat. '
            '<b>Orange ↓:</b> price rises while volume fades. '
            '<b>Yellow/Grey →:</b> mixed, falling or stable activity.'
            '</div>',
            unsafe_allow_html=True,
        )


else:
    st.markdown('<div class="summary-box"><b>Research signal only.</b> Signal Lab identifies setups worth investigating. It does not provide automatic trading instructions, and every signal should be checked against fundamentals, news, liquidity and personal risk.</div>',unsafe_allow_html=True)

    section("Investigate an asset")
    c1,c2,c3=st.columns([1,1,1])
    with c1:
        market=st.selectbox("Market",["Crypto","Stock / ETF"])
    with c2:
        default_ticker="SOL" if market=="Crypto" else "AAPL"
        raw=st.text_input("Ticker",value=default_ticker)
    with c3:
        period=st.selectbox("History",["1y","2y","5y"],index=1)

    ticker=resolve_ticker(raw,market)

    section("Short-term shift radar")
    short_left, short_right = st.columns([1, 3])
    with short_left:
        short_window = st.selectbox(
            "Shift window",
            ["30-day hourly view", "60-day hourly view"],
            help="Hourly bars help detect changes before they become obvious on daily charts.",
        )
    short_days = 30 if short_window.startswith("30") else 60

    with st.spinner(f"Scanning short-term shifts in {ticker}..."):
        intraday = load_intraday_history(ticker, short_days)
        short_data = add_short_shift_indicators(intraday) if not intraday.empty else pd.DataFrame()
        short_result = short_shift_result(short_data) if not short_data.empty else None

    if short_result is None:
        st.info("Short-term hourly data was unavailable for this ticker.")
    else:
        confidence = (
            "HIGH" if short_result["score"] >= 78 or short_result["score"] <= 22
            else "MEDIUM" if short_result["score"] >= 62 or short_result["score"] <= 38
            else "LOW"
        )
        render_signal_hero(short_result["score"], short_result["label"], confidence)

        cols = st.columns(4)
        with cols[0]: metric("6-hour move", signed(short_result["ret6"]), "Fast directional check")
        with cols[1]: metric("24-hour move", signed(short_result["ret24"]), "Current daily shift")
        with cols[2]: metric("RSI 9", f'{short_result["rsi"]:.1f}', f'6-hour change {short_result["rsi_delta"]:+.1f}')
        with cols[3]: metric("Hourly RVOL", f'{short_result["rvol"]:.2f}×', f'6-hour change {short_result["rvol_delta"]:+.2f}×')

        fast_left, fast_right = st.columns(2)
        with fast_left:
            st.markdown('<div class="signal-card"><div class="asset-head"><b>What is shifting positively</b><span class="badge badge-green">Fast evidence</span></div>', unsafe_allow_html=True)
            if short_result["evidence"]:
                for item in short_result["evidence"]:
                    st.markdown(f"✓ {item}")
            else:
                st.markdown("No strong positive short-term agreement yet.")
            st.markdown("</div>", unsafe_allow_html=True)

        with fast_right:
            st.markdown('<div class="signal-card"><div class="asset-head"><b>What still needs confirmation</b><span class="badge badge-amber">Watch</span></div>', unsafe_allow_html=True)
            if short_result["cautions"]:
                for item in short_result["cautions"]:
                    st.markdown(f"• {item}")
            else:
                st.markdown("No major short-term cautions are present.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.caption(
            "This score uses hourly EMA 9/21/55 structure, RSI 9 direction, fast MACD, "
            "hourly relative volume and 6-hour/24-hour confirmation. It is designed "
            "to identify behavioural shifts early, not replace the broader daily trend."
        )
        st.line_chart(short_result["chart"], use_container_width=True)

    section("Broader trend confirmation")
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
