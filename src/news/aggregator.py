"""
src/news/aggregator.py — News Aggregator
Fetches supply chain headlines from NewsAPI or returns realistic mock data.
Extracts supplier mentions from each headline.
"""
import os, logging, requests
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)

MOCK_HEADLINES = [
    {"headline":"Shanghai port faces severe congestion, shipping delays expected 8-12 days","source":"Reuters","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["AsiaTech Co.","GlobalParts Inc."]},
    {"headline":"Aluminium spot prices surge 18% over past month amid supply concerns","source":"Economic Times","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["EuroMaterials"]},
    {"headline":"VendorX Ltd credit rating downgraded by S&P from BB to BB-","source":"Business Standard","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["VendorX Ltd."]},
    {"headline":"Malaysia manufacturing zone issues flood advisory for factory districts","source":"Moneycontrol","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["AsiaTech Co.","GlobalParts Inc."]},
    {"headline":"US proposes 5% tariff increase on electronics imports effective August","source":"Reuters","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["AsiaTech Co."]},
    {"headline":"AsiaTech Co reports record Q2 on-time delivery rate of 97 percent","source":"Economic Times","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["AsiaTech Co."]},
    {"headline":"Global freight rates rise 22% as Red Sea disruptions continue","source":"Reuters","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["PacificSource"]},
    {"headline":"PacificSource logistics reports 36% late delivery rate in Q2","source":"Moneycontrol","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["PacificSource"]},
    {"headline":"Copper prices hit 3-month high on Chinese demand recovery","source":"Business Standard","url":"","published_at":datetime.now().isoformat(),"related_suppliers":["EuroMaterials"]},
    {"headline":"Supply chain resilience index drops to lowest since 2021","source":"Economic Times","url":"","published_at":datetime.now().isoformat(),"related_suppliers":[]},
]

SUPPLIER_KEYWORDS = {
    "AsiaTech Co.":    ["asiatech","asia tech"],
    "EuroMaterials":   ["euromaterials","euro materials"],
    "VendorX Ltd.":    ["vendorx","vendor x"],
    "PacificSource":   ["pacificsource","pacific source"],
    "GlobalParts Inc.":["globalparts","global parts"],
}

class NewsAggregator:
    def __init__(self, config: dict):
        self.api_key  = config.get("news",{}).get("api_key","") or os.getenv("NEWS_API_KEY","")
        self.keywords = config.get("news",{}).get("keywords",["supply chain"])
        self.max_art  = config.get("news",{}).get("max_articles",20)

    def fetch_latest(self) -> List[Dict]:
        if not self.api_key:
            logger.info("[News] No key — using mock headlines")
            return self._enrich(MOCK_HEADLINES[:self.max_art])
        articles = []
        for kw in self.keywords[:3]:
            articles += self._call_api(kw)
        seen, unique = set(), []
        for a in articles:
            k = a["headline"].lower()[:80]
            if k not in seen:
                seen.add(k); unique.append(a)
        return self._enrich(unique[:self.max_art])

    def _call_api(self, keyword: str) -> List[Dict]:
        try:
            r = requests.get("https://newsapi.org/v2/everything", params={
                "q":keyword,"language":"en","sortBy":"publishedAt","pageSize":10,
                "from":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d"),
                "apiKey":self.api_key}, timeout=8)
            r.raise_for_status()
            return [{"headline":a.get("title",""),"source":a.get("source",{}).get("name","?"),
                     "url":a.get("url",""),"published_at":a.get("publishedAt",""),
                     "related_suppliers":[]}
                    for a in r.json().get("articles",[]) if a.get("title")]
        except Exception as e:
            logger.warning(f"[News] API error: {e}"); return []

    def _enrich(self, articles):
        for a in articles:
            if not a.get("related_suppliers"):
                hl = a["headline"].lower()
                a["related_suppliers"] = [s for s,kws in SUPPLIER_KEYWORDS.items() if any(k in hl for k in kws)]
        return articles

    def scrape_economic_times(self): return MOCK_HEADLINES[0:2]
    def scrape_moneycontrol(self):   return MOCK_HEADLINES[2:4]
    def scrape_reuters(self):        return MOCK_HEADLINES[4:6]
