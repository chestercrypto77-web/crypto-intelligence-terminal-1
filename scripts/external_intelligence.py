from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import requests


ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "external_sources.json"
DATA_DIR = ROOT / "data"
INBOX_FILE = DATA_DIR / "external_inbox.json"
SEEN_FILE = DATA_DIR / "external_seen.json"

USER_AGENT = "Mozilla/5.0 CryptoIntelligenceTerminal/8.6.1 reviewed-public-feed-monitor"

DIRECTION_PATTERNS = {
    "LONG": [
        r"\blong\b", r"\bbuy\b", r"\bbullish\b", r"\baccumulat(?:e|ing|ion)\b",
        r"\bbreakout\b", r"\bupside\b", r"\bgoing higher\b", r"\bready to pump\b",
    ],
    "SHORT": [
        r"\bshort\b", r"\bsell\b", r"\bbearish\b", r"\bdistribution\b",
        r"\bbreakdown\b", r"\bdownside\b", r"\bgoing lower\b",
    ],
}
CALL_WORDS = [
    "entry", "target", "stop", "invalidation", "take profit", "tp",
    "long", "short", "buy", "sell", "setup", "trade",
]
COMMENTARY_WORDS = [
    "market update", "analysis", "news", "interview", "explained",
    "prediction", "outlook", "strategy",
]
COMMON_SYMBOLS = {
    "BTC","ETH","SOL","COTI","ONDO","LINK","AVAX","SUI","SEI","NEAR","DOT","POL",
    "ZIL","FIL","AIOZ","RUNE","XRP","ADA","DOGE","SHIB","TAO","FET","RENDER",
    "HYPE","AAVE","UNI","ARB","OP","IMX","OM","PAAL","SUPER","GALA","SAND",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def item_id(source_id: str, link: str, title: str) -> str:
    raw = f"{source_id}|{link}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def child_text(element, endings):
    for child in element.iter():
        tag = child.tag.split("}")[-1].lower()
        if tag in endings and child.text:
            return child.text.strip()
    return ""


def parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    entries = []
    for node in root.iter():
        local = node.tag.split("}")[-1].lower()
        if local not in {"entry", "item"}:
            continue
        title = child_text(node, {"title"})
        published = child_text(node, {"published", "updated", "pubdate"})
        summary = child_text(node, {"summary", "description", "content"})
        link = ""
        for child in node.iter():
            if child.tag.split("}")[-1].lower() == "link":
                link = child.attrib.get("href") or (child.text or "")
                if link:
                    break
        if title and link:
            entries.append({
                "title": clean_text(title),
                "summary": clean_text(summary),
                "link": link.strip(),
                "published_at": published,
            })
    return entries


def extract_symbols(text: str) -> list[str]:
    upper = text.upper()
    found = set()
    for symbol in COMMON_SYMBOLS:
        if re.search(rf"(?<![A-Z0-9])\$?{re.escape(symbol)}(?![A-Z0-9])", upper):
            found.add(symbol)
    for symbol in re.findall(r"\$([A-Z][A-Z0-9]{1,9})\b", upper):
        found.add(symbol)
    return sorted(found)


def detect_direction(text: str) -> str:
    scores = {}
    lower = text.lower()
    for direction, patterns in DIRECTION_PATTERNS.items():
        scores[direction] = sum(bool(re.search(pattern, lower)) for pattern in patterns)
    if scores["LONG"] > scores["SHORT"] and scores["LONG"] > 0:
        return "LONG"
    if scores["SHORT"] > scores["LONG"] and scores["SHORT"] > 0:
        return "SHORT"
    return "UNCLEAR"


def extract_price_levels(text: str) -> list[float]:
    values = []
    patterns = [
        r"(?:entry|target|stop|invalidation|tp)\s*(?:at|around|near|:|-)?\s*\$?\s*([0-9]+(?:\.[0-9]+)?)",
        r"\$\s*([0-9]+(?:\.[0-9]+)?)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.I):
            try:
                number = float(match)
                if number > 0:
                    values.append(number)
            except Exception:
                pass
    unique = []
    for number in values:
        if number not in unique:
            unique.append(number)
    return unique[:6]


def classify(text: str, symbols: list[str], direction: str) -> str:
    lower = text.lower()
    call_hits = sum(word in lower for word in CALL_WORDS)
    commentary_hits = sum(word in lower for word in COMMENTARY_WORDS)
    if symbols and direction != "UNCLEAR" and call_hits >= 2:
        return "POSSIBLE CALL"
    if symbols and (direction != "UNCLEAR" or call_hits >= 1):
        return "POSSIBLE IDEA"
    if commentary_hits or symbols:
        return "COMMENTARY"
    return "GENERAL CONTENT"


def analyze(source: dict, entry: dict) -> dict:
    combined = f'{entry.get("title","")} {entry.get("summary","")}'.strip()
    symbols = extract_symbols(combined)
    direction = detect_direction(combined)
    classification = classify(combined, symbols, direction)
    return {
        "item_id": item_id(source["id"], entry["link"], entry["title"]),
        "detected_at": now_iso(),
        "source_id": source["id"],
        "source_name": source["name"],
        "person": source.get("person", ""),
        "platform": source.get("platform", ""),
        "title": entry["title"],
        "summary": entry.get("summary", "")[:1600],
        "source_link": entry["link"],
        "published_at": entry.get("published_at", ""),
        "classification": classification,
        "symbols": symbols,
        "direction": direction,
        "price_levels": extract_price_levels(combined),
        "review_status": "PENDING",
        "review_required": True,
        "raw_evidence": combined[:2400],
    }



def _decode_json_text(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except Exception:
        return value.replace(r'\"', '"').replace(r'\n', ' ')


def parse_youtube_channel_page(page_text: str) -> list[dict]:
    """Extract recent public video titles and IDs from YouTube's channel page JSON."""
    entries = []
    seen_video_ids = set()
    patterns = [
        r'"videoId":"([^"]+)".{0,1800}?"title":\{"runs":\[\{"text":"((?:\\.|[^"])*)"',
        r'"videoId":"([^"]+)".{0,1800}?"title":\{"simpleText":"((?:\\.|[^"])*)"',
    ]
    for pattern in patterns:
        for video_id, raw_title in re.findall(pattern, page_text, flags=re.S):
            if video_id in seen_video_ids:
                continue
            title = clean_text(_decode_json_text(raw_title))
            if not title:
                continue
            seen_video_ids.add(video_id)
            entries.append({
                "title": title,
                "summary": "Public YouTube channel-page detection. Open the original video to verify the full context.",
                "link": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": "",
            })
            if len(entries) >= 30:
                return entries
    return entries


def fetch_youtube_channel(source: dict) -> tuple[list[dict], str]:
    errors = []
    feed_url = source.get("url")
    if feed_url:
        try:
            response = requests.get(feed_url, timeout=15, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            entries = parse_feed(response.text)
            if entries:
                return entries, "YouTube RSS"
        except Exception as exc:
            errors.append(f"RSS: {exc}")

    page_url = source.get("handle_url") or source.get("profile_url")
    if page_url:
        try:
            response = requests.get(
                page_url,
                timeout=20,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "en-AU,en;q=0.9",
                },
            )
            response.raise_for_status()
            entries = parse_youtube_channel_page(response.text)
            if entries:
                return entries, "YouTube public page fallback"
            errors.append("Channel page returned no extractable videos")
        except Exception as exc:
            errors.append(f"Channel page: {exc}")

    raise RuntimeError("; ".join(errors) or "No usable YouTube source configured")


def fetch_source(source: dict) -> tuple[list[dict], str]:
    source_type = source.get("type")
    if source_type == "youtube_channel":
        return fetch_youtube_channel(source)
    if source_type in {"rss", "youtube_rss"}:
        response = requests.get(
            source["url"],
            timeout=15,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return parse_feed(response.text), "RSS"
    if source_type == "x_api":
        return [], "Disabled: official API credentials required"
    return [], "Disabled or unsupported source"


def main() -> int:
    config = load_json(CONFIG_FILE, {"sources": []})
    inbox = load_json(INBOX_FILE, [])
    seen = load_json(SEEN_FILE, [])
    if not isinstance(inbox, list):
        inbox = []
    if not isinstance(seen, list):
        seen = []
    seen_ids = set(seen)
    new_count = 0
    errors = []
    source_status = []

    for source in config.get("sources", []):
        if not source.get("enabled"):
            continue
        try:
            entries, method = fetch_source(source)
            source_status.append({
                "source_id": source.get("id"),
                "status": "PASS",
                "method": method,
                "items_read": len(entries),
            })
            for entry in entries[:20]:
                analyzed = analyze(source, entry)
                if analyzed["item_id"] in seen_ids:
                    continue
                inbox.append(analyzed)
                seen_ids.add(analyzed["item_id"])
                new_count += 1
        except Exception as exc:
            error_record = {
                "source_id": source.get("id"),
                "error": str(exc),
                "recorded_at": now_iso(),
            }
            errors.append(error_record)
            source_status.append({
                "source_id": source.get("id"),
                "status": "FAIL",
                "method": source.get("type"),
                "items_read": 0,
                "error": str(exc),
            })

    # Most recent first; retain a practical history.
    inbox.sort(key=lambda x: x.get("published_at") or x.get("detected_at"), reverse=True)
    save_json(INBOX_FILE, inbox[:2000])
    save_json(SEEN_FILE, sorted(seen_ids)[-10000:])
    save_json(DATA_DIR / "external_monitor_status.json", {
        "last_run": now_iso(),
        "new_items": new_count,
        "total_inbox": len(inbox),
        "errors": errors,
        "sources": source_status,
    })
    print(json.dumps({
        "new_items": new_count,
        "total_inbox": len(inbox),
        "errors": errors,
        "sources": source_status,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
