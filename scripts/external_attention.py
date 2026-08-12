from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
import copy,json,math,os
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def now():return datetime.now(timezone.utc).isoformat()
def read(path,default):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return copy.deepcopy(default)
def write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    t=path.with_suffix(path.suffix+".tmp")
    t.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    json.loads(t.read_text(encoding="utf-8"));t.replace(path)
def f(v,d=0.0):
    try:
        x=float(v);return x if math.isfinite(x) else d
    except Exception:return d
def parse(v):
    try:
        x=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if x.tzinfo is None:x=x.replace(tzinfo=timezone.utc)
        return x.astimezone(timezone.utc)
    except Exception:return None

import requests,re,hashlib
OUT=DATA/"external_attention.json"
TRENDING="https://api.coingecko.com/api/v3/search/trending"
NEWS="https://newsapi.org/v2/everything"
POS=("partnership","approval","listing","launch","integration","adoption","upgrade","funding","record","growth")
NEG=("hack","exploit","lawsuit","delist","investigation","outage","delay","unlock","breach")
def symbols(text):
    known={str(x.get("symbol") or "").upper() for x in read(ROOT/"holdings.json",[])}
    upper=str(text).upper();return sorted([s for s in known if re.search(rf"(?<![A-Z0-9])\\$?{re.escape(s)}(?![A-Z0-9])",upper)])
def event(source,title,summary,url,published,kind="NEWS",credibility="MEDIUM"):
    blob=f"{title} {summary}";syms=symbols(blob);low=blob.lower()
    pos=sum(w in low for w in POS);neg=sum(w in low for w in NEG)
    tone="POSITIVE" if pos>=neg+2 else "NEGATIVE" if neg>=pos+2 else "MIXED / UNCLEAR"
    eid=hashlib.sha256(f"{source}|{url}|{title}".encode()).hexdigest()[:20]
    return {"event_id":eid,"source":source,"kind":kind,"title":title,"summary":summary[:1000],"url":url,
            "published_at":published,"detected_at":now(),"symbols":syms,"tone":tone,"credibility":credibility}

def main():
    existing=read(OUT,{"events":[]}).get("events") or []
    byid={x.get("event_id"):x for x in existing if x.get("event_id")}
    health=[]

    # Existing reviewed-public-feed monitor is another independent input.
    inbox=read(DATA/"external_inbox.json",[])
    if isinstance(inbox,list):
        for x in inbox[:300]:
            ev=event(str(x.get("source_name") or x.get("source_id") or "Configured feed"),
                     str(x.get("title") or ""),str(x.get("summary") or ""),str(x.get("source_link") or ""),
                     x.get("published_at") or x.get("detected_at"),"PUBLIC FEED","MEDIUM")
            if x.get("symbols"):ev["symbols"]=x.get("symbols")
            byid[ev["event_id"]]=ev
        health.append({"source":"Configured public feeds","status":"PASS","items":len(inbox[:300])})

    # CoinGecko search attention: no claim of sentiment, only attention.
    try:
        r=requests.get(TRENDING,timeout=12,headers={"User-Agent":"CryptoIntelligenceTerminal/18"})
        r.raise_for_status();data=r.json()
        count=0
        for rank,row in enumerate(data.get("coins") or []):
            item=row.get("item") or {};sym=str(item.get("symbol") or "").upper()
            if not sym:continue
            title=f"CoinGecko trending search #{rank+1}: {sym}"
            ev=event("CoinGecko Trending",title,str(item.get("name") or sym),"",now(),"SEARCH ATTENTION","HIGH")
            ev["symbols"]=[sym];ev["trending_rank"]=rank+1;ev["attention_only"]=True
            byid[ev["event_id"]]=ev;count+=1
        health.append({"source":"CoinGecko Trending","status":"PASS","items":count})
    except Exception as exc:
        health.append({"source":"CoinGecko Trending","status":"FAIL","items":0,"error":str(exc)})

    # Optional broad news API. No key = transparent waiting state, not silent failure.
    key=os.getenv("NEWSAPI_KEY","").strip()
    if key:
        try:
            query="crypto OR bitcoin OR ethereum OR blockchain"
            params={"q":query,"language":"en","sortBy":"publishedAt","pageSize":50,"apiKey":key}
            r=requests.get(NEWS,params=params,timeout=15);r.raise_for_status();data=r.json()
            for a in data.get("articles") or []:
                ev=event(str((a.get("source") or {}).get("name") or "NewsAPI"),
                         str(a.get("title") or ""),str(a.get("description") or ""),str(a.get("url") or ""),
                         a.get("publishedAt"),"NEWS","HIGH")
                byid[ev["event_id"]]=ev
            health.append({"source":"NewsAPI","status":"PASS","items":len(data.get("articles") or [])})
        except Exception as exc:
            health.append({"source":"NewsAPI","status":"FAIL","items":0,"error":str(exc)})
    else:
        health.append({"source":"NewsAPI","status":"WAITING FOR NEWSAPI_KEY","items":0})

    events=sorted(byid.values(),key=lambda x:str(x.get("published_at") or x.get("detected_at")),reverse=True)[:5000]
    # Aggregate per held/watch asset with recency-weighted attention; attention is separate from sentiment.
    assets={}
    current=datetime.now(timezone.utc)
    for ev in events:
        t=parse(ev.get("published_at") or ev.get("detected_at"))
        age=(current-t).total_seconds()/3600 if t else 48
        recency=max(0,1-age/48)
        base=30 if ev.get("kind")=="SEARCH ATTENTION" else 20
        if ev.get("credibility")=="HIGH":base+=10
        for sym in ev.get("symbols") or []:
            a=assets.setdefault(str(sym).upper(),{"events":0,"positive":0,"negative":0,"attention_score":0,"latest":[]})
            a["events"]+=1;a["attention_score"]+=base*recency
            if ev.get("tone")=="POSITIVE":a["positive"]+=1
            elif ev.get("tone")=="NEGATIVE":a["negative"]+=1
            if len(a["latest"])<5:a["latest"].append({"source":ev.get("source"),"title":ev.get("title"),"kind":ev.get("kind"),"published_at":ev.get("published_at")})
    for a in assets.values():a["attention_score"]=min(100,a["attention_score"])
    payload={"updated_at":now(),"summary":{"events":len(events),"assets_with_attention":len(assets),
              "healthy_sources":sum(x["status"]=="PASS" for x in health),"sources":len(health)},
             "assets":assets,"events":events,"source_health":health,
             "guardrail":"Attention and headlines are committee evidence, never automatic trade instructions. Search popularity is not treated as positive sentiment."}
    write(OUT,payload);print(json.dumps({"summary":payload["summary"],"sources":health},indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
