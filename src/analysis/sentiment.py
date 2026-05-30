"""
src/analysis/sentiment.py — LLM Sentiment Analyser
Uses Claude to classify headlines: sentiment / risk_type / severity / action.
Batches all articles in one API call for efficiency.
"""
import json, logging, os
from typing import List, Dict
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class SentimentAnalyser:
    def __init__(self, config: dict):
        key = config.get("llm",{}).get("api_key","") or os.getenv("ANTHROPIC_API_KEY","")
        self.client  = Anthropic(api_key=key)
        self.model   = config.get("llm",{}).get("model","claude-sonnet-4-6")
        self.max_tok = config.get("llm",{}).get("max_tokens",1500)

    def analyse_batch(self, articles: List[Dict]) -> List[Dict]:
        if not articles: return []
        headlines_text = "\n".join(
            f"{i+1}. [{a.get('source','?')}] {a['headline']}" for i,a in enumerate(articles))
        prompt = f"""Analyse these supply chain news headlines for a procurement intelligence system.

HEADLINES:
{headlines_text}

For each headline return a JSON array. Each object must have EXACTLY:
- index: headline number (1-based)
- sentiment: "positive"|"negative"|"neutral"
- risk_type: "port_delay"|"financial"|"price_spike"|"weather"|"geopolitical"|"none"
- severity: "critical"|"warning"|"ok"
- summary: one-sentence supply chain impact
- recommended_action: specific procurement action or "Monitor"

Return ONLY valid JSON array, no markdown."""
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=self.max_tok,
                messages=[{"role":"user","content":prompt}])
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            results = json.loads(raw.strip())
            enriched = []
            for i, a in enumerate(articles):
                m = next((r for r in results if r.get("index")==i+1), {})
                enriched.append({**a,
                    "sentiment":m.get("sentiment","neutral"),
                    "risk_type":m.get("risk_type","none"),
                    "severity":m.get("severity","ok"),
                    "summary":m.get("summary",a["headline"]),
                    "recommended_action":m.get("recommended_action","Monitor")})
            logger.info(f"[Sentiment] Analysed {len(enriched)} articles")
            return enriched
        except Exception as e:
            logger.error(f"[Sentiment] Error: {e}")
            return [{**a,"sentiment":"neutral","risk_type":"none",
                     "severity":"ok","summary":a["headline"],
                     "recommended_action":"Monitor"} for a in articles]

    def analyse_single(self, headline: str, source: str="?") -> Dict:
        r = self.analyse_batch([{"headline":headline,"source":source,"related_suppliers":[]}])
        return r[0] if r else {}

    def generate_consensus(self, articles: List[Dict]) -> Dict:
        if not articles: return {"severity":"ok","critical_count":0,"warning_count":0}
        sevs = [a.get("severity","ok") for a in articles]
        cc, wc = sevs.count("critical"), sevs.count("warning")
        return {"severity":"critical" if cc else "warning" if wc else "ok",
                "critical_count":cc,"warning_count":wc,
                "risk_types":list(set(a.get("risk_type","none") for a in articles if a.get("risk_type")!="none"))}
