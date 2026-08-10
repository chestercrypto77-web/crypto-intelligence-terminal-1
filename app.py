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
APP_VERSION = "13.1.0"
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


.live-move-grid{display:grid;grid-template-columns:1.25fr .72fr .72fr .72fr .72fr;gap:.55rem;
align-items:center;background:#1b1f25;border:1px solid var(--line);border-radius:11px;
padding:.68rem .78rem;margin:.4rem 0}
.live-source{font-size:.68rem;color:var(--muted)}
.candle-up{color:#5ee58d;font-weight:850}.candle-down{color:#ff7373;font-weight:850}


.conviction-hero{border-radius:15px;padding:1rem 1.1rem;border:1px solid var(--line);height:100%}
.conviction-strong-buy{background:#123923;border-color:#3d8b59}
.conviction-buy{background:#18364f;border-color:#4d83b0}
.conviction-buy-watch{background:#1d3046;border-color:#4e7195}
.conviction-hold{background:#403814;border-color:#82742f}
.conviction-sell-watch{background:#4a2d18;border-color:#986039}
.conviction-sell{background:#491f25;border-color:#9b4652}
.conviction-strong-sell{background:#38151b;border-color:#b34b59}
.conviction-label{font-size:.75rem;letter-spacing:.12em;text-transform:uppercase;opacity:.78;font-weight:800}
.conviction-call{font-size:1.9rem;font-weight:950;margin:.18rem 0}
.conviction-evidence{font-size:.82rem;opacity:.9}
.check-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.45rem}
.check-item{background:#1a1e24;border:1px solid var(--line);border-radius:9px;padding:.55rem .65rem;font-size:.8rem}
.check-pass{border-left:3px solid #53d38a}.check-fail{border-left:3px solid #ff7272}.check-neutral{border-left:3px solid #f3c765}
.source-chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:.18rem .48rem;margin:.1rem;
font-size:.69rem;color:#dce3eb;background:#1a1e24}
.category-pass{color:#67e59a;font-weight:850}.category-fail{color:#ff8181;font-weight:850}.category-mixed{color:#f0d46d;font-weight:850}
.action-row{display:grid;grid-template-columns:1.05fr .65fr .65fr .65fr 1fr;gap:.5rem;align-items:center;
background:#1b1f25;border:1px solid var(--line);border-radius:11px;padding:.68rem .75rem;margin:.38rem 0}


.research-card{
  background:#1b1f25;border:1px solid #343b45;border-radius:12px;
  padding:.78rem .85rem;margin:.5rem 0
}
.research-head{
  display:grid;grid-template-columns:1.15fr .65fr .65fr .65fr .65fr .65fr;
  gap:.55rem;align-items:center
}
.research-details{
  display:grid;grid-template-columns:1fr 1fr 1fr 1fr;
  gap:.5rem;border-top:1px solid #343b45;margin-top:.62rem;padding-top:.58rem
}
.research-label{font-size:.68rem;color:#94a1b2;text-transform:uppercase;letter-spacing:.06em}
.research-value{font-size:.87rem;font-weight:850;color:#edf2f7}
.research-asset{font-size:1rem;font-weight:950;color:#ffffff}
.research-name{font-size:.72rem;color:#9aa7b6}
.signal-up{color:#55e18a !important;font-weight:900}
.signal-down{color:#ff6f79 !important;font-weight:900}
.signal-watch{color:#70b7ff !important;font-weight:900}
.signal-fade{color:#ffad65 !important;font-weight:900}
.signal-flat{color:#efd36c !important;font-weight:900}
.signal-muted{color:#a1aab7 !important;font-weight:900}
.source-fresh{color:#55e18a;font-weight:800}
.source-aging{color:#efd36c;font-weight:800}
.source-stale{color:#ff7b7b;font-weight:800}
.tab-note{
  background:#181d23;border-left:4px solid #63a7ff;border-radius:8px;
  padding:.7rem .85rem;margin:.45rem 0;color:#dfe7f1
}
.call-badge{
  display:inline-block;border-radius:999px;padding:.22rem .55rem;
  font-size:.72rem;font-weight:900;letter-spacing:.03em
}
.call-buy{background:#163824;color:#75e5a0}
.call-watch{background:#19334e;color:#8ec8ff}
.call-hold{background:#403815;color:#f2d76f}
.call-sell{background:#492027;color:#ff9098}
.outcome-win{color:#55e18a;font-weight:900}
.outcome-loss{color:#ff727b;font-weight:900}
.outcome-flat{color:#efd36c;font-weight:900}
@media(max-width:900px){
  .research-head{grid-template-columns:1fr 1fr}
  .research-details{grid-template-columns:1fr 1fr}
}


.radar-grid{display:grid;grid-template-columns:1.25fr .75fr .75fr .75fr .9fr 1fr;gap:.55rem;align-items:center;background:#1b1f25;border:1px solid #343b45;border-radius:11px;padding:.7rem .78rem;margin:.4rem 0}
.radar-grid:hover{border-color:#566273;background:#20252c}
.radar-asset{font-weight:950;color:#fff;font-size:.95rem}.radar-sub{font-size:.7rem;color:#98a5b4}
.radar-label{font-size:.65rem;color:#8e9aaa;text-transform:uppercase;letter-spacing:.06em}.radar-value{font-size:.84rem;font-weight:850;color:#eef3f8}
.narrative-grid{display:grid;grid-template-columns:1.15fr .7fr .7fr .7fr .8fr;gap:.55rem;align-items:center;background:#191e24;border:1px solid #313842;border-radius:10px;padding:.62rem .72rem;margin:.32rem 0}
.history-card{background:#1a1f25;border:1px solid #343b45;border-radius:12px;padding:.8rem .9rem}
.history-good{border-left:4px solid #53df8d}.history-bad{border-left:4px solid #ff737d}.history-mixed{border-left:4px solid #efd36d}
.change-box{background:#181d23;border-left:4px solid #6aaeff;border-radius:9px;padding:.72rem .85rem;margin:.45rem 0}
@media(max-width:950px){.radar-grid,.narrative-grid{grid-template-columns:1fr 1fr}}

.watch-summary{display:grid;grid-template-columns:repeat(5,1fr);gap:.55rem;margin:.55rem 0 1rem}
.watch-count{background:#1a1f25;border:1px solid #343b45;border-radius:11px;padding:.7rem;text-align:center}
.watch-number{font-size:1.3rem;font-weight:950;color:#fff}.watch-label{font-size:.68rem;color:#9aa7b5;text-transform:uppercase}
.watch-card{display:grid;grid-template-columns:1.2fr .7fr .7fr .7fr .8fr 1fr;gap:.55rem;align-items:center;background:#1b2026;border:1px solid #343b45;border-radius:11px;padding:.72rem .8rem;margin:.38rem 0}
.watch-positive{border-left:4px solid #55e18a}.watch-building{border-left:4px solid #70b7ff}.watch-warning{border-left:4px solid #efd36c}.watch-weakening{border-left:4px solid #ffad65}.watch-risk{border-left:4px solid #ff6f79}
.watch-title{font-weight:950;color:#fff}.watch-sub{font-size:.7rem;color:#98a5b4}.watch-reason{font-size:.73rem;color:#cbd5df}
.heartbeat-good{color:#55e18a;font-weight:900}.heartbeat-bad{color:#ff6f79;font-weight:900}
@media(max-width:950px){.watch-summary{grid-template-columns:1fr 1fr}.watch-card{grid-template-columns:1fr 1fr}}

.asset-front-card{background:#1a1f25;border:1px solid #343b45;border-radius:13px;padding:.82rem .95rem;margin:.42rem 0}
.asset-front-card.good{border-left:4px solid #55e18a}.asset-front-card.info{border-left:4px solid #70b7ff}.asset-front-card.watch{border-left:4px solid #efd36c}.asset-front-card.warn{border-left:4px solid #ffad65}.asset-front-card.risk{border-left:4px solid #ff6f79}
.asset-grid{display:grid;grid-template-columns:1.25fr .72fr .72fr .72fr 1fr;gap:.65rem;align-items:center}
.asset-name{font-size:1rem;font-weight:950;color:#fff}.asset-sub{font-size:.71rem;color:#98a5b4}
.asset-k{font-size:.63rem;color:#8290a0;text-transform:uppercase;letter-spacing:.08em}.asset-v{font-weight:900;color:#fff}
.trade-wallet-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:.6rem;margin:.5rem 0 1rem}
.wallet-tile{background:#1a1f25;border:1px solid #343b45;border-radius:13px;padding:.85rem}
.wallet-tile.good{border-top:4px solid #55e18a}.wallet-tile.info{border-top:4px solid #70b7ff}.wallet-tile.watch{border-top:4px solid #efd36c}.wallet-tile.warn{border-top:4px solid #ffad65}.wallet-tile.risk{border-top:4px solid #ff6f79}
.wallet-name{font-size:.7rem;color:#9aa7b5;text-transform:uppercase}.wallet-value{font-size:1.18rem;font-weight:950;color:#fff}.wallet-note{font-size:.67rem;color:#8fa0b2}
.compact-note{font-size:.72rem;color:#aeb9c5}
@media(max-width:1000px){.asset-grid{grid-template-columns:1fr 1fr}.trade-wallet-grid{grid-template-columns:1fr 1fr}}

.front-trade-card{background:#1a1f25;border:1px solid #343b45;border-radius:13px;padding:.82rem .95rem;margin:.42rem 0}
.front-trade-card.profit{border-left:4px solid #55e18a}
.front-trade-card.active{border-left:4px solid #70b7ff}
.front-trade-card.watch{border-left:4px solid #efd36c}
.front-trade-card.weak{border-left:4px solid #ffad65}
.front-trade-card.loss{border-left:4px solid #ff6f79}
.front-trade-grid{display:grid;grid-template-columns:1.35fr .72fr .72fr .72fr .72fr 1fr;gap:.65rem;align-items:center}
.front-trade-title{font-size:1rem;font-weight:950;color:#fff}
.front-trade-sub{font-size:.7rem;color:#98a5b4}
.front-trade-k{font-size:.62rem;color:#8290a0;text-transform:uppercase;letter-spacing:.08em}
.front-trade-v{font-size:.86rem;font-weight:900;color:#fff}
.strategy-card-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.65rem;margin:.55rem 0}
.strategy-card{background:#1a1f25;border:1px solid #343b45;border-radius:13px;padding:.9rem}
.strategy-card.champion{border-top:4px solid #55e18a}
.strategy-card.challenger{border-top:4px solid #70b7ff}
.strategy-card.collecting{border-top:4px solid #efd36c}
.performance-strip{display:grid;grid-template-columns:repeat(5,1fr);gap:.55rem;margin:.55rem 0 1rem}
.performance-card{background:#1a1f25;border:1px solid #343b45;border-radius:12px;padding:.78rem}
.performance-card.good{border-top:4px solid #55e18a}
.performance-card.bad{border-top:4px solid #ff6f79}
.performance-card.info{border-top:4px solid #70b7ff}
.performance-card.warn{border-top:4px solid #efd36c}
.performance-card.neutral{border-top:4px solid #697583}
.performance-label{font-size:.65rem;color:#8f9dab;text-transform:uppercase}
.performance-value{font-size:1.08rem;font-weight:950;color:#fff}
.performance-note{font-size:.66rem;color:#98a5b4}
@media(max-width:1000px){
.front-trade-grid{grid-template-columns:1fr 1fr}
.strategy-card-grid{grid-template-columns:1fr}
.performance-strip{grid-template-columns:1fr 1fr}
}
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



@st.cache_data(ttl=120, show_spinner=False)
def get_portfolio_intraday() -> dict[str, dict]:
    """Load recent hourly returns for held assets.

    Returns are currency-neutral, so USD hourly data can be used to detect
    direction even though the portfolio valuation is displayed in AUD.
    """
    ticker_to_symbol = {
        ticker: symbol for symbol, ticker in CRYPTO_TICKERS.items()
        if symbol in {holding["symbol"] for holding in PORTFOLIO}
    }
    tickers = sorted(ticker_to_symbol)
    if not tickers:
        return {}

    try:
        raw = yf.download(
            tickers,
            period="5d",
            interval="1h",
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="ticker",
        )
    except Exception:
        return {}

    output = {}
    for ticker, symbol in ticker_to_symbol.items():
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

            if not all(col in frame.columns for col in ["Open", "Close", "Volume"]):
                continue

            frame = frame[["Open", "Close", "Volume"]].dropna(subset=["Close"]).copy()
            if len(frame) < 25:
                continue

            close = frame["Close"].astype(float)
            volume = frame["Volume"].fillna(0).astype(float)
            latest_time = pd.Timestamp(frame.index[-1])
            if latest_time.tzinfo is None:
                latest_time = latest_time.tz_localize("UTC")
            else:
                latest_time = latest_time.tz_convert("UTC")

            now_utc = pd.Timestamp.now(tz="UTC")
            age_minutes = max(0.0, (now_utc - latest_time).total_seconds() / 60)

            def pct(periods: int) -> float:
                if len(close) <= periods or float(close.iloc[-periods-1]) == 0:
                    return 0.0
                return (float(close.iloc[-1]) / float(close.iloc[-periods-1]) - 1) * 100

            rolling_volume = volume.rolling(20).mean().replace(0, np.nan)
            rvol_series = volume / rolling_volume
            current_rvol = float(rvol_series.iloc[-1]) if pd.notna(rvol_series.iloc[-1]) else 1.0
            previous_rvol = float(rvol_series.iloc[-7]) if len(rvol_series) >= 7 and pd.notna(rvol_series.iloc[-7]) else current_rvol

            last_six = frame.tail(6)
            green_candles = int((last_six["Close"] > last_six["Open"]).sum())
            red_candles = int((last_six["Close"] < last_six["Open"]).sum())

            output[symbol] = {
                "change_1h": pct(1),
                "change_6h": pct(6),
                "change_24h": pct(24),
                "hourly_rvol": current_rvol,
                "hourly_rvol_delta": current_rvol - previous_rvol,
                "green_candles_6h": green_candles,
                "red_candles_6h": red_candles,
                "latest_time": latest_time.isoformat(),
                "age_minutes": age_minutes,
                "fresh": age_minutes <= 240,
            }
        except Exception:
            continue
    return output


def parse_last_updated(value) -> pd.Timestamp | None:
    try:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")
        return timestamp
    except Exception:
        return None



def build_portfolio(rows: list[dict], intraday: dict[str, dict] | None = None) -> dict:
    row_map = {str(row.get("id")): row for row in rows}
    intraday = intraday or {}
    items, total = [], 0.0
    for holding in PORTFOLIO:
        row = row_map.get(holding["coin_id"], {})
        price = float(row.get("current_price") or 0)
        cg_ch24 = float(row.get("price_change_percentage_24h") or 0)
        ch7 = float(row.get("price_change_percentage_7d_in_currency") or cg_ch24)
        volume = float(row.get("total_volume") or 0)
        market_cap = float(row.get("market_cap") or 1)

        hourly = intraday.get(holding["symbol"], {})
        cg_updated = parse_last_updated(row.get("last_updated"))
        now_utc = pd.Timestamp.now(tz="UTC")
        cg_age_minutes = (
            max(0.0, (now_utc - cg_updated).total_seconds() / 60)
            if cg_updated is not None else 999999.0
        )
        hourly_fresh = bool(hourly.get("fresh"))
        hourly_age = float(hourly.get("age_minutes", 999999.0))

        # Use the freshest available 24-hour return. This avoids a stale provider
        # masking a fast move that is already visible in hourly candles.
        use_hourly_move = hourly_fresh and (
            cg_age_minutes > 20
            or hourly_age + 10 < cg_age_minutes
            or abs(float(hourly.get("change_24h", 0)) - cg_ch24) >= 3.0
        )
        ch24 = float(hourly.get("change_24h", cg_ch24)) if use_hourly_move else cg_ch24
        ch1 = float(hourly.get("change_1h", 0.0))
        ch6 = float(hourly.get("change_6h", ch24 / 4))
        hourly_rvol = float(hourly.get("hourly_rvol", 1.0))
        hourly_rvol_delta = float(hourly.get("hourly_rvol_delta", 0.0))
        rvol = hourly_rvol if hourly_fresh else clamp(
            .70 + (volume/max(market_cap,1))*8 + abs(ch24)/25, .35, 3.0
        )
        move_source = "Hourly candles" if use_hourly_move else "CoinGecko"
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
        items.append({**holding,"price":price,"value":value,
                      "change_1h":ch1,"change_6h":ch6,"change_24h":ch24,"change_7d":ch7,
                      "coin_gecko_24h":cg_ch24,"volume":volume,"rvol":rvol,
                      "rvol_delta":hourly_rvol_delta,
                      "green_candles_6h":int(hourly.get("green_candles_6h",0)),
                      "red_candles_6h":int(hourly.get("red_candles_6h",0)),
                      "move_source":move_source,
                      "data_age_minutes":hourly_age if use_hourly_move else cg_age_minutes,
                      "momentum":momentum,"momentum_score":momentum_score,
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
    attention = sorted(items, key=lambda x:(abs(x["change_6h"]), abs(x["change_24h"]), x["rvol"]), reverse=True)[:6]
    opportunities = sorted(items, key=lambda x:(x["change_6h"], x["change_24h"], x["rvol_delta"]), reverse=True)[:6]
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
        ("CFG", "Centrifuge", "CFG-USD"),
    ],
    "AI": [
        ("FET", "Artificial Superintelligence Alliance", "FET-USD"),
        ("RENDER", "Render", "RENDER-USD"), ("TAO", "Bittensor", "TAO22974-USD"),
        ("NEAR", "NEAR Protocol", "NEAR-USD"), ("AKT", "Akash Network", "AKT-USD"),
    ],
    "Layer 1": [
        ("SOL", "Solana", "SOL-USD"), ("SUI", "Sui", "SUI20947-USD"),
        ("AVAX", "Avalanche", "AVAX-USD"), ("SEI", "Sei", "SEI-USD"),
        ("ADA", "Cardano", "ADA-USD"),
    ],
    "Layer 2 / Scaling": [
        ("POL", "Polygon", "POL-USD"), ("ARB", "Arbitrum", "ARB11841-USD"),
        ("OP", "Optimism", "OP-USD"), ("IMX", "Immutable", "IMX10603-USD"),
        ("LRC", "Loopring", "LRC-USD"),
    ],
    "DeFi / DEX": [
        ("AAVE", "Aave", "AAVE-USD"), ("UNI", "Uniswap", "UNI7083-USD"),
        ("RUNE", "THORChain", "RUNE-USD"), ("AERO", "Aerodrome", "AERO29270-USD"),
        ("CRV", "Curve DAO", "CRV-USD"),
    ],
    "DePIN / Storage": [
        ("FIL", "Filecoin", "FIL-USD"), ("AR", "Arweave", "AR-USD"),
        ("AIOZ", "AIOZ Network", "AIOZ-USD"), ("HNT", "Helium", "HNT-USD"),
        ("GRT", "The Graph", "GRT-USD"),
    ],
    "Gaming / Metaverse": [
        ("IMX", "Immutable", "IMX10603-USD"), ("SUPER", "SuperVerse", "SUPER-USD"),
        ("GALA", "Gala", "GALA-USD"), ("SAND", "The Sandbox", "SAND-USD"),
        ("ENJ", "Enjin Coin", "ENJ-USD"),
    ],
    "Privacy / Payments": [
        ("COTI", "COTI", "COTI-USD"), ("XMR", "Monero", "XMR-USD"),
        ("ZEC", "Zcash", "ZEC-USD"), ("XLM", "Stellar", "XLM-USD"),
        ("XRP", "XRP", "XRP-USD"),
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



def render_market_top_five_row(rank: int, item: dict) -> None:
    price_arrow, price_colour = direction_arrow(item["ret24"])
    volume_arrow, volume_colour = direction_arrow(item["rvol_delta"], 0.10)
    held = f'{item["portfolio_weight"]:.1f}%' if item["in_portfolio"] else "—"
    st.markdown(
        f'<div class="fourh-grid">'
        f'<div><div class="fourh-asset">{rank}. {esc(item["symbol"])} · {esc(item["name"])}</div>'
        f'<div class="fourh-name">Portfolio weight {held}</div></div>'
        f'<div><span class="flow-arrow flow-{price_colour}">{price_arrow}</span> '
        f'<b>{signed(item["ret24"])}</b><div class="fourh-name">24-hour price</div></div>'
        f'<div><span class="flow-arrow flow-{volume_colour}">{volume_arrow}</span> '
        f'<b>{item["rvol_delta"]:+.2f}×</b><div class="fourh-name">RVOL change</div></div>'
        f'<div><b>{item["rvol"]:.2f}×</b><div class="fourh-name">Current RVOL</div></div>'
        f'<div>{render_flow_arrow(item["flow"])} <b>{esc(item["flow"]["label"])}</b>'
        f'<div class="fourh-name">Volume flow</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )




def render_live_move_row(rank: int, item: dict) -> None:
    arrow1, colour1 = direction_arrow(item.get("change_1h", 0))
    arrow6, colour6 = direction_arrow(item.get("change_6h", 0))
    arrow24, colour24 = direction_arrow(item.get("change_24h", 0))
    candle_text = (
        f'{item.get("green_candles_6h",0)} green / {item.get("red_candles_6h",0)} red'
        if item.get("green_candles_6h",0) or item.get("red_candles_6h",0)
        else "No candle count"
    )
    age = item.get("data_age_minutes", 0)
    source_text = f'{item.get("move_source","Market data")} · {age:.0f} min old'
    st.markdown(
        f'<div class="live-move-grid">'
        f'<div><div class="fourh-asset">{rank}. {esc(item["symbol"])} · {esc(item["name"])}</div>'
        f'<div class="live-source">{esc(source_text)}</div></div>'
        f'<div><span class="flow-arrow flow-{colour1}">{arrow1}</span> '
        f'<b>{signed(item.get("change_1h",0))}</b><div class="fourh-name">1 hour</div></div>'
        f'<div><span class="flow-arrow flow-{colour6}">{arrow6}</span> '
        f'<b>{signed(item.get("change_6h",0))}</b><div class="fourh-name">6 hours</div></div>'
        f'<div><span class="flow-arrow flow-{colour24}">{arrow24}</span> '
        f'<b>{signed(item.get("change_24h",0))}</b><div class="fourh-name">24 hours</div></div>'
        f'<div><b>{item.get("rvol",1):.2f}×</b><div class="fourh-name">RVOL · {esc(candle_text)}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )



def render_objective_card(item: dict, title: str) -> None:
    flow = volume_flow(item.get("change_6h", item["change_24h"]), item.get("rvol_delta",0.0), item["rvol"])
    price_arrow, price_colour = direction_arrow(item.get("change_6h", item["change_24h"]))
    st.markdown(
        f'<div class="objective-card"><div class="objective-title">{esc(title)}</div>'
        f'<div class="objective-main">{esc(item["symbol"])} '
        f'<span class="flow-arrow flow-{price_colour}">{price_arrow}</span></div>'
        f'<div class="objective-row"><span>6-hour price</span><b>{signed(item.get("change_6h",0))}</b></div>'f'<div class="objective-row"><span>24-hour price</span><b>{signed(item["change_24h"])}</b></div>'
        f'<div class="objective-row"><span>7-day price</span><b>{signed(item["change_7d"])}</b></div>'
        f'<div class="objective-row"><span>Relative volume</span><b>{item["rvol"]:.2f}×</b></div>'
        f'<div class="objective-row"><span>Volume flow</span><b>{render_flow_arrow(flow)} {esc(flow["label"])}</b></div>'
        f'</div>',
        unsafe_allow_html=True,
    )



# ---------- V6 unified conviction engine ----------

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


@st.cache_data(ttl=120, show_spinner=False)
def load_binance_4h(symbol: str, limit: int = 220) -> pd.DataFrame:
    pair = f"{symbol.upper()}USDT"
    try:
        response = requests.get(
            BINANCE_KLINES_URL,
            params={"symbol": pair, "interval": "4h", "limit": limit},
            timeout=8,
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            return pd.DataFrame()
        frame = pd.DataFrame(rows, columns=[
            "Open time","Open","High","Low","Close","Volume","Close time",
            "Quote volume","Trades","Taker base","Taker quote","Ignore",
        ])
        frame.index = pd.to_datetime(frame["Open time"], unit="ms", utc=True)
        for column in ["Open","High","Low","Close","Volume"]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def resample_hourly_to_4h(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    x = frame.copy()
    try:
        index = pd.to_datetime(x.index, utc=True)
        x.index = index
        result = x.resample("4h").agg({
            "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
        }).dropna(subset=["Close"])
        return result
    except Exception:
        return pd.DataFrame()


def source_freshness(frame: pd.DataFrame) -> float:
    if frame is None or frame.empty:
        return 999999.0
    try:
        latest = pd.Timestamp(frame.index[-1])
        if latest.tzinfo is None:
            latest = latest.tz_localize("UTC")
        else:
            latest = latest.tz_convert("UTC")
        return max(0.0, (pd.Timestamp.now(tz="UTC") - latest).total_seconds() / 60)
    except Exception:
        return 999999.0


def prepare_conviction_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    x = frame.copy()
    close = x["Close"].astype(float)
    high = x["High"].astype(float)
    low = x["Low"].astype(float)
    volume = x["Volume"].fillna(0).astype(float)

    x["EMA9"] = close.ewm(span=9, adjust=False).mean()
    x["EMA21"] = close.ewm(span=21, adjust=False).mean()
    x["EMA55"] = close.ewm(span=55, adjust=False).mean()
    x["EMA200"] = close.ewm(span=200, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x["RSI14"] = 100 - (100 / (1 + rs))
    x["RSI_DELTA3"] = x["RSI14"] - x["RSI14"].shift(3)

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["MACD_SIGNAL"] = x["MACD"].ewm(span=9, adjust=False).mean()
    x["MACD_HIST"] = x["MACD"] - x["MACD_SIGNAL"]
    x["MACD_ACCEL"] = x["MACD_HIST"] - x["MACD_HIST"].shift(2)

    previous_close = close.shift(1)
    true_range = pd.concat([
        high-low, (high-previous_close).abs(), (low-previous_close).abs()
    ], axis=1).max(axis=1)
    x["ATR14"] = true_range.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    x["ATR_PCT"] = x["ATR14"] / close.replace(0, np.nan) * 100

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr = x["ATR14"].replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1/14, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/14, adjust=False).mean() / atr
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di).replace(0, np.nan)
    x["ADX14"] = dx.ewm(alpha=1/14, adjust=False).mean()
    x["PLUS_DI"] = plus_di
    x["MINUS_DI"] = minus_di

    x["RVOL20"] = volume / volume.rolling(20).mean().replace(0, np.nan)
    x["RVOL_DELTA3"] = x["RVOL20"] - x["RVOL20"].shift(3)
    x["RET1"] = close.pct_change(1) * 100
    x["RET3"] = close.pct_change(3) * 100
    x["RET6"] = close.pct_change(6) * 100
    x["GREEN6"] = (close > x["Open"]).rolling(6).sum()
    x["RED6"] = (close < x["Open"]).rolling(6).sum()
    x["PRIOR_HIGH6"] = high.shift(1).rolling(6).max()
    x["PRIOR_LOW6"] = low.shift(1).rolling(6).min()
    x["BREAKOUT"] = close > x["PRIOR_HIGH6"]
    x["BREAKDOWN"] = close < x["PRIOR_LOW6"]
    x["HIGHER_HIGH"] = high.rolling(3).max() > high.shift(3).rolling(3).max()
    x["HIGHER_LOW"] = low.rolling(3).min() > low.shift(3).rolling(3).min()
    x["LOWER_HIGH"] = high.rolling(3).max() < high.shift(3).rolling(3).max()
    x["LOWER_LOW"] = low.rolling(3).min() < low.shift(3).rolling(3).min()
    return x


def conviction_signal(frame: pd.DataFrame, btc_return: float = 0.0) -> dict | None:
    x = prepare_conviction_indicators(frame)
    valid = x.dropna(subset=[
        "EMA9","EMA21","EMA55","RSI14","MACD_HIST","RVOL20","RET3","RET6"
    ])
    if valid.empty:
        return None
    row = valid.iloc[-1]
    prev = valid.iloc[-2] if len(valid) > 1 else row
    close = float(row["Close"])

    conditions = [
        ("Price above EMA 9", close > row["EMA9"], close < row["EMA9"], "Trend"),
        ("EMA 9 above EMA 21", row["EMA9"] > row["EMA21"], row["EMA9"] < row["EMA21"], "Trend"),
        ("EMA 21 above EMA 55", row["EMA21"] > row["EMA55"], row["EMA21"] < row["EMA55"], "Trend"),
        ("MACD histogram positive", row["MACD_HIST"] > 0, row["MACD_HIST"] < 0, "Momentum"),
        ("MACD momentum accelerating", row["MACD_ACCEL"] > 0, row["MACD_ACCEL"] < 0, "Momentum"),
        ("RSI strengthening", 50 <= row["RSI14"] <= 78 and row["RSI_DELTA3"] > 0,
         row["RSI14"] < 45 and row["RSI_DELTA3"] < 0, "Momentum"),
        ("Relative volume above normal", row["RVOL20"] >= 1.15, row["RVOL20"] < 0.70, "Volume"),
        ("Relative volume increasing", row["RVOL_DELTA3"] > 0.10, row["RVOL_DELTA3"] < -0.10, "Volume"),
        ("Majority of recent candles green", row["GREEN6"] >= 4, row["RED6"] >= 4, "Volume"),
        ("Three-candle price direction positive", row["RET3"] > 0, row["RET3"] < 0, "Structure"),
        ("Higher-high structure", bool(row["HIGHER_HIGH"]), bool(row["LOWER_HIGH"]), "Structure"),
        ("Higher-low structure", bool(row["HIGHER_LOW"]), bool(row["LOWER_LOW"]), "Structure"),
        ("Breakout above prior range", bool(row["BREAKOUT"]), bool(row["BREAKDOWN"]), "Structure"),
        ("Outperforming Bitcoin", row["RET6"] > btc_return + 1.0, row["RET6"] < btc_return - 1.0, "Relative strength"),
    ]

    bullish = sum(1 for _, bull, _, _ in conditions if bool(bull))
    bearish = sum(1 for _, _, bear, _ in conditions if bool(bear))
    category = {}
    for _, bull, bear, group in conditions:
        stats = category.setdefault(group, {"bull":0,"bear":0,"total":0})
        stats["total"] += 1
        stats["bull"] += int(bool(bull))
        stats["bear"] += int(bool(bear))

    trend_pass = category["Trend"]["bull"] >= 2
    volume_pass = category["Volume"]["bull"] >= 2
    bearish_trend = category["Trend"]["bear"] >= 2
    bearish_volume = category["Volume"]["bear"] >= 2

    # Decisive calls, but only when several independent categories agree.
    if bullish >= 10 and bearish <= 2 and trend_pass and volume_pass:
        signal = "STRONG BUY"
    elif bullish >= 8 and bearish <= 3 and trend_pass:
        signal = "BUY"
    elif bullish >= 6 and bearish <= 4:
        signal = "BUY WATCH"
    elif bearish >= 10 and bullish <= 2 and bearish_trend and bearish_volume:
        signal = "STRONG SELL"
    elif bearish >= 8 and bullish <= 3 and bearish_trend:
        signal = "SELL"
    elif bearish >= 6 and bullish <= 4:
        signal = "SELL WATCH"
    else:
        signal = "HOLD"

    class_name = signal.lower().replace(" ", "-")
    evidence = []
    contrary = []
    for name, bull, bear, group in conditions:
        if bool(bull):
            evidence.append({"name":name,"group":group,"state":"bull"})
        elif bool(bear):
            contrary.append({"name":name,"group":group,"state":"bear"})
        else:
            contrary.append({"name":name,"group":group,"state":"neutral"})

    category_states = {}
    for group, stats in category.items():
        if stats["bull"] > stats["bear"] and stats["bull"] >= max(1, stats["total"]//2):
            category_states[group] = "PASS"
        elif stats["bear"] > stats["bull"] and stats["bear"] >= max(1, stats["total"]//2):
            category_states[group] = "FAIL"
        else:
            category_states[group] = "MIXED"

    return {
        "signal":signal,
        "class_name":class_name,
        "bullish":bullish,
        "bearish":bearish,
        "total":len(conditions),
        "conditions":conditions,
        "evidence":evidence,
        "contrary":contrary,
        "categories":category_states,
        "close":close,
        "ret4h":float(row["RET1"]),
        "ret12h":float(row["RET3"]),
        "ret24h":float(row["RET6"]),
        "rsi":float(row["RSI14"]),
        "rsi_delta":float(row["RSI_DELTA3"]),
        "rvol":float(row["RVOL20"]),
        "rvol_delta":float(row["RVOL_DELTA3"]),
        "adx":float(row["ADX14"]) if pd.notna(row["ADX14"]) else np.nan,
        "atr_pct":float(row["ATR_PCT"]) if pd.notna(row["ATR_PCT"]) else np.nan,
        "green6":int(row["GREEN6"]) if pd.notna(row["GREEN6"]) else 0,
        "red6":int(row["RED6"]) if pd.notna(row["RED6"]) else 0,
        "breakout":bool(row["BREAKOUT"]),
        "breakdown":bool(row["BREAKDOWN"]),
        "chart":valid[["Close","EMA9","EMA21","EMA55"]].tail(120),
        "latest_time":pd.Timestamp(valid.index[-1]),
    }


@st.cache_data(ttl=120, show_spinner=False)
def unified_asset_intelligence(symbol: str, ticker: str) -> dict:
    sources = []
    yahoo_hourly = load_intraday_history(ticker, 30)
    yahoo_4h = resample_hourly_to_4h(yahoo_hourly)
    if not yahoo_4h.empty:
        sources.append({
            "name":"Yahoo Finance",
            "frame":yahoo_4h,
            "age":source_freshness(yahoo_4h),
            "candles":len(yahoo_4h),
        })

    binance = load_binance_4h(symbol)
    if not binance.empty:
        sources.append({
            "name":"Binance",
            "frame":binance,
            "age":source_freshness(binance),
            "candles":len(binance),
        })

    if not sources:
        return {"symbol":symbol,"ticker":ticker,"sources":[],"primary":None,"confirmation":None}

    sources.sort(key=lambda item:(item["age"], -item["candles"]))
    primary = sources[0]
    primary_signal = conviction_signal(primary["frame"])

    confirmations = []
    for source in sources[1:]:
        result = conviction_signal(source["frame"])
        if result:
            confirmations.append({"source":source["name"],"result":result,"age":source["age"]})

    agreement = "SINGLE SOURCE"
    if primary_signal and confirmations:
        matching = sum(1 for item in confirmations if item["result"]["signal"] == primary_signal["signal"])
        same_direction = sum(
            1 for item in confirmations
            if ("BUY" in item["result"]["signal"]) == ("BUY" in primary_signal["signal"])
            and ("SELL" in item["result"]["signal"]) == ("SELL" in primary_signal["signal"])
        )
        if matching == len(confirmations):
            agreement = "FULL AGREEMENT"
        elif same_direction >= 1:
            agreement = "DIRECTION AGREEMENT"
        else:
            agreement = "SOURCE CONFLICT"

    return {
        "symbol":symbol,
        "ticker":ticker,
        "sources":[{"name":x["name"],"age":x["age"],"candles":x["candles"]} for x in sources],
        "primary_source":primary["name"],
        "primary":primary_signal,
        "confirmations":confirmations,
        "agreement":agreement,
    }


def render_conviction_hero(symbol: str, result: dict, source: str, agreement: str) -> None:
    st.markdown(
        f'<div class="conviction-hero conviction-{result["class_name"]}">'
        f'<div class="conviction-label">{esc(symbol)} · Four-hour conviction call</div>'
        f'<div class="conviction-call">{esc(result["signal"])}</div>'
        f'<div class="conviction-evidence">{result["bullish"]} bullish conditions · '
        f'{result["bearish"]} bearish conditions · {esc(agreement)} · {esc(source)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_category_states(states: dict) -> None:
    cols = st.columns(len(states))
    for col, (name, state) in zip(cols, states.items()):
        css = "category-pass" if state=="PASS" else "category-fail" if state=="FAIL" else "category-mixed"
        with col:
            st.markdown(
                f'<div class="objective-card"><div class="objective-title">{esc(name)}</div>'
                f'<div class="objective-main {css}">{esc(state)}</div></div>',
                unsafe_allow_html=True,
            )


def render_signal_checklist(result: dict) -> None:
    blocks = []
    for name, bull, bear, group in result["conditions"]:
        if bool(bull):
            css, marker = "check-pass", "✓"
        elif bool(bear):
            css, marker = "check-fail", "✕"
        else:
            css, marker = "check-neutral", "—"
        blocks.append(
            f'<div class="check-item {css}"><b>{marker} {esc(name)}</b>'
            f'<div class="fourh-name">{esc(group)}</div></div>'
        )
    st.markdown('<div class="check-grid">' + "".join(blocks) + '</div>', unsafe_allow_html=True)


def render_action_row(rank: int, item: dict) -> None:
    result = item["intelligence"]["primary"]
    age = min((x["age"] for x in item["intelligence"]["sources"]), default=999999)
    st.markdown(
        f'<div class="action-row">'
        f'<div><div class="fourh-asset">{rank}. {esc(item["symbol"])}</div>'
        f'<div class="fourh-name">{esc(item.get("name",""))} · {esc(item.get("narrative",""))}</div></div>'
        f'<div><b>{esc(result["signal"])}</b><div class="fourh-name">Call</div></div>'
        f'<div><b>{signed(result["ret4h"])}</b><div class="fourh-name">4 hours</div></div>'
        f'<div><b>{result["rvol"]:.2f}×</b><div class="fourh-name">RVOL</div></div>'
        f'<div><b>{result["bullish"]} bull / {result["bearish"]} bear</b>'
        f'<div class="fourh-name">{esc(item["intelligence"]["agreement"])} · {age:.0f} min</div></div>'
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



SIGNALS_LATEST_FILE = Path(__file__).with_name("data") / "signals_latest.json"
SIGNAL_HISTORY_FILE = Path(__file__).with_name("data") / "signal_history.json"
PAPER_TRADES_FILE = Path(__file__).with_name("data") / "paper_trades.json"
EXTERNAL_CALLS_FILE = Path(__file__).with_name("data") / "external_calls.json"
EXTERNAL_INBOX_FILE = Path(__file__).with_name("data") / "external_inbox.json"
EXTERNAL_STATUS_FILE = Path(__file__).with_name("data") / "external_monitor_status.json"
EXTERNAL_SOURCES_FILE = Path(__file__).with_name("config") / "external_sources.json"
EVIDENCE_LEDGER_FILE = Path(__file__).with_name("data") / "evidence_ledger.json"
SIGNAL_LIFECYCLE_FILE = Path(__file__).with_name("data") / "signal_lifecycle.json"
RESEARCH_WALLET_FILE = Path(__file__).with_name("data") / "research_wallet.json"
STRATEGY_REGISTRY_FILE = Path(__file__).with_name("data") / "strategy_registry.json"
ENGINE_HEALTH_FILE = Path(__file__).with_name("data") / "engine_health.json"
STRATEGY_LAB_FILE = Path(__file__).with_name("data") / "strategy_lab.json"
RISK_GUARDIAN_FILE = Path(__file__).with_name("data") / "risk_guardian.json"
RISK_HISTORY_FILE = Path(__file__).with_name("data") / "risk_history.json"
OBSERVER_LATEST_FILE = Path(__file__).with_name("data") / "observer_latest.json"
OBSERVER_HISTORY_FILE = Path(__file__).with_name("data") / "observer_history.json"
OBSERVER_WALLET_FILE = Path(__file__).with_name("data") / "observer_wallet.json"
SIGNAL_TIMING_FILE = Path(__file__).with_name("data") / "signal_timing.json"
SCALP_WALLET_FILE = Path(__file__).with_name("data") / "scalp_wallet.json"
SCALP_CHECKPOINTS_FILE = Path(__file__).with_name("data") / "scalp_checkpoints.json"
SCALP_LEARNING_FILE = Path(__file__).with_name("data") / "scalp_learning.json"
TRADE_LESSONS_FILE = Path(__file__).with_name("data") / "trade_lessons.json"
TRADE_REVIEWS_FILE = Path(__file__).with_name("data") / "trade_reviews.json"
LEARNING_STATE_FILE = Path(__file__).with_name("data") / "learning_state.json"
TRADE_DIAGNOSTICS_FILE = Path(__file__).with_name("data") / "trade_diagnostics.json"
CHALLENGER_ARENA_FILE = Path(__file__).with_name("data") / "challenger_arena.json"
INTELLIGENCE_BUS_FILE = Path(__file__).with_name("data") / "intelligence_bus.json"
MARKET_SCHOOL_FILE = Path(__file__).with_name("data") / "market_school.json"
MICROSTRUCTURE_FILE = Path(__file__).with_name("data") / "microstructure_latest.json"
PORTFOLIO_MANAGER_FILE = Path(__file__).with_name("data") / "portfolio_manager.json"
FUND_STATE_FILE = Path(__file__).with_name("data") / "fund_state.json"
SWING_WALLET_FILE = Path(__file__).with_name("data") / "swing_wallet.json"
CORE_WALLET_FILE = Path(__file__).with_name("data") / "core_wallet.json"

def read_runtime_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def trade_live_return(trade: dict, current_prices: dict[str,float]):
    entry=float(trade.get("entry_price") or 0); current=float(current_prices.get(trade.get("symbol"),0) or 0)
    if entry<=0 or current<=0: return None
    raw=(current/entry-1)*100
    return raw if trade.get("direction")=="LONG" else -raw


def checkpoint_return(trade,key):
    value=(trade.get("returns") or {}).get(key)
    return value.get("return") if isinstance(value,dict) else value

def evaluated_return(trade):
    if trade.get("status")=="CLOSED" and trade.get("final_return") is not None:
        return float(trade["final_return"])
    for key in ["7d","3d","1d","12h","4h","1h"]:
        value=checkpoint_return(trade,key)
        if value is not None: return float(value)
    value=trade.get("current_return")
    return float(value) if value is not None else None

def performance_summary(trades):
    results=[evaluated_return(t) for t in trades]
    results=[x for x in results if x is not None]
    wins=[x for x in results if x>.25]; losses=[x for x in results if x<-.25]
    gp=sum(wins); gl=abs(sum(losses))
    return {"calls":len(trades),"evaluated":len(results),"wins":len(wins),"losses":len(losses),
      "win_rate":len(wins)/len(results)*100 if results else 0,
      "average_return":sum(results)/len(results) if results else 0,
      "average_winner":sum(wins)/len(wins) if wins else 0,
      "average_loser":sum(losses)/len(losses) if losses else 0,
      "profit_factor":gp/gl if gl else (float("inf") if gp else 0)}

def html_signal(value: float, threshold: float = .15) -> str:
    arrow, colour = direction_arrow(float(value or 0), threshold)
    css = {
        "up":"signal-up","down":"signal-down","watch":"signal-watch",
        "fade":"signal-fade","flat":"signal-flat","muted":"signal-muted"
    }.get(colour, "signal-muted")
    return f'<span class="{css}">{arrow} {signed(float(value or 0))}</span>'

def html_flow(flow: dict) -> str:
    css = {
        "up":"signal-up","down":"signal-down","watch":"signal-watch",
        "fade":"signal-fade","flat":"signal-flat","muted":"signal-muted"
    }.get(flow.get("colour"), "signal-muted")
    return f'<span class="{css}">{esc(flow.get("arrow","→"))} {esc(flow.get("label","Stable"))}</span>'

def freshness_html(age_minutes: float) -> str:
    age = float(age_minutes or 0)
    css = "source-fresh" if age <= 15 else "source-aging" if age <= 90 else "source-stale"
    return f'<span class="{css}">{age:.0f} min</span>'

def call_badge(call: str) -> str:
    value = str(call or "HOLD").upper()
    if "BUY" in value and "WATCH" not in value:
        css = "call-buy"
    elif "SELL" in value:
        css = "call-sell"
    elif "WATCH" in value:
        css = "call-watch"
    else:
        css = "call-hold"
    return f'<span class="call-badge {css}">{esc(value)}</span>'

def outcome_html(value: str) -> str:
    text = str(value or "PENDING").upper()
    css = "outcome-win" if text == "WIN" else "outcome-loss" if text == "LOSS" else "outcome-flat"
    return f'<span class="{css}">{esc(text)}</span>'


def safe_float(value, default=0.0):
    try:
        number=float(value)
        return number if math.isfinite(number) else default
    except Exception:
        return default

def wallet_start(wallet):
    return safe_float(wallet.get("starting_cash") or wallet.get("starting_capital") or 100000,100000)

def wallet_equity(wallet):
    return safe_float(wallet.get("equity") or wallet_start(wallet),wallet_start(wallet))

def wallet_return_pct(wallet):
    start=wallet_start(wallet)
    return (wallet_equity(wallet)/start-1)*100 if start else 0.0

def signal_priority_value(call: str) -> int:
    return {
        "STRONG BUY": 7, "BUY": 6, "BUY WATCH": 5, "HOLD": 4,
        "SELL WATCH": 3, "SELL": 2, "STRONG SELL": 1,
    }.get(str(call or "HOLD").upper(), 0)

def historical_asset_stats(symbol: str, trades: list[dict]) -> dict:
    relevant=[t for t in trades if str(t.get("symbol","")).upper()==symbol.upper()]
    results=[evaluated_return(t) for t in relevant]
    results=[x for x in results if x is not None]
    wins=[x for x in results if x>.25]
    losses=[x for x in results if x<-.25]
    return {
        "calls":len(relevant),"evaluated":len(results),"wins":len(wins),"losses":len(losses),
        "win_rate":len(wins)/len(results)*100 if results else 0.0,
        "average":sum(results)/len(results) if results else 0.0,
        "best":max(results) if results else None,"worst":min(results) if results else None,
        "trades":relevant,
    }

def latest_signal_change(symbol: str, history: list[dict]) -> dict | None:
    records=[x for x in history if str(x.get("symbol","")).upper()==symbol.upper()]
    if not records: return None
    records=sorted(records,key=lambda x:str(x.get("recorded_at","")))
    latest=records[-1]; previous=records[-2] if len(records)>1 else None
    changes=[]
    if previous:
        if latest.get("signal")!=previous.get("signal"):
            changes.append(f'Call changed from {previous.get("signal")} to {latest.get("signal")}')
        if float(latest.get("rvol",0) or 0)>float(previous.get("rvol",0) or 0)+.2:
            changes.append("Relative volume increased")
        if float(latest.get("return_4h",0) or 0)>float(previous.get("return_4h",0) or 0)+1:
            changes.append("Four-hour price momentum improved")
        if float(latest.get("bullish",0) or 0)>float(previous.get("bullish",0) or 0):
            changes.append("More bullish checklist conditions are passing")
        if float(latest.get("bearish",0) or 0)>float(previous.get("bearish",0) or 0):
            changes.append("More bearish checklist conditions are passing")
    return {"latest":latest,"previous":previous,"changes":changes}

def external_agreement_for_asset(symbol: str, calls: list[dict], current_call: str) -> dict:
    relevant=[c for c in calls if str(c.get("symbol","")).upper()==symbol.upper() and c.get("status","ACTIVE")=="ACTIVE"]
    engine_side="BUY" if "BUY" in current_call else "SELL" if "SELL" in current_call else "HOLD"
    agree=disagree=0; items=[]
    for call in relevant:
        external_side="BUY" if "BUY" in str(call.get("call","")).upper() else "SELL" if "SELL" in str(call.get("call","")).upper() else "HOLD"
        matched=external_side==engine_side and engine_side!="HOLD"
        agree+=int(matched); disagree+=int(not matched and external_side!="HOLD")
        items.append({**call,"agreement":"AGREE" if matched else "DISAGREE" if external_side!="HOLD" else "NEUTRAL"})
    return {"count":len(relevant),"agree":agree,"disagree":disagree,"items":items}

def render_radar_row(rank: int, item: dict) -> None:
    result=item["intelligence"]["primary"]
    agreement=item["intelligence"].get("agreement","SINGLE SOURCE")
    age=min((s["age"] for s in item["intelligence"].get("sources",[])),default=999999)
    st.markdown(
        f'<div class="radar-grid"><div><div class="radar-asset">{rank}. {esc(item["symbol"])} · {esc(item.get("name",""))}</div>'
        f'<div class="radar-sub">{esc(item.get("narrative",""))} · {esc(agreement)}</div></div>'
        f'<div><div class="radar-label">Call</div><div class="radar-value">{call_badge(result["signal"])}</div></div>'
        f'<div><div class="radar-label">4H</div><div class="radar-value">{html_signal(result["ret4h"])}</div></div>'
        f'<div><div class="radar-label">24H</div><div class="radar-value">{html_signal(result["ret24h"])}</div></div>'
        f'<div><div class="radar-label">RVOL</div><div class="radar-value">{result["rvol"]:.2f}×</div></div>'
        f'<div><div class="radar-label">Evidence</div><div class="radar-value">{result["bullish"]} bull / {result["bearish"]} bear</div>'
        f'<div class="radar-sub">{age:.0f} min old</div></div></div>',unsafe_allow_html=True)

def narrative_flow_state(items: list[dict]) -> dict:
    buys=sum(1 for x in items if "BUY" in x["intelligence"]["primary"]["signal"])
    sells=sum(1 for x in items if "SELL" in x["intelligence"]["primary"]["signal"])
    avg4=sum(x["intelligence"]["primary"]["ret4h"] for x in items)/len(items) if items else 0
    avgrvol=sum(x["intelligence"]["primary"]["rvol"] for x in items)/len(items) if items else 0
    if buys>sells and avg4>0: return {"label":"RISING","arrow":"↑"}
    if sells>buys and avg4<0: return {"label":"NEGATIVE","arrow":"↓"}
    if avgrvol>1.2: return {"label":"ACTIVE / MIXED","arrow":"↕"}
    return {"label":"MIXED","arrow":"→"}

st.set_page_config(page_title=APP_NAME,page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown(CSS,unsafe_allow_html=True)
market_rows, source = get_market_rows()
portfolio_intraday = get_portfolio_intraday()
portfolio = build_portfolio(market_rows, portfolio_intraday)

st.sidebar.markdown("## ◈ Intelligence Desk")
st.sidebar.caption(f"Version {APP_VERSION}")
st.sidebar.markdown("---")
selection = st.sidebar.radio("Navigation",["Today","Portfolio","Markets","Watch","Trading Desk","Strategy Lab","Performance Lab","Settings"],label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption(f"{source} · portfolio prices 5 min · hourly moves 2 min")

titles = {
    "Today":("Today","Your five-minute market, portfolio and trading briefing."),
    "Portfolio":("Portfolio","Your holdings, live value, allocation and portfolio structure."),
    "Markets":("Markets","Top projects by narrative with clean price and volume context."),
    "Watch":("Watch","What deserves attention now, with detail hidden behind each asset."),
    "Trading Desk":("Trading Desk","All paper wallets, positions, completed trades and external calls in one place."),
    "Strategy Lab":("Strategy Lab","Champion and challenger strategies, kept separate from daily use."),
    "Performance Lab":("Performance Lab","Trade outcomes, lessons and evidence about what is working."),
    "Settings":("Settings","Workflow status, data health and platform controls."),
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
    section("Moves now")
    live_movers = sorted(
        portfolio["items"],
        key=lambda x:(abs(x.get("change_6h",0)), abs(x.get("change_1h",0)), abs(x["change_24h"])),
        reverse=True,
    )
    for rank,item in enumerate(live_movers[:6],1):
        render_live_move_row(rank,item)

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
    section("Live portfolio moves")
    live_movers = sorted(
        portfolio["items"],
        key=lambda x:(x.get("change_6h",0), x.get("change_1h",0), x["change_24h"]),
        reverse=True,
    )
    for rank,item in enumerate(live_movers[:8],1):
        render_live_move_row(rank,item)

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
    st.markdown(
        '<div class="summary-box"><b>Purpose:</b> Show the top five observable market projects '
        'inside each narrative using price direction, RVOL change, current RVOL and volume flow. '
        'No prediction score or confidence percentage is used.</div>',
        unsafe_allow_html=True,
    )

    with st.spinner("Loading narrative market data..."):
        market_narratives, market_projects = scan_fourh_universe(portfolio)

    if not market_projects:
        st.error("Narrative market data is temporarily unavailable. Try refreshing later.")
    else:
        section("Top 5 projects by narrative")
        st.caption(
            "Projects are ordered within each narrative by fixed volume-flow rules, "
            "then RVOL change, current RVOL and price direction."
        )

        narrative_order = []
        for narrative, items in market_narratives.items():
            if items:
                positive = sum(1 for item in items if item["flow"]["label"] == "Positive flow")
                negative = sum(1 for item in items if item["flow"]["label"] == "Negative flow")
                average_rvol_change = sum(item["rvol_delta"] for item in items) / len(items)
                narrative_order.append((narrative, positive - negative, average_rvol_change))
        narrative_order.sort(key=lambda row: (row[1], row[2]), reverse=True)

        for index, (narrative, _, _) in enumerate(narrative_order):
            items = market_narratives[narrative][:5]
            flow_label, flow_arrow, _ = narrative_flow_summary(items)
            with st.expander(
                f'{narrative} · {flow_arrow} {flow_label} volume flow · Top {len(items)}',
                expanded=index < 3,
            ):
                for rank, item in enumerate(items, 1):
                    render_market_top_five_row(rank, item)

        section("Portfolio narrative exposure")
        themes = sorted(portfolio["themes"], key=lambda x: x["value"], reverse=True)
        cols = st.columns(4)
        for col, theme in zip(cols, themes[:4]):
            with col:
                metric(
                    theme["name"],
                    f'{theme["value"]/portfolio["total"]*100:.1f}%',
                    money(theme["value"]),
                )

        section("Arrow rules")
        st.markdown(
            '<div class="summary-box">'
            '<b>Green ↑:</b> price and volume are rising together. '
            '<b>Red ↓:</b> volume is rising while price falls. '
            '<b>Blue ↑:</b> volume is rising while price is mostly flat. '
            '<b>Orange ↓:</b> price rises while volume fades. '
            '<b>Yellow/Grey →:</b> mixed, falling or stable activity.'
            '</div>',
            unsafe_allow_html=True,
        )

elif selection=="Watch":
    latest_watch=read_runtime_json(SIGNALS_LATEST_FILE,{"signals":[]})
    observer_watch=read_runtime_json(OBSERVER_LATEST_FILE,{"signals":[]})
    risk_watch=read_runtime_json(RISK_GUARDIAN_FILE,{"asset_checks":[]})
    lifecycle_watch=read_runtime_json(SIGNAL_LIFECYCLE_FILE,{"assets":{}})
    paper_watch=read_runtime_json(PAPER_TRADES_FILE,[])
    external_watch=read_runtime_json(EXTERNAL_CALLS_FILE,[])

    signals=latest_watch.get("signals") or []
    observer_map={str(x.get("symbol","")).upper():x for x in (observer_watch.get("signals") or [])}
    risk_map={str(x.get("symbol","")).upper():x for x in (risk_watch.get("asset_checks") or [])}
    lifecycle_assets=lifecycle_watch.get("assets") or {}
    open_paper={str(x.get("symbol","")).upper():x for x in paper_watch if x.get("status")=="OPEN"}
    external_map={str(x.get("symbol","")).upper():x for x in external_watch if x.get("status","ACTIVE")=="ACTIVE"}

    def lifecycle_for(symbol):
        for value in lifecycle_assets.values():
            if str(value.get("symbol","")).upper()==symbol:
                return value.get("current_state","NEUTRAL")
        return "NEUTRAL"

    def classify(signal):
        symbol=str(signal.get("symbol","")).upper()
        call=str(signal.get("signal") or "HOLD").upper()
        risk=(risk_map.get(symbol) or {}).get("state","NORMAL")
        rvold=safe_float(signal.get("rvol_delta"))
        if risk in {"INVALIDATION RISK","DATA UNRELIABLE"}:
            return "risk","Risk"
        if signal.get("changed") or call in {"STRONG BUY","STRONG SELL"}:
            return ("good" if "BUY" in call else "risk"),"Immediate"
        if call in {"BUY WATCH","SELL WATCH"} and rvold>0:
            return "info","Building"
        if rvold<-.10:
            return "warn","Weakening"
        return "watch","Research"

    groups={"Immediate":[],"Building":[],"Weakening":[],"Risk":[],"Research":[]}
    for signal in signals:
        css,bucket=classify(signal)
        item=dict(signal); item["_css"]=css
        groups[bucket].append(item)

    st.markdown('<div class="summary-box"><b>Opportunity Board:</b> only core asset and trade information is shown first. Open an asset panel for the evidence, Observer, risk, trading and external details.</div>',unsafe_allow_html=True)
    cols=st.columns(5)
    for col,label in zip(cols,groups.keys()):
        with col: metric(label,str(len(groups[label])),"Assets")
    chosen=st.radio("View",list(groups.keys()),horizontal=True,label_visibility="collapsed")
    visible=sorted(groups[chosen],key=lambda x:(abs(safe_float(x.get("return_4h"))),safe_float(x.get("rvol"))),reverse=True)

    if not visible:
        st.caption(f"No assets currently sit in {chosen}.")
    for signal in visible:
        symbol=str(signal.get("symbol","")).upper()
        observer=observer_map.get(symbol,{})
        risk=risk_map.get(symbol,{})
        paper=open_paper.get(symbol)
        external=external_map.get(symbol)
        life=lifecycle_for(symbol)
        css=signal.get("_css","watch")
        st.markdown(
            f'<div class="asset-front-card {css}"><div class="asset-grid">'
            f'<div><div class="asset-name">{esc(symbol)} · {esc(signal.get("name",""))}</div><div class="asset-sub">{esc(signal.get("narrative",""))} · {esc(life)}</div></div>'
            f'<div><div class="asset-k">Call</div><div class="asset-v">{esc(signal.get("signal","HOLD"))}</div></div>'
            f'<div><div class="asset-k">4H</div><div class="asset-v">{html_signal(safe_float(signal.get("return_4h")))}</div></div>'
            f'<div><div class="asset-k">24H</div><div class="asset-v">{html_signal(safe_float(signal.get("return_24h")))}</div></div>'
            f'<div><div class="asset-k">Trade</div><div class="asset-v">{"Open" if paper else "None"}</div></div>'
            f'</div></div>',unsafe_allow_html=True
        )
        with st.expander(f"Open {symbol} details"):
            tabs=st.tabs(["Core","Observer","Risk","Trading","External"])
            with tabs[0]:
                st.dataframe(pd.DataFrame([{
                    "Signal":signal.get("signal"),"Previous":signal.get("previous_signal"),
                    "4H %":signal.get("return_4h"),"12H %":signal.get("return_12h"),"24H %":signal.get("return_24h"),
                    "RVOL":signal.get("rvol"),"RVOL change":signal.get("rvol_delta"),"RSI":signal.get("rsi"),
                    "Bullish":signal.get("bullish"),"Bearish":signal.get("bearish"),"Source":signal.get("data_source"),
                }]),use_container_width=True,hide_index=True)
                if signal.get("checks"): st.dataframe(pd.DataFrame(signal["checks"]),use_container_width=True,hide_index=True)
            with tabs[1]:
                st.json(observer,expanded=False) if observer else st.caption("No observer record.")
            with tabs[2]:
                st.json(risk,expanded=False) if risk else st.caption("No Risk Guardian record.")
            with tabs[3]:
                st.json(paper,expanded=False) if paper else st.caption("No open paper trade.")
            with tabs[4]:
                st.json(external,expanded=False) if external else st.caption("No active external call.")

elif selection=="15M Observer":
    observer=read_runtime_json(OBSERVER_LATEST_FILE,{"signals":[],"health":{}})
    observer_history=read_runtime_json(OBSERVER_HISTORY_FILE,[])
    observer_wallet=read_runtime_json(OBSERVER_WALLET_FILE,{})
    timing=read_runtime_json(SIGNAL_TIMING_FILE,{"assets":{}})

    st.markdown(
        '<div class="summary-box"><b>Early observer:</b> this layer searches for developing shifts '
        'before the hourly 4H Champion confirms them. It is a separate challenger and paper wallet, '
        'not a replacement for the Champion.</div>',
        unsafe_allow_html=True,
    )

    if not observer.get("signals"):
        st.info("Run the 15-Minute Observer workflow once after uploading V8.9.")
    else:
        health=observer.get("health") or {}
        wallet_equity=float(observer_wallet.get("equity") or observer_wallet.get("starting_cash") or 100000)
        starting=float(observer_wallet.get("starting_cash") or 100000)
        wallet_return=(wallet_equity/starting-1)*100 if starting else 0

        section("Observer heartbeat")
        cols=st.columns(6)
        with cols[0]: metric("Last run",str(observer.get("generated_at",""))[:16].replace("T"," "),"UTC")
        with cols[1]: metric("Analysed",str(health.get("assets_analysed",0)),f'{health.get("assets_requested",0)} requested')
        with cols[2]: metric("Unavailable",str(len(health.get("unavailable_assets") or [])),", ".join((health.get("unavailable_assets") or [])[:3]) or "None")
        with cols[3]: metric("Wallet",f'${wallet_equity:,.2f}',f'{wallet_return:+.2f}%')
        with cols[4]: metric("Open",str(len(observer_wallet.get("open_positions") or [])),"Observer positions")
        with cols[5]: metric("Closed",str(len(observer_wallet.get("closed_positions") or [])),"Completed")

        tabs=st.tabs(["Early Signals","Observer Wallet","Timing Lab","Observer Journal"])

        with tabs[0]:
            section("Current early observations")
            signal_filter=st.selectbox(
                "Observer state",
                ["ALL","EARLY BUY","BUY WATCH","EARLY SELL","SELL WATCH","VOLATILITY WATCH","NEUTRAL"]
            )
            rows=[]
            for item in observer.get("signals") or []:
                if signal_filter!="ALL" and item.get("signal")!=signal_filter:
                    continue
                rows.append({
                    "Asset":item.get("symbol"),
                    "Observer":item.get("signal"),
                    "Lifecycle":item.get("lifecycle_state"),
                    "15M %":item.get("return_15m"),
                    "1H %":item.get("return_1h"),
                    "4H %":item.get("return_4h"),
                    "RVOL":item.get("rvol"),
                    "RVOL change":item.get("rvol_delta"),
                    "RSI":item.get("rsi"),
                    "Bullish":item.get("bullish_conditions"),
                    "Bearish":item.get("bearish_conditions"),
                    "Source":item.get("data_source"),
                    "Changed":item.get("changed"),
                })
            if rows:
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            else:
                st.caption("No observations match this filter.")

        with tabs[1]:
            section("Observer paper wallet")
            cols=st.columns(5)
            with cols[0]: metric("Equity",f'${wallet_equity:,.2f}',f'{wallet_return:+.2f}%')
            with cols[1]: metric("Cash",f'${float(observer_wallet.get("cash") or 0):,.2f}',"Reserve")
            with cols[2]: metric("Realised P/L",f'${float(observer_wallet.get("realised_pnl") or 0):+,.2f}',"Closed trades")
            with cols[3]: metric("Unrealised P/L",f'${float(observer_wallet.get("unrealised_pnl") or 0):+,.2f}',"Open trades")
            with cols[4]: metric("Latest change",f'${float(observer_wallet.get("equity_change_this_run") or 0):+,.2f}',"This observer run")

            equity_history=pd.DataFrame(observer_wallet.get("equity_history") or [])
            if not equity_history.empty and "recorded_at" in equity_history.columns:
                equity_history["recorded_at"]=pd.to_datetime(equity_history["recorded_at"],errors="coerce")
                equity_history=equity_history.dropna(subset=["recorded_at"]).set_index("recorded_at")
                st.line_chart(equity_history[["equity"]],use_container_width=True)

            section("Open observer positions")
            open_positions=observer_wallet.get("open_positions") or []
            if open_positions:
                st.dataframe(pd.DataFrame([{
                    "Asset":p.get("symbol"),
                    "Direction":p.get("direction"),
                    "Entry":p.get("entry_price"),
                    "Current":p.get("current_price"),
                    "Allocated":p.get("allocated_cash"),
                    "P/L %":p.get("unrealised_return"),
                    "P/L $":p.get("unrealised_pnl"),
                    "Opened":p.get("entry_time"),
                } for p in open_positions]),use_container_width=True,hide_index=True)
            else:
                st.caption("No observer positions are open.")

            section("Closed observer positions")
            closed_positions=observer_wallet.get("closed_positions") or []
            if closed_positions:
                st.dataframe(pd.DataFrame([{
                    "Asset":p.get("symbol"),
                    "Direction":p.get("direction"),
                    "Entry":p.get("entry_price"),
                    "Exit":p.get("exit_price"),
                    "P/L %":p.get("realised_return"),
                    "P/L $":p.get("realised_pnl"),
                    "Reason":p.get("exit_reason"),
                    "Opened":p.get("entry_time"),
                    "Closed":p.get("exit_time"),
                } for p in reversed(closed_positions[-250:])]),use_container_width=True,hide_index=True)
            else:
                st.caption("No observer trades have closed yet.")

        with tabs[2]:
            section("Observer versus hourly timing")
            comparison_rows=[]
            for symbol,asset in (timing.get("assets") or {}).items():
                for comparison in asset.get("comparisons") or []:
                    observer_price=comparison.get("observer_price")
                    hourly_price=comparison.get("hourly_price")
                    price_advantage=None
                    if observer_price and hourly_price:
                        raw=(float(hourly_price)/float(observer_price)-1)*100
                        price_advantage=raw if comparison.get("direction")=="LONG" else -raw
                    comparison_rows.append({
                        "Asset":symbol,
                        "Direction":comparison.get("direction"),
                        "Observer detected":comparison.get("observer_detected_at"),
                        "Hourly detected":comparison.get("hourly_detected_at"),
                        "Lead minutes":comparison.get("lead_minutes"),
                        "Observer price":observer_price,
                        "Hourly price":hourly_price,
                        "Early price advantage %":price_advantage,
                    })
            if comparison_rows:
                st.dataframe(pd.DataFrame(comparison_rows),use_container_width=True,hide_index=True)
                lead_values=[row["Lead minutes"] for row in comparison_rows if row["Lead minutes"] is not None]
                advantage_values=[row["Early price advantage %"] for row in comparison_rows if row["Early price advantage %"] is not None]
                cols=st.columns(3)
                with cols[0]: metric("Comparisons",str(len(comparison_rows)),"Matched directions")
                with cols[1]: metric("Average lead",f'{sum(lead_values)/len(lead_values):.0f} min' if lead_values else "—","Observer before hourly")
                with cols[2]: metric("Average price advantage",f'{sum(advantage_values)/len(advantage_values):+.2f}%' if advantage_values else "—","Before costs")
            else:
                st.caption("Timing comparisons will appear when an early observation is later matched by the hourly engine.")

        with tabs[3]:
            section("Observer activity")
            activity=observer_wallet.get("activity_journal") or []
            if activity:
                st.dataframe(pd.DataFrame(list(reversed(activity[-500:]))),use_container_width=True,hide_index=True)
            else:
                st.caption("Observer activity will appear after the first run.")
            section("Observer history")
            if observer_history:
                st.dataframe(pd.DataFrame(list(reversed(observer_history[-500:]))),use_container_width=True,hide_index=True)
            else:
                st.caption("No observer history has been recorded.")


elif selection=="Research":
    st.markdown(
        '<div class="summary-box"><b>Observable market data:</b> all colours below are generated '
        'from fixed price and volume rules. Green and red are not subjective confidence scores.</div>',
        unsafe_allow_html=True,
    )

    section("Portfolio market radar")
    ordered_items = sorted(
        portfolio["items"],
        key=lambda x:(abs(x.get("change_6h",0)), x.get("rvol",0), abs(x.get("change_24h",0))),
        reverse=True,
    )

    for item in ordered_items:
        flow = volume_flow(
            item.get("change_6h", item.get("change_24h",0)),
            item.get("rvol_delta",0.0),
            item.get("rvol",1.0),
        )
        source = item.get("move_source","Market data")
        age = item.get("data_age_minutes",0)
        st.markdown(
            f'<div class="research-card">'
            f'<div class="research-head">'
            f'<div><div class="research-asset">{esc(item["symbol"])}</div>'
            f'<div class="research-name">{esc(item.get("name",""))} · {esc(item.get("narrative",""))}</div></div>'
            f'<div><div class="research-label">1 hour</div><div class="research-value">{html_signal(item.get("change_1h",0))}</div></div>'
            f'<div><div class="research-label">6 hours</div><div class="research-value">{html_signal(item.get("change_6h",0))}</div></div>'
            f'<div><div class="research-label">24 hours</div><div class="research-value">{html_signal(item.get("change_24h",0))}</div></div>'
            f'<div><div class="research-label">7 days</div><div class="research-value">{html_signal(item.get("change_7d",0))}</div></div>'
            f'<div><div class="research-label">Volume flow</div><div class="research-value">{html_flow(flow)}</div></div>'
            f'</div>'
            f'<div class="research-details">'
            f'<div><div class="research-label">Current RVOL</div><div class="research-value">{item.get("rvol",1):.2f}×</div></div>'
            f'<div><div class="research-label">RVOL change</div><div class="research-value">{html_signal(item.get("rvol_delta",0),.10)}</div></div>'
            f'<div><div class="research-label">Data</div><div class="research-value">{esc(source)} · {freshness_html(age)}</div></div>'
            f'<div><div class="research-label">Portfolio weight</div><div class="research-value">{item.get("weight",0):.1f}%</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    section("Colour rules")
    st.markdown(
        '<div class="summary-box">'
        '<span class="signal-up"><b>Green ↑</b></span> price and volume are rising together. '
        '<span class="signal-down"><b>Red ↓</b></span> volume is rising while price falls. '
        '<span class="signal-watch"><b>Blue ↑</b></span> volume is rising while price is flat or not confirmed. '
        '<span class="signal-fade"><b>Orange ↓</b></span> price is rising while volume fades. '
        '<span class="signal-flat"><b>Yellow →</b></span> mixed or stable conditions.'
        '</div>',
        unsafe_allow_html=True,
    )

elif selection=="4H Intelligence":
    signal_history=read_runtime_json(SIGNAL_HISTORY_FILE,[])
    paper_trades=read_runtime_json(PAPER_TRADES_FILE,[])
    external_calls=read_runtime_json(EXTERNAL_CALLS_FILE,[])
    st.markdown('<div class="summary-box"><b>Flagship 4H Intelligence:</b> current calls, narrative rotation, source agreement, prior-call performance and reviewed external agreement. No hidden 0–100 score is used.</div>',unsafe_allow_html=True)

    with st.spinner("Scanning portfolio holdings across available four-hour sources..."):
        portfolio_calls=[]
        progress=st.progress(0,text="Preparing portfolio radar...")
        total=max(1,len(portfolio["items"]))
        for index,item in enumerate(portfolio["items"]):
            symbol=item["symbol"]; ticker=CRYPTO_TICKERS.get(symbol,f"{symbol}-USD")
            intelligence=unified_asset_intelligence(symbol,ticker)
            if intelligence.get("primary"): portfolio_calls.append({**item,"intelligence":intelligence})
            progress.progress((index+1)/total,text=f"Scanning {symbol}...")
        progress.empty()

    if not portfolio_calls:
        st.error("No usable four-hour market data could be retrieved.")
    else:
        portfolio_calls.sort(key=lambda x:(signal_priority_value(x["intelligence"]["primary"]["signal"]),x["intelligence"]["primary"]["bullish"]-x["intelligence"]["primary"]["bearish"],x["intelligence"]["primary"]["ret4h"]),reverse=True)
        section("Market radar")
        counts=defaultdict(int)
        for item in portfolio_calls: counts[item["intelligence"]["primary"]["signal"]]+=1
        cols=st.columns(5)
        values=[("Strong Buy",counts["STRONG BUY"]),("Buy / Watch",counts["BUY"]+counts["BUY WATCH"]),("Hold",counts["HOLD"]),("Sell / Watch",counts["SELL"]+counts["SELL WATCH"]),("Strong Sell",counts["STRONG SELL"])]
        for col,(label,value) in zip(cols,values):
            with col: metric(label,str(value),"Current calls")
        actionable=[x for x in portfolio_calls if x["intelligence"]["primary"]["signal"]!="HOLD"]
        for rank,item in enumerate((actionable or portfolio_calls)[:12],1): render_radar_row(rank,item)

        section("Narrative radar")
        grouped=defaultdict(list)
        for item in portfolio_calls: grouped[item.get("narrative","Other")].append(item)
        rows=[]
        for narrative,items in grouped.items():
            state=narrative_flow_state(items)
            top=sorted(items,key=lambda x:(signal_priority_value(x["intelligence"]["primary"]["signal"]),x["intelligence"]["primary"]["rvol"],x["intelligence"]["primary"]["ret4h"]),reverse=True)[:5]
            rows.append((narrative,state,top))
        rows.sort(key=lambda row:(sum(signal_priority_value(x["intelligence"]["primary"]["signal"]) for x in row[2]),sum(x["intelligence"]["primary"]["ret4h"] for x in row[2])),reverse=True)
        for narrative,state,items in rows:
            with st.expander(f'{narrative} · {state["arrow"]} {state["label"]} · Top {len(items)}'):
                for rank,item in enumerate(items,1):
                    result=item["intelligence"]["primary"]
                    st.markdown(f'<div class="narrative-grid"><div><div class="radar-asset">{rank}. {esc(item["symbol"])}</div><div class="radar-sub">{esc(item.get("name",""))}</div></div><div><div class="radar-label">Call</div><div class="radar-value">{call_badge(result["signal"])}</div></div><div><div class="radar-label">4H</div><div class="radar-value">{html_signal(result["ret4h"])}</div></div><div><div class="radar-label">RVOL</div><div class="radar-value">{result["rvol"]:.2f}×</div></div><div><div class="radar-label">Sources</div><div class="radar-value">{esc(item["intelligence"].get("agreement","—"))}</div></div></div>',unsafe_allow_html=True)

        section("Deep-dive asset")
        option_map={f'{item["symbol"]} · {item.get("name","")} · held':(item["symbol"],CRYPTO_TICKERS.get(item["symbol"],f'{item["symbol"]}-USD'),item) for item in portfolio_calls}
        selected_label=st.selectbox("Portfolio holding",list(option_map.keys()))
        selected_symbol,selected_ticker,selected_item=option_map[selected_label]
        c=st.columns([1,1,1])
        with c[0]: custom_symbol=st.text_input("Or investigate another asset",placeholder="LINK or AAPL")
        with c[1]: custom_type=st.selectbox("Asset type",["Crypto","US stock / ETF"])
        with c[2]: run_custom=st.button("Open deep dive",use_container_width=True)
        if run_custom and custom_symbol.strip():
            selected_symbol=custom_symbol.strip().upper()
            selected_ticker=resolve_ticker(selected_symbol,"Crypto" if custom_type=="Crypto" else "Stock / ETF")

        with st.spinner(f"Deep-diving {selected_symbol}..."): intel=unified_asset_intelligence(selected_symbol,selected_ticker)
        result=intel.get("primary")
        if not result:
            st.error(f"Not enough four-hour data was available for {selected_symbol}.")
        else:
            stats=historical_asset_stats(selected_symbol,paper_trades)
            change=latest_signal_change(selected_symbol,signal_history)
            external=external_agreement_for_asset(selected_symbol,external_calls,result["signal"])
            left,right=st.columns([1.35,1])
            with left: render_conviction_hero(selected_symbol,result,intel.get("primary_source","Market data"),intel.get("agreement","SINGLE SOURCE"))
            with right:
                cls="history-good" if stats["win_rate"]>=60 and stats["evaluated"] else "history-bad" if stats["win_rate"]<40 and stats["evaluated"] else "history-mixed"
                st.markdown(f'<div class="history-card {cls}"><div class="objective-title">Prior call performance</div><div class="objective-main">{stats["win_rate"]:.1f}% win rate</div><div class="objective-row"><span>Calls</span><b>{stats["calls"]}</b></div><div class="objective-row"><span>Evaluated</span><b>{stats["evaluated"]}</b></div><div class="objective-row"><span>Average result</span><b>{stats["average"]:+.2f}%</b></div></div>',unsafe_allow_html=True)

            section("Current observable evidence")
            render_category_states(result["categories"])
            cols=st.columns(6)
            values=[("4H",signed(result["ret4h"]),"Latest candle"),("12H",signed(result["ret12h"]),"Three candles"),("24H",signed(result["ret24h"]),"Six candles"),("RVOL",f'{result["rvol"]:.2f}×',f'{result["rvol_delta"]:+.2f}× change'),("RSI",f'{result["rsi"]:.1f}',f'{result["rsi_delta"]:+.1f} change'),("ADX",f'{result["adx"]:.1f}' if pd.notna(result["adx"]) else "—","Trend strength")]
            for col,(label,value,note) in zip(cols,values):
                with col: metric(label,value,note)

            section("Why the call changed")
            if change and change["changes"]:
                st.markdown('<div class="change-box"><b>Latest recorded changes</b><br>'+"<br>".join(f'• {esc(x)}' for x in change["changes"])+"</div>",unsafe_allow_html=True)
            elif change:
                st.markdown('<div class="change-box">The latest recorded scan did not show a major state change.</div>',unsafe_allow_html=True)
            else: st.info("No prior signal history exists for this asset yet.")

            section("External-source agreement")
            cols=st.columns(3)
            with cols[0]: metric("Active external calls",str(external["count"]),"Reviewed calls only")
            with cols[1]: metric("Agree",str(external["agree"]),"Same direction")
            with cols[2]: metric("Disagree",str(external["disagree"]),"Opposite direction")
            if external["items"]:
                st.dataframe(pd.DataFrame([{"Source":x.get("source"),"Call":x.get("call"),"Direction":x.get("direction"),"Entry":x.get("entry_price"),"Agreement":x.get("agreement"),"Timeframe":x.get("timeframe"),"Reference":x.get("source_link")} for x in external["items"]]),use_container_width=True,hide_index=True)
            else: st.caption("No reviewed external calls are active for this asset.")

            section("Prior calls on this asset")
            if stats["trades"]:
                st.dataframe(pd.DataFrame([{"Source":t.get("source"),"Call":t.get("call"),"Entry":t.get("entry_price"),"1H":checkpoint_return(t,"1h"),"4H":checkpoint_return(t,"4h"),"12H":checkpoint_return(t,"12h"),"24H":checkpoint_return(t,"1d"),"3D":checkpoint_return(t,"3d"),"7D":checkpoint_return(t,"7d"),"Latest":evaluated_return(t),"Status":t.get("status")} for t in reversed(stats["trades"][-30:])]),use_container_width=True,hide_index=True)
            else: st.caption("No prior paper-trade calls have been recorded for this asset.")

            section("Conviction checklist")
            st.caption(f'{result["bullish"]} bullish · {result["bearish"]} bearish · {result["total"]} total conditions')
            render_signal_checklist(result)
            section("Four-hour trend chart")
            st.line_chart(result["chart"],use_container_width=True)
            section("Source confirmation")
            source_rows=[{"Source":intel.get("primary_source"),"Call":result["signal"],"4H":result["ret4h"],"24H":result["ret24h"],"RVOL":result["rvol"],"Bullish":result["bullish"],"Bearish":result["bearish"]}]
            for confirmation in intel.get("confirmations",[]):
                other=confirmation["result"]; source_rows.append({"Source":confirmation["source"],"Call":other["signal"],"4H":other["ret4h"],"24H":other["ret24h"],"RVOL":other["rvol"],"Bullish":other["bullish"],"Bearish":other["bearish"]})
            st.dataframe(pd.DataFrame(source_rows),use_container_width=True,hide_index=True)

elif selection=="Research Desk":
    ledger=read_runtime_json(EVIDENCE_LEDGER_FILE,[])
    lifecycle=read_runtime_json(SIGNAL_LIFECYCLE_FILE,{"updated_at":None,"assets":{}})
    wallet=read_runtime_json(RESEARCH_WALLET_FILE,{})
    registry=read_runtime_json(STRATEGY_REGISTRY_FILE,{"strategies":[]})
    engine_health=read_runtime_json(ENGINE_HEALTH_FILE,{})
    st.markdown('<div class="summary-box"><b>Research Desk Foundation:</b> immutable evidence, signal lifecycle and a paper-only AI research wallet.</div>',unsafe_allow_html=True)
    tabs=st.tabs(["Research Wallet","Engine Health","Evidence Ledger","Signal Lifecycle","Strategy Registry"])
    with tabs[0]:
        equity=float(wallet.get("equity") or wallet.get("starting_cash") or 100000); start=float(wallet.get("starting_cash") or 100000); ret=(equity/start-1)*100 if start else 0; opens=wallet.get("open_positions") or []; closed=wallet.get("closed_positions") or []
        cols=st.columns(5)
        with cols[0]: metric("Wallet equity",f'${equity:,.2f}',f'{ret:+.2f}% from start')
        with cols[1]: metric("Cash",f'${float(wallet.get("cash") or 0):,.2f}',"Paper cash")
        with cols[2]: metric("Open positions",str(len(opens)),"Decisive calls")
        with cols[3]: metric("Closed positions",str(len(closed)),"Completed")
        with cols[4]: metric("Realised P/L",f'${float(wallet.get("realised_pnl") or 0):+,.2f}',"Paper result")
        if wallet.get("equity_history"):
            h=pd.DataFrame(wallet["equity_history"]); h["recorded_at"]=pd.to_datetime(h["recorded_at"],errors="coerce"); h=h.dropna(subset=["recorded_at"]).set_index("recorded_at"); st.line_chart(h[["equity"]],use_container_width=True)
        section("Open positions")
        if opens: st.dataframe(pd.DataFrame(opens),use_container_width=True,hide_index=True)
        else: st.caption("No decisive calls have opened research-wallet positions yet.")
        section("Closed positions")
        if closed: st.dataframe(pd.DataFrame(list(reversed(closed[-100:]))),use_container_width=True,hide_index=True)
        else: st.caption("No research-wallet positions have closed yet.")
    with tabs[1]:
        section("Latest engine health")
        status=engine_health.get("overall_status","NOT RUN")
        generated=engine_health.get("generated_at")
        st.markdown(
            f'<div class="summary-box"><b>Status:</b> {esc(status)}'
            f' · <b>Generated:</b> {esc(str(generated or "Not run"))}</div>',
            unsafe_allow_html=True,
        )
        market=engine_health.get("market_data") or {}
        signals_health=engine_health.get("signals") or {}
        trades_health=engine_health.get("paper_trading") or {}
        wallet_health=engine_health.get("research_wallet") or {}
        cols=st.columns(5)
        with cols[0]: metric("Analysed",str(market.get("assets_analysed",0)),f'{market.get("holdings_requested",0)} requested')
        with cols[1]: metric("Fallbacks",str(market.get("fallback_successes",0)),", ".join(market.get("fallback_assets",[])[:4]) or "None")
        with cols[2]: metric("Unavailable",str(market.get("unavailable_count",0)),", ".join(market.get("unavailable_assets",[])[:4]) or "None")
        with cols[3]: metric("New trades",str(trades_health.get("new_engine_trades",0)),f'{trades_health.get("equivalent_duplicates_prevented",0)} duplicates blocked')
        with cols[4]: metric("Wallet equity",f'${float(wallet_health.get("wallet_equity") or 0):,.2f}',f'${float(wallet_health.get("cash") or 0):,.2f} cash')
        section("Wallet activity this run")
        activity=wallet_health.get("activity") or {}
        st.dataframe(pd.DataFrame([{
            "Retained":activity.get("retained",0),
            "Closed":activity.get("closed",0),
            "Opened":activity.get("opened",0),
            "Rejected: capacity":activity.get("rejected_capacity",0),
            "Rejected: reserve":activity.get("rejected_cash_reserve",0),
            "Existing positions":activity.get("rejected_existing",0),
        }]),use_container_width=True,hide_index=True)
        warnings=engine_health.get("warnings") or []
        if warnings:
            for warning in warnings:
                st.warning(warning)
        else:
            st.success("No engine-health warnings were recorded.")
        with st.expander("Full engine health JSON"):
            st.json(engine_health,expanded=False)

    with tabs[2]:
        section("Immutable evidence ledger")
        if ledger:
            rows=[]
            for e in reversed(ledger[-1000:]): rows.append({"Recorded":e.get("recorded_at"),"Asset":e.get("asset"),"Strategy":e.get("strategy_id"),"Version":e.get("strategy_version"),"Signal":e.get("signal"),"Lifecycle":e.get("lifecycle_state"),"Entry":e.get("entry_price"),"RVOL":(e.get("indicators") or {}).get("rvol"),"Bullish":(e.get("indicators") or {}).get("bullish_conditions"),"Bearish":(e.get("indicators") or {}).get("bearish_conditions"),"Source":e.get("data_source")})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            assets=sorted({str(x.get("asset")) for x in ledger if x.get("asset")}); chosen=st.selectbox("Inspect asset evidence",assets); selected=[x for x in ledger if x.get("asset")==chosen]
            if selected: st.json(selected[-1],expanded=False)
        else: st.info("The next successful hourly run will begin the Evidence Ledger.")
    with tabs[3]:
        section("Signal lifecycle")
        assets=lifecycle.get("assets") or {}; counts=defaultdict(int)
        for a in assets.values(): counts[a.get("current_state","UNKNOWN")]+=1
        cols=st.columns(6)
        for col,label in zip(cols,["FORMING","CONFIRMED","ACTIVE","WEAKENING","NEUTRAL","INVALIDATED"]):
            with col: metric(label,str(counts[label]),"Current state")
        if assets:
            st.dataframe(pd.DataFrame([{"Asset":a.get("symbol"),"Strategy":a.get("strategy_id"),"Current signal":a.get("current_signal"),"Lifecycle":a.get("current_state"),"Last updated":a.get("last_updated"),"Transitions":len(a.get("transitions") or [])} for a in assets.values()]),use_container_width=True,hide_index=True)
            key=st.selectbox("Inspect lifecycle history",sorted(assets.keys())); hist=(assets.get(key) or {}).get("transitions") or []
            if hist: st.dataframe(pd.DataFrame(list(reversed(hist[-100:]))),use_container_width=True,hide_index=True)
        else: st.info("Lifecycle records will appear after the next hourly run.")
    with tabs[4]:
        section("Champion and challenger registry")
        strategies=registry.get("strategies") or []
        if strategies:
            st.dataframe(pd.DataFrame([{"Strategy":s.get("name"),"ID":s.get("strategy_id"),"Role":s.get("role"),"Version":s.get("version"),"Enabled":s.get("enabled"),"Description":s.get("description")} for s in strategies]),use_container_width=True,hide_index=True)
            sid=st.selectbox("Inspect rules",[s.get("strategy_id") for s in strategies]); st.json(next(s for s in strategies if s.get("strategy_id")==sid),expanded=False)
        else: st.info("The strategy registry will be created by bootstrap.")
        st.markdown('<div class="summary-box"><b>Current stage:</b> only the Champion powers live paper calls. Challengers are registered for future side-by-side testing.</div>',unsafe_allow_html=True)



elif selection=="Trading Desk":
    fund=read_runtime_json(FUND_STATE_FILE,{})
    core=read_runtime_json(CORE_WALLET_FILE,{})
    swing=read_runtime_json(SWING_WALLET_FILE,{})
    scalp=read_runtime_json(SCALP_WALLET_FILE,{})
    manager=read_runtime_json(PORTFOLIO_MANAGER_FILE,{"actions":[]})
    wallets=[("Core",core),("Swing",swing),("Scalp",scalp)]
    st.markdown('<div class="summary-box"><b>Trading Desk:</b> what we are trading, what it is doing, and what action the engine is taking. Detailed evidence stays behind each position.</div>',unsafe_allow_html=True)
    open_rows=[(book,p) for book,w in wallets for p in (w.get("open_positions") or [])]
    c1,c2,c3,c4=st.columns(4)
    with c1: metric("Active trades",str(len(open_rows)),"Across all books")
    with c2: metric("Core",f"${wallet_equity(core):,.0f}",f"{wallet_return_pct(core):+.2f}%")
    with c3: metric("Swing",f"${wallet_equity(swing):,.0f}",f"{wallet_return_pct(swing):+.2f}%")
    with c4: metric("Scalp",f"${wallet_equity(scalp):,.0f}",f"{wallet_return_pct(scalp):+.2f}%")
    section("Active trades")
    if not open_rows: st.caption("No positions are open. Waiting is a valid decision.")
    for book,p in sorted(open_rows,key=lambda x:safe_float(x[1].get("unrealised_pnl")),reverse=True):
        ret=safe_float(p.get("unrealised_return")); pnl=safe_float(p.get("unrealised_pnl"))
        css="profit" if pnl>0 else "loss" if pnl<0 else "active"
        action="PROTECT PROFIT" if ret>=3 else "REVIEW RISK" if ret<=-1.5 else "HOLD / WATCH"
        st.markdown(f'<div class="front-trade-card {css}"><div class="front-trade-grid">'
            f'<div><div class="front-trade-title">{esc(p.get("symbol",""))} · {book}</div><div class="front-trade-sub">{esc(p.get("direction",""))} · {esc(p.get("signal",""))}</div></div>'
            f'<div><div class="front-trade-k">Entry</div><div class="front-trade-v">{safe_float(p.get("entry_price")):,.6f}</div></div>'
            f'<div><div class="front-trade-k">Current</div><div class="front-trade-v">{safe_float(p.get("current_price")):,.6f}</div></div>'
            f'<div><div class="front-trade-k">Return</div><div class="front-trade-v">{ret:+.2f}%</div></div>'
            f'<div><div class="front-trade-k">P/L</div><div class="front-trade-v">${pnl:+,.2f}</div></div>'
            f'<div><div class="front-trade-k">Action</div><div class="front-trade-v">{action}</div></div></div></div>',unsafe_allow_html=True)
        with st.expander(f"Open {p.get('symbol','')} details"):
            decision=((p.get("committee_snapshot") or {}).get("decision") or {})
            a,b,c=st.columns(3)
            with a: metric("Committee",str(decision.get("quality") or "Legacy"),str(decision.get("action") or ""))
            with b: metric("Best move",f"{safe_float(p.get('maximum_favourable_excursion_pct')):+.2f}%","Since entry")
            with c: metric("Worst move",f"{safe_float(p.get('maximum_adverse_excursion_pct')):+.2f}%","Since entry")
    section("Recent decisions")
    actions=list(reversed((manager.get("actions") or [])[-12:]))
    if actions:
        st.dataframe(pd.DataFrame([{"Asset":a.get("symbol"),"Book":a.get("book"),"Action":a.get("action"),
            "Reason":a.get("reason") or a.get("detail"),"P/L":a.get("pnl")} for a in actions]),
            use_container_width=True,hide_index=True)
    else: st.caption("No recent portfolio actions.")

elif selection=="Strategy Lab":
    lab=read_runtime_json(STRATEGY_LAB_FILE,{"strategies":{}})
    strategies=lab.get("strategies") or {}
    st.markdown('<div class="summary-box"><b>Strategy Lab:</b> which approach is currently doing the best job. This is a competition of decision quality, not a wall of statistics.</div>',unsafe_allow_html=True)
    if not strategies: st.info("Run Hourly Signal Recorder to initialise the Strategy Lab.")
    else:
        ranked=sorted(strategies.items(),key=lambda x:(wallet_return_pct(x[1]),safe_float((x[1].get("metrics") or {}).get("win_rate"))),reverse=True)
        section("Strategy competition")
        for rank,(sid,wallet) in enumerate(ranked,1):
            metrics=wallet.get("metrics") or {}; positions=wallet.get("open_positions") or []
            best=max(positions,key=lambda p:safe_float(p.get("unrealised_pnl")),default={})
            now_state=f'{best.get("symbol")} {best.get("direction")}' if best else "WAITING"
            css="profit" if wallet_return_pct(wallet)>0 else "loss" if wallet_return_pct(wallet)<0 else "watch"
            st.markdown(f'<div class="front-trade-card {css}"><div class="front-trade-grid">'
                f'<div><div class="front-trade-title">#{rank} · {esc(wallet.get("name",sid))}</div><div class="front-trade-sub">{esc(wallet.get("role","CHALLENGER"))}</div></div>'
                f'<div><div class="front-trade-k">Equity</div><div class="front-trade-v">${wallet_equity(wallet):,.0f}</div></div>'
                f'<div><div class="front-trade-k">Return</div><div class="front-trade-v">{wallet_return_pct(wallet):+.2f}%</div></div>'
                f'<div><div class="front-trade-k">Win rate</div><div class="front-trade-v">{safe_float(metrics.get("win_rate")):.1f}%</div></div>'
                f'<div><div class="front-trade-k">Now</div><div class="front-trade-v">{esc(now_state)}</div></div>'
                f'<div><div class="front-trade-k">Trades</div><div class="front-trade-v">{len(wallet.get("closed_positions") or [])}</div></div></div></div>',unsafe_allow_html=True)
            with st.expander(f"Open {wallet.get('name',sid)}"):
                a,b,c,d=st.columns(4)
                with a: metric("Open",str(len(positions)),"Current")
                with b: metric("Closed",str(len(wallet.get("closed_positions") or [])),"Evidence")
                with c: metric("Drawdown",f"{safe_float(metrics.get('max_drawdown')):.2f}%","Risk")
                with d: metric("Latest",f"${safe_float(wallet.get('equity_change_this_run')):+,.2f}","Last run")
                if positions:
                    for p in positions[:8]: st.write(f'{p.get("symbol")} · {p.get("direction")} · {safe_float(p.get("unrealised_return")):+.2f}%')
                else: st.caption("No trade is currently good enough for this strategy.")

elif selection=="Performance Lab":
    trade_reviews=read_runtime_json(TRADE_REVIEWS_FILE,{"reviews":[],"summary":{}})
    learning=read_runtime_json(LEARNING_STATE_FILE,{"summary":{},"rule_candidates":[]})
    diagnostics=read_runtime_json(TRADE_DIAGNOSTICS_FILE,{"summary":{},"diagnostics":[],"winner_loser_comparison":{}})
    arena=read_runtime_json(CHALLENGER_ARENA_FILE,{"ranking":[]})
    market_school=read_runtime_json(MARKET_SCHOOL_FILE,{"summary":{}})
    intelligence_bus=read_runtime_json(INTELLIGENCE_BUS_FILE,{"messages":[]})
    microstructure=read_runtime_json(MICROSTRUCTURE_FILE,{"signals":[]})
    reviews=trade_reviews.get("reviews") or []
    diagnostic_index={str(x.get("position_id") or ""):x for x in (diagnostics.get("diagnostics") or [])}
    summary=learning.get("summary") or {}

    st.markdown(
        '<div class="summary-box"><b>Performance Lab:</b> replay the trade, understand the AI decision, '
        'see what happened afterwards, and keep the lesson. The technical detail stays behind the scenes.</div>',
        unsafe_allow_html=True,
    )

    c1,c2,c3,c4,c5=st.columns(5)
    with c1: metric("Reviewed",str(summary.get("trades_reviewed",len(reviews))),"Trade cases")
    with c2: metric("Good process",str(summary.get("good_process",0)),"Repeat")
    with c3: metric("Poor process",str(summary.get("poor_process",0)),"Correct")
    with c4: metric("Missed re-entry",str(summary.get("missed_reentries",0)),"Opportunity failures")
    with c5: metric("Lessons testing",str(summary.get("candidate_lessons",0)),"Sample gated")

    school_summary=market_school.get("summary") or {}
    s1,s2,s3,s4=st.columns(4)
    with s1: metric("Charts studied",str(school_summary.get("assets_studied",0)),"Tracked assets")
    with s2: metric("Snapshots learned",str(school_summary.get("labelled_snapshots",0)),"Historical states")
    with s3: metric("Large moves studied",str(school_summary.get("large_moves_studied",0)),"Not just trades")
    with s4: metric("1m/5m watched",str(len(microstructure.get("signals") or [])),"Execution timing")

    section("Trade replays")
    if not reviews:
        st.caption("No reviewed trades yet.")
    else:
        # Most recent cases first; each card remains concise until opened.
        for r in list(reversed(reviews[-100:])):
            pnl=safe_float(r.get("realised_pnl"))
            ret=safe_float(r.get("realised_return"))
            a=r.get("assessment") or {}
            reentry=r.get("reentry") or {}
            process=str(a.get("process_quality") or "PENDING")
            css="profit" if process=="GOOD" else "loss" if process=="POOR" else "watch"

            st.markdown(
                f'<div class="front-trade-card {css}"><div class="front-trade-grid">'
                f'<div><div class="front-trade-title">{esc(r.get("symbol",""))} · {esc(r.get("wallet",""))}</div>'
                f'<div class="front-trade-sub">{esc(r.get("direction",""))} · {esc(r.get("exit_reason",""))}</div></div>'
                f'<div><div class="front-trade-k">Result</div><div class="front-trade-v">{ret:+.2f}%</div></div>'
                f'<div><div class="front-trade-k">P/L</div><div class="front-trade-v">${pnl:+,.2f}</div></div>'
                f'<div><div class="front-trade-k">Entry</div><div class="front-trade-v">{esc(a.get("entry_quality") or "UNKNOWN")}</div></div>'
                f'<div><div class="front-trade-k">Process</div><div class="front-trade-v">{esc(process)}</div></div>'
                f'<div><div class="front-trade-k">Re-entry</div><div class="front-trade-v">{esc(reentry.get("status") or "MONITORING")}</div></div>'
                f'</div></div>',unsafe_allow_html=True
            )

            with st.expander(f"Replay {r.get('symbol','')} trade"):
                decision=r.get("decision_replay") or {}
                post=r.get("post_exit") or {}
                diagnostic=diagnostic_index.get(str(r.get("position_id") or ""),{})
                replay=r.get("replay") or {}
                path=pd.DataFrame(replay.get("price_path") or [])
                events=pd.DataFrame(replay.get("events") or [])

                # Trade story headline metrics.
                q1,q2,q3,q4=st.columns(4)
                with q1: metric("Entry",f"{safe_float(r.get('entry_price')):,.6f}",str(r.get("direction") or ""))
                with q2: metric("Exit",f"{safe_float(r.get('exit_price')):,.6f}",f"{ret:+.2f}%")
                with q3: metric("Best after exit",f"{safe_float(post.get('best_directional_move_pct')):+.2f}%","Same trade direction")
                with q4:
                    missed=safe_float(post.get("missed_move_value_on_original_capital"))
                    metric("Move value",f"${missed:,.0f}","Same original capital" if missed else "No positive post-exit move")

                # Visual replay. Vega-Lite is built into Streamlit; no new dependency.
                if not path.empty and {"time","price"}.issubset(path.columns):
                    path["time"]=pd.to_datetime(path["time"],errors="coerce",utc=True)
                    path=path.dropna(subset=["time","price"]).sort_values("time")
                    if not path.empty:
                        chart_rows=[]
                        for _,row in path.iterrows():
                            chart_rows.append({
                                "time":row["time"].isoformat(),
                                "price":safe_float(row["price"]),
                                "kind":"PRICE",
                                "label":str(row.get("state") or ""),
                            })
                        for _,ev in events.iterrows() if not events.empty else []:
                            chart_rows.append({
                                "time":str(ev.get("time") or ""),
                                "price":safe_float(ev.get("price")),
                                "kind":str(ev.get("event") or "EVENT"),
                                "label":str(ev.get("label") or ""),
                            })
                        chart_df=pd.DataFrame(chart_rows)
                        st.vega_lite_chart(
                            chart_df,
                            {
                                "height":320,
                                "layer":[
                                    {
                                        "transform":[{"filter":"datum.kind === 'PRICE'"}],
                                        "mark":{"type":"line","strokeWidth":2},
                                        "encoding":{
                                            "x":{"field":"time","type":"temporal","title":None},
                                            "y":{"field":"price","type":"quantitative","title":"Price","scale":{"zero":False}},
                                            "tooltip":[
                                                {"field":"time","type":"temporal","title":"Time"},
                                                {"field":"price","type":"quantitative","title":"Price","format":".6f"}
                                            ]
                                        }
                                    },
                                    {
                                        "transform":[{"filter":"datum.kind !== 'PRICE'"}],
                                        "mark":{"type":"point","filled":True,"size":130},
                                        "encoding":{
                                            "x":{"field":"time","type":"temporal"},
                                            "y":{"field":"price","type":"quantitative"},
                                            "color":{
                                                "field":"kind","type":"nominal",
                                                "scale":{"domain":["ENTRY","EXIT","REENTRY"],"range":["#46d37c","#ff6868","#f0b84b"]},
                                                "legend":{"title":None}
                                            },
                                            "tooltip":[
                                                {"field":"kind","type":"nominal","title":"Event"},
                                                {"field":"label","type":"nominal","title":"Meaning"},
                                                {"field":"time","type":"temporal","title":"Time"},
                                                {"field":"price","type":"quantitative","title":"Price","format":".6f"}
                                            ]
                                        }
                                    }
                                ]
                            },
                            use_container_width=True,
                        )
                        st.caption("Green = entry · Red = exit · Yellow = first fresh same-direction re-entry evidence.")
                else:
                    st.caption("Price replay history was not recorded for this legacy trade. New reviews will build the timeline automatically.")

                # Compact diagnosis: this is the engine's homework on the result.
                if diagnostic:
                    d1,d2,d3,d4=st.columns(4)
                    with d1: metric("Diagnosis",str(diagnostic.get("category") or "REVIEW"),str(diagnostic.get("severity") or ""))
                    with d2: metric("Best while held",f"{safe_float(diagnostic.get('mfe_pct')):+.2f}%","MFE")
                    with d3: metric("Worst while held",f"{safe_float(diagnostic.get('mae_pct')):+.2f}%","MAE")
                    with d4: metric("Best after exit",f"{safe_float(diagnostic.get('post_exit_best_pct')):+.2f}%","Same direction")
                    st.caption(str(diagnostic.get("next_question") or ""))

                # Four plain-English parts of the case file.
                left,right=st.columns(2)
                with left:
                    st.markdown("**Why the AI entered**")
                    reasons=decision.get("why_entered") or ["Entry evidence was not captured for this legacy trade."]
                    for reason in reasons[:5]:
                        st.write(f"• {reason}")
                    st.markdown("**Why the AI exited**")
                    for reason in (decision.get("why_exited") or [r.get("exit_reason") or "Unknown"])[:3]:
                        st.write(f"• {reason}")
                with right:
                    st.markdown("**What happened afterwards**")
                    st.write(decision.get("what_happened_next") or "Still collecting post-exit evidence.")
                    st.markdown("**What we learned**")
                    st.markdown(
                        f'<div class="summary-box">{esc(a.get("lesson") or "Still collecting evidence.")}</div>',
                        unsafe_allow_html=True,
                    )

                # Compact decision timeline: only changed states are useful to a human.
                decision_path=replay.get("decision_path") or []
                changed=[]
                last=None
                for d in decision_path:
                    state=str(d.get("state") or "")
                    if state and state!=last:
                        changed.append({
                            "Time":str(d.get("time") or "")[:16].replace("T"," "),
                            "AI state":state,
                            "Price":safe_float(d.get("price")),
                        })
                        last=state
                if changed:
                    st.markdown("**AI decision path**")
                    st.dataframe(pd.DataFrame(changed[-12:]),use_container_width=True,hide_index=True)

    section("Learning under test")
    candidates=learning.get("rule_candidates") or []
    if candidates:
        st.dataframe(
            pd.DataFrame([{
                "Evidence":x.get("key"),
                "Samples":x.get("samples"),
                "Expectancy %":x.get("expectancy_pct"),
                "Win rate %":x.get("win_rate"),
                "Direction":x.get("direction"),
                "Status":x.get("status"),
            } for x in candidates[:20]]),
            use_container_width=True,hide_index=True,
        )
    else:
        st.caption("No lesson has enough repeated evidence yet. The engine is collecting examples instead of forcing conclusions.")

    section("Challenger arena")
    ranking=arena.get("ranking") or []
    if not ranking:
        st.caption("Shadow challengers have not accumulated results yet. Run the Hourly Signal Recorder to begin the competition.")
    else:
        arena_rows=[{
            "Strategy":x.get("name"),
            "Trades":x.get("closed_trades"),
            "Win rate %":round(safe_float(x.get("win_rate_pct")),1),
            "Expectancy %":round(safe_float(x.get("expectancy_pct")),2),
            "Profit factor":round(safe_float(x.get("profit_factor")),2),
            "Net P/L":round(safe_float(x.get("net_pnl")),2),
            "Status":x.get("promotion_status"),
        } for x in ranking]
        st.dataframe(pd.DataFrame(arena_rows),use_container_width=True,hide_index=True)
        st.caption("This is paper-only self competition. Every challenger uses the same trade management so we can learn whether stricter entry filters improve results.")

    st.caption("Trade replay is evidence, not hindsight permission: learned rules remain sample-gated and never rewrite trading logic automatically.")

elif selection=="Settings":
    engine_health=read_runtime_json(ENGINE_HEALTH_FILE,{})
    risk=read_runtime_json(RISK_GUARDIAN_FILE,{})
    strategy=read_runtime_json(STRATEGY_LAB_FILE,{})
    observer=read_runtime_json(OBSERVER_LATEST_FILE,{})
    st.markdown('<div class="summary-box"><b>Settings and health:</b> operational information is kept away from the daily decision pages.</div>',unsafe_allow_html=True)
    tabs=st.tabs(["Engine Health","Workflows","Data Files","Advanced"])
    with tabs[0]:
        st.json(engine_health,expanded=False)
    with tabs[1]:
        st.dataframe(pd.DataFrame([{
            "Workflow":"Hourly Signal Recorder","Purpose":"4H signals, wallets, Strategy Lab and Risk Guardian",
            "Expected":"Hourly","Latest data":(engine_health.get("generated_at") or "")
        },{
            "Workflow":"15-Minute Market Observer","Purpose":"Early shifts and Observer wallet",
            "Expected":"15-minute attempts","Latest data":(observer.get("generated_at") or "")
        }]),use_container_width=True,hide_index=True)
    with tabs[2]:
        contract=read_runtime_json(Path(__file__).with_name("config")/"persistent_data.json",{"files":{}})
        st.dataframe(pd.DataFrame([{"Protected file":name,"Purpose":meta.get("purpose","")} for name,meta in (contract.get("files") or {}).items()]),use_container_width=True,hide_index=True)
    with tabs[3]:
        st.caption("Strategy and risk internals remain available here without crowding the daily pages.")
        with st.expander("Risk Guardian"): st.json(risk,expanded=False)
        with st.expander("Strategy Lab raw state"): st.json(strategy,expanded=False)

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
