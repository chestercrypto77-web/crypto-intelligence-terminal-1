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
APP_VERSION = "8.1.0"
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

st.set_page_config(page_title=APP_NAME,page_icon="◈",layout="wide",initial_sidebar_state="expanded")
st.markdown(CSS,unsafe_allow_html=True)
market_rows, source = get_market_rows()
portfolio_intraday = get_portfolio_intraday()
portfolio = build_portfolio(market_rows, portfolio_intraday)

st.sidebar.markdown("## ◈ Intelligence Desk")
st.sidebar.caption(f"Version {APP_VERSION}")
st.sidebar.markdown("---")
selection = st.sidebar.radio("Navigation",["Today","Portfolio","Markets","Watch","Research","4H Intelligence","External Intelligence","Paper Trading","Performance Lab","Signal Lab"],label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption(f"{source} · portfolio prices 5 min · hourly moves 2 min")

titles = {
    "Today":("Good morning, Mark","Your portfolio briefing in under five minutes."),
    "Portfolio":("My Portfolio","How am I doing, and which holdings matter most today?"),
    "Markets":("Market Themes","Where is capital moving, and how is your portfolio exposed?"),
    "Watch":("Needs Attention","Only the holdings with the most meaningful changes."),
    "Research":("Research","The evidence beneath the daily briefing."),
    "4H Intelligence":("4H Intelligence","The platform’s primary conviction engine for portfolio and on-demand asset calls."),
    "External Intelligence":("External Intelligence","Hourly reviewed monitoring of approved analysts and public research sources."),
    "Paper Trading":("Paper Trading","Engine calls plus reviewed Sheldon and external predictions."),
    "Performance Lab":("Performance Lab","Measure whether calls became profitable or losing hours and days later."),
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
    section("Priority briefs")
    for start in range(0,len(portfolio["attention"]),2):
        cols=st.columns(2)
        for col,item in zip(cols,portfolio["attention"][start:start+2]):
            with col: attention_card(item)
    section("Interpretation")
    st.markdown('<div class="summary-box">A watch item is not automatically a buy or sell signal. It means price, participation, risk or momentum has changed enough to deserve closer investigation.</div>',unsafe_allow_html=True)

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
    st.markdown(
        '<div class="summary-box"><b>V6 conviction engine:</b> This page now combines fresh hourly/four-hour '
        'candles from multiple sources, evaluates a fixed checklist, and makes decisive Buy, Hold and Sell calls. '
        'The call is not a trade instruction; the complete evidence remains visible.</div>',
        unsafe_allow_html=True,
    )

    section("Action required")
    st.caption("All portfolio holdings are checked. Strongest calls appear first.")

    portfolio_calls = []
    progress_bar = st.progress(0, text="Scanning portfolio holdings...")
    held_tickers = {item["symbol"]: CRYPTO_TICKERS.get(item["symbol"], f'{item["symbol"]}-USD') for item in portfolio["items"]}
    total_assets = max(1, len(held_tickers))

    for index, item in enumerate(portfolio["items"]):
        symbol = item["symbol"]
        ticker = held_tickers[symbol]
        intelligence = unified_asset_intelligence(symbol, ticker)
        if intelligence.get("primary"):
            portfolio_calls.append({**item, "intelligence":intelligence})
        progress_bar.progress((index+1)/total_assets, text=f"Scanning {symbol}...")
    progress_bar.empty()

    signal_priority = {
        "STRONG BUY":7, "BUY":6, "BUY WATCH":5, "STRONG SELL":4,
        "SELL":3, "SELL WATCH":2, "HOLD":1,
    }
    portfolio_calls.sort(
        key=lambda x:(
            signal_priority.get(x["intelligence"]["primary"]["signal"],0),
            x["intelligence"]["primary"]["bullish"] - x["intelligence"]["primary"]["bearish"],
            abs(x["intelligence"]["primary"]["ret4h"]),
        ),
        reverse=True,
    )

    actionable = [x for x in portfolio_calls if x["intelligence"]["primary"]["signal"] != "HOLD"]
    for rank, item in enumerate((actionable or portfolio_calls)[:10], 1):
        render_action_row(rank, item)

    if portfolio_calls:
        counts = defaultdict(int)
        for item in portfolio_calls:
            counts[item["intelligence"]["primary"]["signal"]] += 1
        cols = st.columns(5)
        labels = ["STRONG BUY","BUY","BUY WATCH","SELL / STRONG SELL","HOLD"]
        values = [
            counts["STRONG BUY"],
            counts["BUY"],
            counts["BUY WATCH"],
            counts["SELL"]+counts["STRONG SELL"]+counts["SELL WATCH"],
            counts["HOLD"],
        ]
        for col,label,value in zip(cols,labels,values):
            with col:
                metric(label,str(value),"Current portfolio calls")

    section("Deep-dive asset")
    options = {
        f'{item["symbol"]} · {item["name"]} · held': (item["symbol"], CRYPTO_TICKERS.get(item["symbol"], f'{item["symbol"]}-USD'), item)
        for item in portfolio["items"]
    }
    selected_label = st.selectbox("Select a portfolio holding", list(options.keys()))
    selected_symbol, selected_ticker, selected_holding = options[selected_label]

    custom_cols = st.columns([1,1,1])
    with custom_cols[0]:
        custom_symbol = st.text_input("Or investigate another symbol", placeholder="Example: LINK")
    with custom_cols[1]:
        custom_market = st.selectbox("Asset type", ["Crypto","US stock / ETF"])
    with custom_cols[2]:
        run_custom = st.button("Deep dive", use_container_width=True)

    if run_custom and custom_symbol.strip():
        selected_symbol = custom_symbol.strip().upper()
        selected_ticker = resolve_ticker(selected_symbol, "Crypto" if custom_market=="Crypto" else "Stock / ETF")
        selected_holding = next((x for x in portfolio["items"] if x["symbol"]==selected_symbol), None)

    with st.spinner(f"Deep-diving {selected_symbol} across available sources..."):
        selected_intel = unified_asset_intelligence(selected_symbol, selected_ticker)

    result = selected_intel.get("primary")
    if not result:
        st.error(f"Could not retrieve enough four-hour data for {selected_symbol}.")
    else:
        hero_cols = st.columns([1.45,1])
        with hero_cols[0]:
            render_conviction_hero(
                selected_symbol, result,
                selected_intel.get("primary_source","Market data"),
                selected_intel.get("agreement","SINGLE SOURCE"),
            )
        with hero_cols[1]:
            source_html = "".join(
                f'<span class="source-chip">{esc(source["name"])} · {source["age"]:.0f} min · '
                f'{source["candles"]} candles</span>'
                for source in selected_intel.get("sources",[])
            )
            st.markdown(
                f'<div class="objective-card"><div class="objective-title">Data sources</div>'
                f'<div style="margin-top:.45rem">{source_html}</div>'
                f'<div class="objective-row"><span>Primary source</span>'
                f'<b>{esc(selected_intel.get("primary_source","—"))}</b></div>'
                f'<div class="objective-row"><span>Cross-source result</span>'
                f'<b>{esc(selected_intel.get("agreement","—"))}</b></div></div>',
                unsafe_allow_html=True,
            )

        section("Independent evidence groups")
        render_category_states(result["categories"])

        metric_cols = st.columns(6)
        metrics = [
            ("4-hour move", signed(result["ret4h"]), "Latest completed candle"),
            ("12-hour move", signed(result["ret12h"]), "Three 4H candles"),
            ("24-hour move", signed(result["ret24h"]), "Six 4H candles"),
            ("RVOL", f'{result["rvol"]:.2f}×', f'{result["rvol_delta"]:+.2f}× change'),
            ("RSI 14", f'{result["rsi"]:.1f}', f'{result["rsi_delta"]:+.1f} change'),
            ("ADX", f'{result["adx"]:.1f}' if pd.notna(result["adx"]) else "—", "Trend strength"),
        ]
        for col,(label,value,note) in zip(metric_cols,metrics):
            with col:
                metric(label,value,note)

        section("Conviction checklist")
        st.caption(
            f'{result["bullish"]} bullish conditions and {result["bearish"]} bearish conditions '
            f'out of {result["total"]}. No hidden 0–100 score is used.'
        )
        render_signal_checklist(result)

        section("Price and trend")
        st.line_chart(result["chart"], use_container_width=True)
        st.caption("Four-hour close with EMA 9, EMA 21 and EMA 55.")

        section("Source confirmation")
        if selected_intel.get("confirmations"):
            rows = []
            rows.append({
                "Source":selected_intel.get("primary_source"),
                "Call":result["signal"],
                "4H":signed(result["ret4h"]),
                "24H":signed(result["ret24h"]),
                "RVOL":round(result["rvol"],2),
                "Bullish":result["bullish"],
                "Bearish":result["bearish"],
            })
            for confirmation in selected_intel["confirmations"]:
                other = confirmation["result"]
                rows.append({
                    "Source":confirmation["source"],
                    "Call":other["signal"],
                    "4H":signed(other["ret4h"]),
                    "24H":signed(other["ret24h"]),
                    "RVOL":round(other["rvol"],2),
                    "Bullish":other["bullish"],
                    "Bearish":other["bearish"],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Only one usable candle source was available for this asset.")

        section("Call rules")
        st.markdown(
            '<div class="summary-box">'
            '<b>Strong Buy:</b> at least 10 bullish conditions, no more than two bearish conditions, '
            'with both trend and volume confirmation. '
            '<b>Buy:</b> at least eight bullish conditions with trend confirmation. '
            '<b>Buy Watch:</b> at least six bullish conditions. '
            '<b>Sell calls:</b> use the same thresholds in the opposite direction. '
            '<b>Hold:</b> evidence is not sufficiently one-sided.'
            '</div>',
            unsafe_allow_html=True,
        )




elif selection=="External Intelligence":
    inbox = read_runtime_json(EXTERNAL_INBOX_FILE, [])
    monitor_status = read_runtime_json(EXTERNAL_STATUS_FILE, {})
    source_config = read_runtime_json(EXTERNAL_SOURCES_FILE, {"sources":[]})
    external_calls = read_runtime_json(EXTERNAL_CALLS_FILE, [])

    st.markdown(
        '<div class="summary-box"><b>Reviewed intelligence feed:</b> the hourly workflow monitors '
        'approved public sources and identifies possible calls or market ideas. Nothing is entered '
        'into paper trading until you review and confirm it.</div>',
        unsafe_allow_html=True,
    )

    enabled_sources = [s for s in source_config.get("sources",[]) if s.get("enabled")]
    pending = [x for x in inbox if x.get("review_status","PENDING")=="PENDING"]
    possible = [x for x in pending if x.get("classification") in {"POSSIBLE CALL","POSSIBLE IDEA"}]
    cols=st.columns(4)
    with cols[0]: metric("Pending items",str(len(pending)),"Awaiting review")
    with cols[1]: metric("Possible calls / ideas",str(len(possible)),"Rule-based detection")
    with cols[2]: metric("Enabled sources",str(len(enabled_sources)),"Public approved feeds")
    with cols[3]:
        last_run=monitor_status.get("last_run")
        metric("Last monitor run",last_run[:16].replace("T"," ") if last_run else "Not run","UTC")

    tab_inbox, tab_review, tab_sources = st.tabs([
        "Intelligence Inbox","Review and Prepare Call","Approved Sources"
    ])

    with tab_inbox:
        filters=st.columns(3)
        with filters[0]:
            classification_filter=st.selectbox(
                "Classification",
                ["ALL","POSSIBLE CALL","POSSIBLE IDEA","COMMENTARY","GENERAL CONTENT"]
            )
        with filters[1]:
            platform_filter=st.selectbox(
                "Platform",
                ["ALL"]+sorted({str(x.get("platform")) for x in inbox if x.get("platform")})
            )
        with filters[2]:
            source_filter=st.selectbox(
                "Source",
                ["ALL"]+sorted({str(x.get("source_name")) for x in inbox if x.get("source_name")})
            )

        visible=[]
        for item in inbox:
            if classification_filter!="ALL" and item.get("classification")!=classification_filter:
                continue
            if platform_filter!="ALL" and item.get("platform")!=platform_filter:
                continue
            if source_filter!="ALL" and item.get("source_name")!=source_filter:
                continue
            visible.append(item)

        if not visible:
            st.info("No monitored items match the current filters. Run the hourly workflow once after uploading V7.2.")
        else:
            for item in visible[:100]:
                direction=item.get("direction","UNCLEAR")
                badge = call_badge(
                    "BUY WATCH" if direction=="LONG"
                    else "SELL WATCH" if direction=="SHORT"
                    else "HOLD"
                )
                symbols=", ".join(item.get("symbols") or []) or "No asset detected"
                st.markdown(
                    f'<div class="research-card">'
                    f'<div class="research-head">'
                    f'<div><div class="research-asset">{esc(item.get("source_name"))}</div>'
                    f'<div class="research-name">{esc(item.get("platform"))} · {esc(item.get("published_at") or item.get("detected_at"))}</div></div>'
                    f'<div><div class="research-label">Classification</div><div class="research-value">{esc(item.get("classification"))}</div></div>'
                    f'<div><div class="research-label">Direction</div><div class="research-value">{badge}</div></div>'
                    f'<div><div class="research-label">Assets</div><div class="research-value">{esc(symbols)}</div></div>'
                    f'<div><div class="research-label">Review</div><div class="research-value">{esc(item.get("review_status","PENDING"))}</div></div>'
                    f'<div><div class="research-label">Levels found</div><div class="research-value">{esc(", ".join(str(x) for x in item.get("price_levels",[])) or "—")}</div></div>'
                    f'</div>'
                    f'<div class="research-details" style="grid-template-columns:1fr">'
                    f'<div><div class="research-label">Title</div><div class="research-value">{esc(item.get("title"))}</div>'
                    f'<div class="research-name" style="margin-top:.35rem">{esc((item.get("summary") or "")[:500])}</div>'
                    f'<div style="margin-top:.45rem"><a href="{esc(item.get("source_link"))}" target="_blank">Open original source</a></div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

    with tab_review:
        candidates=[x for x in inbox if x.get("classification") in {"POSSIBLE CALL","POSSIBLE IDEA"}]
        if not candidates:
            st.info("No possible calls or ideas are waiting for review.")
        else:
            labels={
                f'{x.get("source_name")} · {x.get("title","")[:70]} · {x.get("item_id")}':x
                for x in candidates
            }
            selected_label=st.selectbox("Select detected item",list(labels.keys()))
            selected=labels[selected_label]
            detected_symbols=selected.get("symbols") or [""]
            detected_levels=selected.get("price_levels") or []

            st.markdown(
                f'<div class="tab-note"><b>Original:</b> {esc(selected.get("title"))}<br>'
                f'<b>Detected:</b> {esc(selected.get("classification"))} · '
                f'{esc(selected.get("direction"))} · {esc(", ".join(detected_symbols) or "no symbol")}<br>'
                f'<a href="{esc(selected.get("source_link"))}" target="_blank">Open and verify the source before approving</a></div>',
                unsafe_allow_html=True,
            )

            c1,c2,c3=st.columns(3)
            with c1:
                review_source=st.text_input("Source",value=selected.get("person") or selected.get("source_name"))
                review_symbol=st.text_input("Confirmed symbol",value=detected_symbols[0])
                default_direction=selected.get("direction") if selected.get("direction") in {"LONG","SHORT"} else "LONG"
                review_direction=st.selectbox("Confirmed direction",["LONG","SHORT"],index=0 if default_direction=="LONG" else 1)
            with c2:
                review_call=st.selectbox("Confirmed call",["BUY WATCH","BUY","STRONG BUY","SELL WATCH","SELL","STRONG SELL"])
                review_entry=st.number_input(
                    "Entry price",
                    min_value=0.0,
                    value=float(detected_levels[0]) if detected_levels else 0.0,
                    format="%.10f",
                )
                review_timeframe=st.text_input("Timeframe",placeholder="4H / swing / daily")
            with c3:
                review_target=st.number_input(
                    "Target price",
                    min_value=0.0,
                    value=float(detected_levels[1]) if len(detected_levels)>1 else 0.0,
                    format="%.10f",
                )
                review_invalidation=st.number_input(
                    "Invalidation price",
                    min_value=0.0,
                    value=float(detected_levels[2]) if len(detected_levels)>2 else 0.0,
                    format="%.10f",
                )
                review_link=st.text_input("Source link",value=selected.get("source_link",""))

            review_notes=st.text_area(
                "Review notes",
                value=f'Original title: {selected.get("title","")}\nDetected text: {(selected.get("summary") or "")[:700]}'
            )

            if st.button("Prepare confirmed external_calls.json",use_container_width=True):
                if not review_symbol.strip() or review_entry<=0:
                    st.error("Confirm the symbol and enter a valid entry price.")
                else:
                    updated=list(external_calls) if isinstance(external_calls,list) else []
                    call_id=f'REVIEWED_{selected.get("item_id")}'
                    if not any(str(x.get("call_id"))==call_id for x in updated):
                        updated.append({
                            "call_id":call_id,
                            "source":review_source.strip().upper(),
                            "symbol":review_symbol.strip().upper(),
                            "direction":review_direction,
                            "call":review_call,
                            "entry_time":pd.Timestamp.now(tz="UTC").isoformat(),
                            "entry_price":review_entry,
                            "target_price":review_target or None,
                            "invalidation_price":review_invalidation or None,
                            "timeframe":review_timeframe,
                            "source_link":review_link,
                            "notes":review_notes,
                            "status":"ACTIVE",
                            "detected_item_id":selected.get("item_id"),
                        })
                    st.success("Verified call prepared. Download and replace data/external_calls.json in GitHub.")
                    st.download_button(
                        "Download confirmed external_calls.json",
                        data=json.dumps(updated,indent=2),
                        file_name="external_calls.json",
                        mime="application/json",
                        use_container_width=True,
                    )

    with tab_sources:
        rows=[]
        for source in source_config.get("sources",[]):
            rows.append({
                "Enabled":source.get("enabled"),
                "Source":source.get("name"),
                "Person":source.get("person"),
                "Platform":source.get("platform"),
                "Type":source.get("type"),
                "Review required":source.get("review_required"),
                "Notes":source.get("notes"),
                "Profile":source.get("profile_url"),
            })
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        st.markdown(
            '<div class="summary-box"><b>X limitation:</b> the Sheldon X source is listed but disabled '
            'because official API credentials are required. YouTube and Medium public feeds work without '
            'private credentials. Video titles and descriptions can be monitored; full video understanding '
            'would require transcripts or a separate transcription service.</div>',
            unsafe_allow_html=True,
        )


elif selection=="Paper Trading":
    latest_signals = read_runtime_json(SIGNALS_LATEST_FILE, {"generated_at":None,"signals":[]})
    signal_history = read_runtime_json(SIGNAL_HISTORY_FILE, [])
    paper_trades = read_runtime_json(PAPER_TRADES_FILE, [])
    external_calls = read_runtime_json(EXTERNAL_CALLS_FILE, [])
    current_prices = {item["symbol"]:item["price"] for item in portfolio["items"]}

    engine_trades = [t for t in paper_trades if t.get("source")=="OUR ENGINE"]
    sheldon_trades = [t for t in paper_trades if t.get("source")=="SHELDON THE SNIPER"]
    other_trades = [t for t in paper_trades if t.get("source") not in {"OUR ENGINE","SHELDON THE SNIPER"}]

    st.markdown(
        '<div class="summary-box"><b>Automatic accountability:</b> the hourly workflow freezes '
        'engine calls and separately tracks reviewed Sheldon and manual calls.</div>',
        unsafe_allow_html=True,
    )

    generated_at = latest_signals.get("generated_at")
    cols=st.columns(4)
    with cols[0]: metric("Engine trades",str(len(engine_trades)),"Automatically recorded")
    with cols[1]: metric("Sheldon trades",str(len(sheldon_trades)),"Reviewed external calls")
    with cols[2]: metric("Signal records",str(len(signal_history)),"Hourly journal")
    with cols[3]: metric("Last recorder run",generated_at[:16].replace("T"," ") if generated_at else "Not run","UTC")

    tab_engine, tab_sheldon, tab_add, tab_journal = st.tabs([
        "Our Engine Calls","Sheldon Calls","Add Sheldon / External Call","Signal Journal"
    ])

    with tab_engine:
        st.markdown('<div class="tab-note">Calls created automatically when the engine changes into an actionable Buy or Sell state.</div>',unsafe_allow_html=True)
        if not engine_trades:
            st.info("No engine paper trades have been opened yet.")
        else:
            rows=[]
            for trade in reversed(engine_trades):
                live=trade_live_return(trade,current_prices)
                rows.append({
                    "Asset":trade.get("symbol"),"Call":trade.get("call"),
                    "Direction":trade.get("direction"),
                    "Entry time":str(trade.get("entry_time",""))[:16].replace("T"," "),
                    "Entry price":trade.get("entry_price"),
                    "Current":current_prices.get(trade.get("symbol")),
                    "Open return":live,
                    "Best":trade.get("best_return"),"Worst":trade.get("worst_return"),
                    "Status":trade.get("status"),
                })
            frame=pd.DataFrame(rows)
            st.dataframe(frame,use_container_width=True,hide_index=True)

    with tab_sheldon:
        st.markdown('<div class="tab-note">Only calls you have reviewed and confirmed are listed here. They remain separate from our engine.</div>',unsafe_allow_html=True)
        if external_calls:
            st.markdown("#### Reviewed Sheldon call list")
            st.dataframe(pd.DataFrame(external_calls),use_container_width=True,hide_index=True)
        else:
            st.caption("No reviewed Sheldon calls have been added yet.")
        if sheldon_trades:
            st.markdown("#### Sheldon paper-trade tracking")
            rows=[]
            for trade in reversed(sheldon_trades):
                rows.append({
                    "Asset":trade.get("symbol"),"Call":trade.get("call"),
                    "Direction":trade.get("direction"),"Entry":trade.get("entry_price"),
                    "1H":checkpoint_return(trade,"1h"),"4H":checkpoint_return(trade,"4h"),
                    "12H":checkpoint_return(trade,"12h"),"24H":checkpoint_return(trade,"1d"),
                    "Current":trade.get("current_return"),"Status":trade.get("status"),
                })
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

    with tab_add:
        st.markdown(
            '<div class="tab-note"><b>Workflow:</b> enter the confirmed call, download the generated '
            '<code>external_calls.json</code>, then replace <code>data/external_calls.json</code> in GitHub.</div>',
            unsafe_allow_html=True,
        )
        c1,c2,c3=st.columns(3)
        with c1:
            ext_source=st.selectbox("Source",["SHELDON THE SNIPER","MARK","OTHER"])
            ext_symbol=st.text_input("Asset symbol",placeholder="COTI")
            ext_direction=st.selectbox("Direction",["LONG","SHORT"])
        with c2:
            ext_call=st.selectbox("Call",["BUY WATCH","BUY","STRONG BUY","SELL WATCH","SELL","STRONG SELL"])
            ext_entry=st.number_input("Entry price",min_value=0.0,value=0.0,format="%.10f")
            ext_timeframe=st.text_input("Timeframe",placeholder="4H / swing / daily")
        with c3:
            ext_target=st.number_input("Target price",min_value=0.0,value=0.0,format="%.10f")
            ext_invalidation=st.number_input("Invalidation price",min_value=0.0,value=0.0,format="%.10f")
            ext_link=st.text_input("Source link or reference")
        ext_notes=st.text_area("Notes",placeholder="Record exactly what was predicted and any conditions.")
        if st.button("Prepare updated external_calls.json",use_container_width=True):
            if not ext_symbol.strip() or ext_entry<=0:
                st.error("Enter an asset symbol and a valid entry price.")
            else:
                updated=list(external_calls) if isinstance(external_calls,list) else []
                call_id=f'{ext_source.replace(" ","_")}_{ext_symbol.upper()}_{pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")}'
                updated.append({
                    "call_id":call_id,"source":ext_source,"symbol":ext_symbol.strip().upper(),
                    "direction":ext_direction,"call":ext_call,
                    "entry_time":pd.Timestamp.now(tz="UTC").isoformat(),
                    "entry_price":ext_entry,"target_price":ext_target or None,
                    "invalidation_price":ext_invalidation or None,"timeframe":ext_timeframe,
                    "source_link":ext_link,"notes":ext_notes,"status":"ACTIVE"
                })
                st.success("Download the file, then replace data/external_calls.json in GitHub.")
                st.download_button(
                    "Download external_calls.json",
                    data=json.dumps(updated,indent=2),
                    file_name="external_calls.json",
                    mime="application/json",
                    use_container_width=True,
                )

    with tab_journal:
        changed=[x for x in latest_signals.get("signals",[]) if x.get("changed")]
        st.markdown("#### Latest signal changes")
        if not changed:
            st.caption("No signal-state changes in the latest hourly scan.")
        else:
            for r in changed:
                st.markdown(
                    f'<div class="action-row"><div><div class="fourh-asset">{esc(r.get("symbol"))}</div>'
                    f'<div class="fourh-name">{esc(r.get("name"))}</div></div>'
                    f'<div>{call_badge(r.get("previous_signal") or "FIRST SCAN")}<div class="fourh-name">Previous</div></div>'
                    f'<div>{call_badge(r.get("signal"))}<div class="fourh-name">Current</div></div>'
                    f'<div><b>{r.get("entry_price",0):.8g}</b><div class="fourh-name">Frozen price</div></div>'
                    f'<div><b>{r.get("bullish",0)} bull / {r.get("bearish",0)} bear</b>'
                    f'<div class="fourh-name">{esc(r.get("data_source"))}</div></div></div>',
                    unsafe_allow_html=True,
                )
        with st.expander(f"Full signal journal · {len(signal_history)} records"):
            rows=[]
            for r in reversed(signal_history[-1000:]):
                rows.append({
                    "Recorded":str(r.get("recorded_at",""))[:16].replace("T"," "),
                    "Asset":r.get("symbol"),"Signal":r.get("signal"),
                    "Previous":r.get("previous_signal"),"Changed":r.get("changed"),
                    "Entry":r.get("entry_price"),"4H":r.get("return_4h"),
                    "12H":r.get("return_12h"),"24H":r.get("return_24h"),
                    "RVOL":r.get("rvol"),"Source":r.get("data_source"),
                })
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif selection=="Performance Lab":
    paper_trades=read_runtime_json(PAPER_TRADES_FILE,[])
    if not paper_trades:
        st.info("No paper trades have been recorded yet. The hourly recorder will populate this page as signals and reviewed external calls are captured.")
    else:
        st.markdown('<div class="summary-box"><b>Purpose:</b> Judge every engine and external call using the same hourly and daily checkpoints. Long calls profit when price rises; short calls profit when price falls.</div>',unsafe_allow_html=True)
        sources=sorted({str(t.get("source") or "UNKNOWN") for t in paper_trades})
        section("Source comparison")
        source_rows=[]
        for source_name in sources:
            s=performance_summary([t for t in paper_trades if str(t.get("source") or "UNKNOWN")==source_name])
            source_rows.append({"Source":source_name,"Calls":s["calls"],"Evaluated":s["evaluated"],
              "Win rate":f'{s["win_rate"]:.1f}%',"Average return":f'{s["average_return"]:+.2f}%',
              "Average winner":f'{s["average_winner"]:+.2f}%',"Average loser":f'{s["average_loser"]:+.2f}%',
              "Profit factor":"∞" if math.isinf(s["profit_factor"]) else f'{s["profit_factor"]:.2f}'})
        st.dataframe(pd.DataFrame(source_rows),use_container_width=True,hide_index=True)
        s=performance_summary(paper_trades)
        cols=st.columns(4)
        with cols[0]: metric("Total calls",str(s["calls"]),f'{s["evaluated"]} evaluated')
        with cols[1]: metric("Win rate",f'{s["win_rate"]:.1f}%',"Above +0.25%")
        with cols[2]: metric("Average result",f'{s["average_return"]:+.2f}%',"Latest checkpoint")
        with cols[3]: metric("Profit factor","∞" if math.isinf(s["profit_factor"]) else f'{s["profit_factor"]:.2f}',"Gross wins ÷ gross losses")
        section("Call-by-call outcomes")
        rows=[]
        for t in reversed(paper_trades):
            result=evaluated_return(t)
            outcome="WIN" if result is not None and result>.25 else "LOSS" if result is not None and result<-.25 else "FLAT / PENDING"
            rows.append({"Source":t.get("source"),"Asset":t.get("symbol"),"Call":t.get("call"),
              "Direction":t.get("direction"),"Entry":t.get("entry_price"),
              "1H":checkpoint_return(t,"1h"),"4H":checkpoint_return(t,"4h"),
              "12H":checkpoint_return(t,"12h"),"24H":checkpoint_return(t,"1d"),
              "3D":checkpoint_return(t,"3d"),"7D":checkpoint_return(t,"7d"),
              "Best":t.get("best_return"),"Worst":t.get("worst_return"),
              "Latest":result,"Outcome":outcome,"Status":t.get("status")})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        section("Learning rule")
        st.markdown('<div class="summary-box">The platform will compare results by source, call type, direction, asset, narrative and entry conditions. It will not rewrite live rules from a handful of examples; changes should wait for a meaningful sample.</div>',unsafe_allow_html=True)


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
